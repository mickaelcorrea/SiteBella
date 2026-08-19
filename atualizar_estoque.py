# -*- coding: utf-8 -*-
"""
Atualiza o estoque do site (index.html) a partir do relatório de estoque do Dapic.

Uso:
    python atualizar_estoque.py [caminho_do_pdf] [--sem-git]

Se nenhum caminho for informado, procura por: relatorios/estoque.pdf

O que o script faz:
1. Lê dados/catalogo_master.json (lista COMPLETA de produtos, preços,
   tamanhos e cores que a loja oferece — esse arquivo é o "catálogo cheio",
   editado manualmente só quando um produto/cor/tamanho novo é cadastrado,
   ou quando o PREÇO de um produto muda).
2. Lê o PDF do relatório "Consulta de estoque" do Dapic.
3. Para cada produto do catálogo master, decide quais tamanhos e cores
   continuam disponíveis hoje (com base no relatório) e monta a lista final
   que vai pro site.
4. Regrava DOIS blocos dentro do index.html:
   - o array `produtos` (nome, preço, e quais tamanhos/cores aparecem como
     opção — o PREÇO vem sempre do catalogo_master.json, o script nunca
     inventa nem altera preço sozinho);
   - o objeto `estoquePorCorTamanho` (quantidade exata por cor/tamanho,
     usada pelo seletor de quantidade e pela validação do carrinho).
5. Faz commit e push automático pro GitHub (a menos que rode com --sem-git).

Regra de negócio (definida com o dono da loja):
- Se uma cor não tem NENHUM tamanho com saldo > 0 (coluna "Real" do Dapic)
  -> a cor some das opções do produto.
- Se um tamanho não tem NENHUMA cor com saldo > 0 -> o tamanho some das
  opções do produto.
- Se o produto inteiro zerar -> o produto some do catálogo do site.
- Se uma referência do site não aparecer no relatório do Dapic, o script
  NÃO mexe nela (mantém como estava) e avisa no final.
- O script só decide entre MOSTRAR ou ESCONDER cores/tamanhos que já
  existem no catálogo master — ele não inventa cor/tamanho novo que nunca
  foi cadastrado. Se aparecer estoque de uma cor/tamanho totalmente novo no
  Dapic, o script avisa no final para você decidir se quer cadastrar.

IMPORTANTE sobre "Considerar saldo zerado" (opção do relatório do Dapic):
- Se o relatório foi gerado com essa opção em "Sim", uma linha com
  quantidade 0 aparece explicitamente no PDF.
- Se foi gerado com "Não", linhas zeradas simplesmente NÃO aparecem no
  relatório — ou seja, a AUSÊNCIA de uma cor/tamanho (dentro de uma
  referência que apareceu no relatório) já significa "está zerado".
  O script detecta automaticamente qual dos dois modos foi usado lendo o
  cabeçalho do PDF, e ajusta a regra sozinho. Isso é importante porque o
  Dapic pode mudar essa configuração de um relatório pro outro sem avisar,
  e usar a regra errada faz o script parar de esconder itens sem estoque.

IMPORTANTE sobre PREÇO:
- O script NUNCA calcula, arredonda ou altera preço. Ele só copia o valor
  que já está em dados/catalogo_master.json. Se o preço no site estiver
  errado, o problema está nesse arquivo (ou foi editado direto no
  index.html sem atualizar o master) — corrija o preço lá, não no
  index.html, senão a próxima rodada do script apaga a correção manual.
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

# Ordem "natural" de tamanho, só para deixar os botões no site em ordem
# lógica (P, M, G... depois os plus size) em vez da ordem em que apareceram
# no relatório do Dapic.
ORDEM_TAMANHO = ["ÚNICO", "PP", "P", "M", "G", "GG", "XG", "36", "38", "40", "42", "44", "46", "48", "50", "52", "54"]


def carregar_catalogo_master():
    with open(CATALOGO_MASTER, "r", encoding="utf-8") as f:
        return json.load(f)


def ordenar_tamanhos(tamanhos):
    def chave(t):
        t_norm = normalizar(t)
        return (ORDEM_TAMANHO.index(t_norm) if t_norm in ORDEM_TAMANHO else 999, t)
    return sorted(tamanhos, key=chave)


def calcular_novo_catalogo(catalogo_master, dados, refs_encontradas, inclui_zerados):
    """Devolve (novo_catalogo, relatorio_mudancas, cores_novas_detectadas).

    inclui_zerados indica se o PDF foi gerado com "Considerar saldo zerado:
    Sim" ou "Não" (ver docstring do módulo). Isso muda a regra pra uma
    combinação cor/tamanho que não aparece nos dados de uma ref que FOI
    encontrada no relatório:
    - Sim -> tratamos como "sem dado / desconhecido" (mantém como estava).
    - Não -> tratamos como "confirmadamente zerado" (esconde).
    """
    novo_catalogo = []
    mudancas = []
    cores_novas_detectadas = []

    for produto in catalogo_master:
        ref = produto["ref"]
        ref_canon = canonicalizar_ref(ref)

        if ref_canon not in refs_encontradas:
            mudancas.append(f"[AVISO] Ref {ref} não encontrada no relatório do Dapic — mantido como estava.")
            novo_catalogo.append(produto)
            continue

        disp_produto = dados.get(ref_canon, {})

        cores_originais = produto.get("cores", [])
        tamanhos_originais = produto.get("tamanhos", [])

        # avisa (sem agir) sobre cor/tamanho que o Dapic conhece mas o
        # catálogo master não — pode ser produto novo que vale cadastrar.
        cores_norm_conhecidas = {normalizar(c) for c in cores_originais}
        for cor_relatorio, tam_dict in disp_produto.items():
            if cor_relatorio not in cores_norm_conhecidas:
                total = sum(v["real"] for v in tam_dict.values())
                if total > 0:
                    cores_novas_detectadas.append((ref, produto["nome"], cor_relatorio, total))

        def saldo(cor, tamanho):
            cor_norm = normalizar(cor)
            tam_norm = normalizar(tamanho)
            info_cor = disp_produto.get(cor_norm)
            if info_cor is None:
                return None if inclui_zerados else False
            info = info_cor.get(tam_norm)
            if info is None:
                return None if inclui_zerados else False
            return info["real"] > 0

        novas_cores = []
        for cor in cores_originais:
            resultados = [saldo(cor, t) for t in tamanhos_originais]
            conhecidos = [r for r in resultados if r is not None]
            if conhecidos and not any(conhecidos):
                mudancas.append(f"  - {ref} ({produto['nome']}): cor '{cor}' removida (sem estoque em nenhum tamanho)")
                continue
            novas_cores.append(cor)

        novos_tamanhos = []
        for tamanho in tamanhos_originais:
            resultados = [saldo(c, tamanho) for c in cores_originais]
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
        produto_novo["tamanhos"] = ordenar_tamanhos(novos_tamanhos)
        novo_catalogo.append(produto_novo)

    return novo_catalogo, mudancas, cores_novas_detectadas


def montar_estoque_por_cor_tamanho(novo_catalogo, dados, inclui_zerados):
    """Monta o dicionário ref -> cor -> tamanho -> quantidade "real", só
    para as combinações que sobreviveram no novo_catalogo.

    Quando o relatório NÃO lista linhas zeradas (inclui_zerados=False),
    uma combinação cor/tamanho sem dado no PDF é preenchida com 0 em vez de
    omitida — porque no site, uma combinação AUSENTE do
    estoquePorCorTamanho é tratada como "estoque ilimitado". Se não
    preenchêssemos o 0 explícito aqui, qualquer combinação zerada (omitida
    pelo Dapic) voltaria a ficar sem limite nenhum no site."""
    resultado = {}
    for produto in novo_catalogo:
        ref = produto["ref"]
        ref_canon = canonicalizar_ref(ref)
        disp_produto = dados.get(ref_canon)
        if not disp_produto:
            continue
        bloco_produto = {}
        for cor in produto["cores"]:
            cor_norm = normalizar(cor)
            info_cor = disp_produto.get(cor_norm)
            if not info_cor:
                # sem dado nenhum pra essa cor -> deixa sem entrada aqui
                # (comportamento permissivo, igual referência não encontrada)
                continue
            bloco_cor = {}
            for tamanho in produto["tamanhos"]:
                tam_norm = normalizar(tamanho)
                info_tam = info_cor.get(tam_norm)
                if info_tam is None:
                    if inclui_zerados:
                        continue
                    bloco_cor[tamanho] = 0
                else:
                    bloco_cor[tamanho] = info_tam["real"]
            if bloco_cor:
                bloco_produto[cor] = bloco_cor
        if bloco_produto:
            resultado[ref] = bloco_produto
    return resultado


def _js_str(valor):
    return json.dumps(valor, ensure_ascii=False)


def montar_bloco_produtos(catalogo):
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


def montar_bloco_estoque(estoque_por_ref, catalogo, data_relatorio):
    nomes_por_ref = {p["ref"]: p["nome"] for p in catalogo}
    linhas = [
        "// ===== Estoque por COR x TAMANHO x QUANTIDADE =====",
        "//",
        '// Preenchido automaticamente pelo atualizar_estoque.py a partir da',
        f'// coluna "Real" do relatório do Dapic ({data_relatorio}).',
        "//",
        "// Produto -> Cor -> Tamanho -> Quantidade.",
        "// Produtos ou cores que não constam no relatório ficam com estoque",
        "// ilimitado (comportamento antigo preservado).",
        "const estoquePorCorTamanho = {",
    ]
    refs = list(estoque_por_ref.keys())
    for i, ref in enumerate(refs):
        nome = nomes_por_ref.get(ref, "")
        if nome:
            linhas.append(f"  // {nome}")
        linhas.append(f'  {_js_str(ref)}: {{')
        cores = list(estoque_por_ref[ref].keys())
        for j, cor in enumerate(cores):
            tamanhos = estoque_por_ref[ref][cor]
            partes_tam = ", ".join(f"{_js_str(t)}: {q}" for t, q in tamanhos.items())
            virgula = "," if j < len(cores) - 1 else ""
            linhas.append(f"    {_js_str(cor)}: {{ {partes_tam} }}{virgula}")
        virgula_ref = "," if i < len(refs) - 1 else ""
        linhas.append(f"  }}{virgula_ref}")
    linhas.append("};")
    return "\n".join(linhas)


def gravar_no_index_html(bloco_produtos, bloco_estoque):
    html = INDEX_HTML.read_text(encoding="utf-8")

    padrao_produtos = re.compile(r"const produtos = \[[\s\S]*?\n\s*\];")
    if not padrao_produtos.search(html):
        raise RuntimeError("Não encontrei o array 'const produtos = [...]' no index.html — nada foi alterado.")
    html = padrao_produtos.sub(lambda _m: bloco_produtos, html, count=1)

    padrao_estoque = re.compile(
        r"// ===== Estoque por COR x TAMANHO x QUANTIDADE =====[\s\S]*?\nconst estoquePorCorTamanho = \{[\s\S]*?\n\};"
    )
    if padrao_estoque.search(html):
        html = padrao_estoque.sub(lambda _m: bloco_estoque, html, count=1)
    else:
        print("AVISO: não encontrei o bloco 'estoquePorCorTamanho' no index.html — ele não foi atualizado.")
        print("(Isso é esperado se o seu site ainda não tem esse sistema de estoque numérico.)")

    INDEX_HTML.write_text(html, encoding="utf-8")


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
    caminho_pdf = None
    sem_git = False
    for arg in sys.argv[1:]:
        if arg == "--sem-git":
            sem_git = True
        else:
            caminho_pdf = Path(arg)
    if caminho_pdf is None:
        caminho_pdf = PDF_PADRAO

    if not caminho_pdf.exists():
        print(f"ERRO: não encontrei o PDF em {caminho_pdf}")
        print("Exporte o relatório 'Consulta de estoque' do Dapic e salve nesse caminho (ou passe o caminho como argumento).")
        sys.exit(1)

    print(f"Lendo relatório: {caminho_pdf}")
    dados, refs_encontradas, avisos, inclui_zerados = ler_relatorio_estoque(str(caminho_pdf))
    print(f"Referências encontradas no relatório: {len(refs_encontradas)}")
    for a in avisos:
        print("AVISO:", a)

    catalogo_master = carregar_catalogo_master()
    novo_catalogo, mudancas, cores_novas = calcular_novo_catalogo(catalogo_master, dados, refs_encontradas, inclui_zerados)

    print("\n--- Resumo das mudanças ---")
    if mudancas:
        for m in mudancas:
            print(m)
    else:
        print("Nenhuma mudança de estoque detectada.")

    if cores_novas:
        print("\n--- Cores com estoque no Dapic que NÃO estão cadastradas no catálogo master ---")
        print("(o script não adicionou automaticamente — cadastre em dados/catalogo_master.json se quiser vendê-las)")
        for ref, nome, cor, total in cores_novas:
            print(f"  - {ref} ({nome}): cor '{cor}' com {total} unidades no Dapic, mas não cadastrada no site")

    print(f"\nProdutos no catálogo master: {len(catalogo_master)}")
    print(f"Produtos que continuam visíveis no site: {len(novo_catalogo)}")

    estoque_por_ref = montar_estoque_por_cor_tamanho(novo_catalogo, dados, inclui_zerados)
    bloco_produtos = montar_bloco_produtos(novo_catalogo)
    bloco_estoque = montar_bloco_estoque(estoque_por_ref, novo_catalogo, date.today().strftime("%d/%m/%Y"))

    gravar_no_index_html(bloco_produtos, bloco_estoque)
    print("\nindex.html atualizado (lista de produtos + quantidades por cor/tamanho).")

    if sem_git:
        print("Rodado com --sem-git: revise o index.html e faça o commit/push você mesmo.")
    else:
        git_commit_e_push()


if __name__ == "__main__":
    main()
