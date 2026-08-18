# -*- coding: utf-8 -*-
"""
Atualiza o estoque do site (index.html) a partir do relatório de estoque do Dapic.

Uso:
    python atualizar_estoque.py [caminho_do_pdf]

Se nenhum caminho for informado, procura por: relatorios/estoque.pdf

O que o script faz:
1. Lê dados/catalogo_master.json (lista COMPLETA de produtos, tamanhos e
   cores que a loja já vendeu algum dia — esse arquivo é o "catálogo cheio",
   editado manualmente só quando um produto/cor/tamanho novo é cadastrado).
2. Lê o PDF do relatório "Consulta de estoque" do Dapic.
3. Para cada produto do catálogo master, decide quais tamanhos e cores
   continuam disponíveis hoje (com base no relatório) e monta a lista final
   que vai pro site.
4. Regrava o array `produtos` dentro do index.html.
5. Faz commit e push automático pro GitHub (a menos que rode com --sem-git).

Regra de negócio (definida com o dono da loja):
- Se uma cor não tem NENHUM tamanho com saldo disponível > 0 -> a cor some
  das opções do produto.
- Se um tamanho não tem NENHUMA cor com saldo disponível > 0 -> o tamanho
  some das opções do produto.
- Se o produto inteiro zerar (nenhuma combinação de cor/tamanho com saldo)
  -> o produto some do catálogo do site.
- Se uma referência do site não aparecer OU uma cor/tamanho específico do
  produto não aparecer no relatório do Dapic, o script NÃO mexe nessa
  cor/tamanho (mantém como estava) e avisa no final — isso evita apagar
  coisa por falta de dado, só por saldo realmente zerado.
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from dapic_parser import ler_relatorio_estoque, normalizar, canonicalizar_ref

PASTA_BASE = Path(__file__).resolve().parent
CATALOGO_MASTER = PASTA_BASE / "dados" / "catalogo_master.json"
INDEX_HTML = PASTA_BASE / "index.html"
PDF_PADRAO = PASTA_BASE / "relatorios" / "estoque.pdf"


def carregar_catalogo_master():
    with open(CATALOGO_MASTER, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_novo_catalogo(catalogo_master, disponibilidade, refs_encontradas):
    """Devolve (novo_catalogo, relatorio_mudancas)."""
    novo_catalogo = []
    mudancas = []

    for produto in catalogo_master:
        ref = produto["ref"]
        ref_canon = canonicalizar_ref(ref)

        if ref_canon not in refs_encontradas:
            # referência não apareceu no relatório -> não mexe, só avisa
            mudancas.append(f"[AVISO] Ref {ref} não encontrada no relatório do Dapic — mantido como estava.")
            novo_catalogo.append(produto)
            continue

        disp_produto = disponibilidade.get(ref_canon, {})

        cores_originais = produto.get("cores", [])
        tamanhos_originais = produto.get("tamanhos", [])

        def tem_estoque(cor, tamanho):
            cor_norm = normalizar(cor)
            tam_norm = normalizar(tamanho)
            if cor_norm not in disp_produto:
                return None  # sem dado -> desconhecido
            qtd = disp_produto[cor_norm].get(tam_norm)
            if qtd is None:
                return None
            return qtd > 0

        novas_cores = []
        for cor in cores_originais:
            resultados = [tem_estoque(cor, t) for t in tamanhos_originais]
            # some só se TODOS os tamanhos dessa cor deram resultado
            # conhecido (não-None) e nenhum tinha estoque
            conhecidos = [r for r in resultados if r is not None]
            if conhecidos and not any(conhecidos):
                mudancas.append(f"  - {ref} ({produto['nome']}): cor '{cor}' removida (sem estoque em nenhum tamanho)")
                continue
            novas_cores.append(cor)

        novos_tamanhos = []
        for tamanho in tamanhos_originais:
            resultados = [tem_estoque(c, tamanho) for c in cores_originais]
            conhecidos = [r for r in resultados if r is not None]
            if conhecidos and not any(conhecidos):
                mudancas.append(f"  - {ref} ({produto['nome']}): tamanho '{tamanho}' removido (sem estoque em nenhuma cor)")
                continue
            novos_tamanhos.append(tamanho)

        if not novas_cores or not novos_tamanhos:
            mudancas.append(f"[PRODUTO ESCONDIDO] {ref} ({produto['nome']}): sem estoque em nenhuma variação.")
            continue

        produto_novo = dict(produto)
        produto_novo["cores"] = novas_cores
        produto_novo["tamanhos"] = novos_tamanhos
        novo_catalogo.append(produto_novo)

    return novo_catalogo, mudancas


def _js_str(valor):
    return json.dumps(valor, ensure_ascii=False)


def montar_bloco_js(catalogo):
    linhas = ["const produtos = [", ""]
    for p in catalogo:
        partes = [f'ref:{_js_str(p["ref"])}', f'nome:{_js_str(p["nome"])}', f'preco:{p["preco"]}']
        if p.get("precoPlus") is not None:
            partes.append(f'precoPlus:{p["precoPlus"]}')
        tamanhos = ",".join(_js_str(t) for t in p["tamanhos"])
        partes.append(f"tamanhos:[{tamanhos}]")
        cores = ",".join(_js_str(c) for c in p["cores"])
        partes.append(f"cores:[{cores}]")
        if p.get("frases"):
            frases = ",".join(_js_str(fr) for fr in p["frases"])
            partes.append(f"frases:[{frases}]")
        linhas.append(" {" + ",".join(partes) + "},")
    linhas.append("")
    linhas.append(" ];")
    return "\n".join(linhas)


def gravar_no_index_html(bloco_js):
    html = INDEX_HTML.read_text(encoding="utf-8")
    padrao = re.compile(r"const produtos = \[[\s\S]*?\n\s*\];")
    if not padrao.search(html):
        raise RuntimeError("Não encontrei o array 'const produtos = [...]' no index.html — nada foi alterado.")
    novo_html = padrao.sub(lambda _m: bloco_js, html, count=1)
    INDEX_HTML.write_text(novo_html, encoding="utf-8")


def git_commit_e_push():
    def rodar(cmd):
        return subprocess.run(cmd, cwd=PASTA_BASE, capture_output=True, text=True)

    rodar(["git", "add", "index.html"])
    status = rodar(["git", "status", "--porcelain", "index.html"])
    if not status.stdout.strip():
        print("Nada mudou no index.html — não é necessário commit.")
        return

    hoje = date.today().isoformat()
    commit = rodar(["git", "commit", "-m", f"Atualização automática de estoque - {hoje}"])
    print(commit.stdout)
    if commit.returncode != 0:
        print(commit.stderr)
        print("ERRO ao commitar. Rode 'git status' pra ver o que houve.")
        return

    push = rodar(["git", "push"])
    print(push.stdout)
    if push.returncode != 0:
        print(push.stderr)
        print("ERRO ao dar push. O commit foi feito localmente, mas não subiu pro GitHub — rode 'git push' manualmente.")
    else:
        print("Site atualizado e enviado pro GitHub com sucesso!")


def main():
    caminho_pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_PADRAO
    sem_git = "--sem-git" in sys.argv

    if not caminho_pdf.exists():
        print(f"ERRO: não encontrei o PDF em {caminho_pdf}")
        print("Exporte o relatório 'Consulta de estoque' do Dapic e salve nesse caminho (ou passe o caminho como argumento).")
        sys.exit(1)

    print(f"Lendo relatório: {caminho_pdf}")
    disponibilidade, refs_encontradas, avisos = ler_relatorio_estoque(str(caminho_pdf))
    print(f"Referências encontradas no relatório: {len(refs_encontradas)}")
    for a in avisos:
        print("AVISO:", a)

    catalogo_master = carregar_catalogo_master()
    novo_catalogo, mudancas = calcular_novo_catalogo(catalogo_master, disponibilidade, refs_encontradas)

    print("\n--- Resumo das mudanças ---")
    if mudancas:
        for m in mudancas:
            print(m)
    else:
        print("Nenhuma mudança de estoque detectada.")

    print(f"\nProdutos no catálogo master: {len(catalogo_master)}")
    print(f"Produtos que continuam visíveis no site: {len(novo_catalogo)}")

    bloco_js = montar_bloco_js(novo_catalogo)
    gravar_no_index_html(bloco_js)
    print("\nindex.html atualizado.")

    if sem_git:
        print("Rodado com --sem-git: revise o index.html e faça o commit/push você mesmo.")
    else:
        git_commit_e_push()


if __name__ == "__main__":
    main()
