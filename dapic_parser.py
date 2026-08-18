# -*- coding: utf-8 -*-
"""
Leitor do relatório "Consulta de estoque" do Dapic (PDF) -> disponibilidade
por referência / cor / tamanho.

Gera um dicionário:
    disponibilidade[ref_canonico][COR_NORMALIZADA][TAMANHO_NORMALIZADO] = quantidade disponível
    refs_encontradas = set de refs (canônicas) que apareceram no relatório

Regras específicas observadas no relatório real do cliente (Bella Moda Íntima):
- Produtos "plus size" às vezes aparecem como uma referência separada com
  sufixo "/PLUS" (ex: "2069-1/PLUS"), que deve ser somada à referência base
  ("2069-1"), pois no site as duas fazem parte do MESMO produto.
- Nomes de cor longos (ex: "CHOCOLATE") quebram de linha dentro da célula do
  PDF, então usamos o CÓDIGO da cor (número antes do "-") como chave real de
  cruzamento e mantemos um mapa código -> nome (construído automaticamente
  a partir do relatório + um fallback fixo para os códigos já conhecidos).
"""
import re
import subprocess
import sys
import unicodedata

try:
    import pdfplumber
except ImportError:
    # instala automaticamente no MESMO interpretador Python que está
    # rodando o script (evita o problema de "instalei num Python e rodei
    # com outro" quando o Windows tem mais de uma instalação de Python).
    print("Dependência 'pdfplumber' não encontrada — instalando automaticamente...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

# Fallback conhecido (código de cor no Dapic -> nome), usado quando o nome
# não pode ser lido com segurança na célula (linha quebrada no PDF).
CODIGO_COR_FALLBACK = {
    "1": "PRETO",
    "2": "CIDREIRA",
    "3": "DESEJO",
    "4": "MARINHO",
    "5": "RUBI",
    "6": "PINK",
    "7": "BASE",
    "8": "BRANCO",
    "9": "SATIN",
    "10": "PANTERA",
    "11": "FROZEN",
    "18": "ROMANCE",
    "27": "CHOCOLATE",
    "30": "BROWNIE",
    "31": "ESTAMPA SORTIDA",
}


def _remove_acentos(txt):
    nfkd = unicodedata.normalize("NFD", txt)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalizar(txt):
    """Maiúsculo, sem acento, sem espaços extras — usado para comparar
    cores e tamanhos entre o relatório do Dapic e o catálogo do site."""
    if txt is None:
        return ""
    txt = _remove_acentos(str(txt)).upper().strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def canonicalizar_ref(ref):
    """Normaliza uma referência para comparação: remove sufixo /PLUS e
    zeros à esquerda do bloco numérico inicial, para casar coisas como
    '030' (relatório) com '30' (site), ou '2069-1/PLUS' com '2069-1'."""
    if ref is None:
        return ""
    r = ref.strip().upper()
    r = r.replace("/PLUS", "")
    r = re.sub(r"^0+(?=\d)", "", r)
    return r


def _extrair_codigo_nome_cor(texto_cel):
    """A partir do texto bruto da célula 'Cor' (pode ter \n por quebra de
    linha), extrai (codigo, nome_ou_None). O nome só é confiável quando a
    célula NÃO quebrou linha; quando quebrou, devolve nome=None e quem
    chama decide usar o fallback."""
    primeira_linha = texto_cel.split("\n")[0]
    if " - " not in primeira_linha:
        return None, None
    codigo, resto = primeira_linha.split(" - ", 1)
    codigo = codigo.strip()

    if "\n" in texto_cel:
        # célula quebrou linha -> não dá pra confiar no nome extraído aqui
        return codigo, None

    # remove o número de "disponível" que vem colado no final (ex: "PRETO 7")
    nome = re.sub(r"\s*\d+\s*$", "", resto).strip()
    return codigo, nome if nome else None


def ler_relatorio_estoque(caminho_pdf):
    """Lê o PDF do relatório 'Consulta de estoque' do Dapic e devolve:
    (dados, refs_encontradas, avisos)

    dados[ref_canonico][COR_NORMALIZADA][TAMANHO_NORMALIZADO] = {"real": int, "disponivel": int}

    - "real": quantidade física total (coluna "Real" do relatório) — é o
      número usado para preencher o limite de quantidade no site
      (estoquePorCorTamanho).
    - "disponivel": "Real" menos o que já está "Comprometida" — usado só
      para decidir se uma cor/tamanho deve aparecer como opção no site.
    """
    dados = {}
    refs_encontradas = set()
    mapa_codigo_cor = dict(CODIGO_COR_FALLBACK)
    avisos = []

    linhas_brutas = []  # (ref_cel, cor_cel, tamanho, real, disponivel)

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                ref_atual = None
                cor_atual = None
                for linha in tabela:
                    if not linha or len(linha) < 8:
                        continue
                    produto_cel, _disp1, cor_cel, _disp2, tamanho, real, _comp, disponivel = linha[:8]

                    # ignora cabeçalhos
                    if produto_cel in ("Produtos acabados", "Produto"):
                        continue
                    if tamanho == "Tamanho":
                        continue

                    if produto_cel:
                        ref_atual = produto_cel.split(" - ", 1)[0].strip()
                    if cor_cel:
                        cor_atual = cor_cel

                    if ref_atual is None or cor_atual is None or tamanho is None:
                        continue
                    if real is None or disponivel is None:
                        continue

                    linhas_brutas.append((ref_atual, cor_atual, tamanho, real, disponivel))

    # 1a passada: construir mapa código->nome de cor usando células que não quebraram linha
    for _ref, cor_cel, _tam, _real, _disp in linhas_brutas:
        codigo, nome = _extrair_codigo_nome_cor(cor_cel)
        if codigo and nome:
            mapa_codigo_cor[codigo] = normalizar(nome)

    # normaliza o fallback também
    for cod, nome in CODIGO_COR_FALLBACK.items():
        mapa_codigo_cor.setdefault(cod, normalizar(nome))

    # 2a passada: montar os dados finais
    codigos_sem_nome = set()
    for ref, cor_cel, tamanho, real, disponivel in linhas_brutas:
        # a referência "apareceu no relatório" mesmo que a cor não seja
        # reconhecida — isso evita deixar o produto inteiro intocado só
        # porque UMA das cores não pôde ser identificada.
        refs_encontradas.add(canonicalizar_ref(ref))

        codigo, _ = _extrair_codigo_nome_cor(cor_cel)
        if not codigo:
            continue
        nome_cor = mapa_codigo_cor.get(codigo)
        if not nome_cor:
            codigos_sem_nome.add(codigo)
            continue

        try:
            qtd_real = int(str(real).strip())
            qtd_disp = int(str(disponivel).strip())
        except ValueError:
            continue

        ref_canon = canonicalizar_ref(ref)
        tam_norm = normalizar(tamanho)

        refs_encontradas.add(ref_canon)
        dados.setdefault(ref_canon, {}).setdefault(nome_cor, {})
        # soma (caso REF e REF/PLUS caiam na mesma cor+tamanho, o que não
        # deveria acontecer, mas somar é seguro)
        atual = dados[ref_canon][nome_cor].get(tam_norm, {"real": 0, "disponivel": 0})
        dados[ref_canon][nome_cor][tam_norm] = {
            "real": atual["real"] + qtd_real,
            "disponivel": atual["disponivel"] + qtd_disp,
        }

    if codigos_sem_nome:
        avisos.append(
            "Códigos de cor sem nome identificado (ignorados): "
            + ", ".join(sorted(codigos_sem_nome))
        )

    return dados, refs_encontradas, avisos
