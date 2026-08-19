#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

BASE = Path(__file__).resolve().parent
PDF_PATH = BASE / "estoque.pdf"
HTML_PATH = BASE / "index.html"
JSON_PATH = BASE / "estoque.json"

# Códigos de cor usados no relatório do Dapic.
COR_CODIGOS = {
    "1": "Preto", "2": "Cidreira", "3": "Desejo", "4": "Marinho",
    "5": "Rubi", "6": "Pink", "7": "Base", "8": "Branco",
    "9": "Satin", "10": "Pantera", "11": "Frozen", "12": "Chumbo",
    "18": "Romance",
}

# O site usa um código diferente do Dapic para esta referência.
ALIASES_REF = {"CUECA-015": "CUECA-15"}

# O Dapic pode imprimir estas variações para o tamanho Único.
NORMALIZAR_TAMANHO = {
    "UNICO": "Único",
    "ÚNICO": "Único",
    "U/PLUS": "Único",
    "PP": "PP", "P": "P", "M": "M", "G": "G", "GG": "GG", "XG": "XG",
    "48": "48", "50": "50", "52": "52", "54": "54",
}

TAMANHO_RE = re.compile(
    r"(?<![A-ZÀ-Ü])(PP|P|M|G|GG|XG|UNICO|ÚNICO|U/PLUS|48|50|52|54)\s+"
    r"(\d+)\s+0\s+(\d+)"
)


def referencias_do_site():
    html = HTML_PATH.read_text(encoding="utf-8")
    refs = re.findall(r'\{ref:"([^"]+)"', html)
    if not refs:
        raise RuntimeError("Nenhuma referência foi encontrada no index.html.")
    return refs


def extrair_data_relatorio(pdf):
    primeira = pdf.pages[0].extract_text(x_tolerance=1, y_tolerance=3) or ""
    m = re.search(r"Consulta de estoque admin\s*-\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", primeira)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%d/%m/%Y %H:%M").isoformat()


def atualizar():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {PDF_PATH}")

    refs = referencias_do_site()
    aliases_inversos = {v: k for k, v in ALIASES_REF.items()}

    # Todos os produtos do site entram no JSON. Assim, se uma referência
    # desaparecer do relatório (estoque zerado), ela fica explicitamente vazia
    # e não volta a funcionar como estoque ilimitado.
    estoque = {ref: {} for ref in refs}
    produto_atual = None
    cor_atual = None

    with pdfplumber.open(PDF_PATH) as pdf:
        atualizado_em = extrair_data_relatorio(pdf)

        for page in pdf.pages:
            texto = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            for linha in texto.splitlines():
                # Só uma referência conhecida do catálogo pode iniciar um
                # novo produto. Isso evita confundir "10 - PANTERA" com uma
                # referência chamada 10.
                inicio = re.match(r"^([^ ]+)\s+-\s+", linha)
                if inicio:
                    candidato = inicio.group(1)
                    if candidato in estoque:
                        produto_atual = candidato
                        cor_atual = None
                    elif candidato in aliases_inversos:
                        produto_atual = aliases_inversos[candidato]
                        cor_atual = None

                if not produto_atual:
                    continue

                # Procura uma das cores conhecidas na linha.
                encontrou_cor = False
                for codigo, nome_cor in COR_CODIGOS.items():
                    padrao = rf"(?<![A-Z0-9]){re.escape(codigo)}\s+-\s+{re.escape(nome_cor.upper())}\s+(\d+)(?=\s|$)"
                    m = re.search(padrao, linha)
                    if m:
                        cor_atual = nome_cor
                        estoque[produto_atual].setdefault(cor_atual, {})
                        resto = linha[m.end():]
                        encontrou_cor = True
                        break
                else:
                    resto = linha

                if not cor_atual:
                    continue

                for m in TAMANHO_RE.finditer(resto):
                    tamanho = NORMALIZAR_TAMANHO.get(m.group(1), m.group(1))
                    quantidade = int(m.group(3))
                    if quantidade > 0:
                        estoque[produto_atual][cor_atual][tamanho] = quantidade

    # Remove cores vazias.
    for ref in list(estoque):
        for cor in list(estoque[ref]):
            if not estoque[ref][cor]:
                del estoque[ref][cor]

    total = sum(
        quantidade
        for produto in estoque.values()
        for cor in produto.values()
        for quantidade in cor.values()
    )

    resultado = {
        "updated_at": atualizado_em or datetime.now().astimezone().isoformat(),
        "source": PDF_PATH.name,
        "total_available": total,
        "products": estoque,
    }

    JSON_PATH.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Estoque atualizado: {JSON_PATH}")
    print(f"Referências do catálogo: {len(refs)}")
    print(f"Total disponível no catálogo: {total}")


if __name__ == "__main__":
    atualizar()
