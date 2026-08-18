# Atualização automática de estoque (Dapic -> site)

Este pacote atualiza o `index.html` do seu site (Bella Moda Íntima) todos os
dias com base no relatório de estoque do Dapic, e já sobe (`git push`) a
atualização pro GitHub.

## Como funciona, resumindo

1. Você exporta o relatório **Consulta de Estoque** do Dapic em PDF.
2. Salva esse PDF sempre no mesmo lugar: `relatorios/estoque.pdf` (substituindo
   o do dia anterior).
3. Clica duas vezes em `atualizar_estoque.bat`.
4. O script lê o PDF, decide quais tamanhos/cores de cada produto continuam
   disponíveis, reescreve o `index.html` e já faz commit + push pro GitHub.
5. Em poucos minutos o GitHub Pages publica a versão nova do site.

## Passo a passo detalhado

### 1) Instalação (só na primeira vez)

- Copie todos os arquivos deste pacote para dentro da pasta do seu projeto
  `SiteBella` (a mesma pasta onde já está o `index.html` e a pasta `imagens`).
- Você precisa ter o **Python** instalado (baixe em python.org se não tiver,
  marcando a opção "Add Python to PATH" na instalação).
- Dê dois cliques em `instalar.bat` (só precisa fazer isso uma vez).

### 2) Todos os dias

1. No Dapic, vá em **Menu > Estoque > Consulta de estoque**.
2. Configure os filtros como no relatório que você me mandou:
   - Tipo do produto: Produto acabado
   - Exibir itens por: Produto, Cor e Tamanho
   - Considerar saldo zerado: **Sim**
   - Considerar produtos desativados: Não
3. Exporte/imprima esse relatório como PDF.
4. Salve o arquivo PDF dentro da pasta do projeto, em:
   `SiteBella/relatorios/estoque.pdf` (sempre com esse nome, substituindo o
   arquivo antigo).
5. Dê dois cliques em `atualizar_estoque.bat`.
6. Leia o resumo que aparece na tela (o que mudou, o que sumiu, avisos).
7. Pronto — o site já foi atualizado e enviado pro GitHub automaticamente.

Se preferir revisar antes de publicar, abra um terminal na pasta do projeto
e rode:
```
python atualizar_estoque.py --sem-git
```
Isso atualiza o `index.html` mas NÃO faz commit/push — você confere a
diferença no VS Code (aba "Source Control") e decide se quer subir.

## Como o script decide o que mostrar no site

- `dados/catalogo_master.json` é o "catálogo completo": a lista de TODOS os
  produtos, tamanhos e cores que a loja já ofereceu. Esse arquivo é a fonte
  da verdade sobre o que EXISTE (nome, preço, tamanhos e cores possíveis).
  Ele só deve ser editado manualmente quando você cadastrar um produto, cor
  ou tamanho **novo** que ainda não existe no site.
- Todo dia, o script cruza esse catálogo completo com o relatório do Dapic e
  decide o que fica visível:
  - Se uma **cor** não tem estoque em nenhum tamanho, ela some das opções
    daquele produto.
  - Se um **tamanho** não tem estoque em nenhuma cor, ele some das opções.
  - Se o produto inteiro zerar, ele some do catálogo do site.
  - Se uma referência do site **não aparecer** no relatório do Dapic (ex:
    produto desativado no Dapic), o script não mexe nela e avisa na tela,
    pra você decidir manualmente se ainda faz sentido ela estar no site.

### Uma limitação importante

O site guarda tamanhos e cores como duas listas separadas por produto (não
como uma grade tamanho×cor). Então a regra acima é uma aproximação: um
tamanho "P" só some se **nenhuma** cor tiver P em estoque, e uma cor só some
se **nenhum** tamanho dela tiver estoque. Ou seja, pode acontecer de o site
mostrar "P" e "Preto" como disponíveis mesmo que "P Preto" especificamente
esteja zerado (mas "P Branco" tenha estoque, por exemplo). Se no futuro você
quiser um controle exato por combinação de tamanho+cor, dá pra evoluir o
site pra isso — é uma mudança maior na estrutura do catálogo, me avise se
quiser fazer.

## Arquivos deste pacote

- `dapic_parser.py` — lê o PDF do Dapic e extrai a disponibilidade.
- `atualizar_estoque.py` — script principal (roda todo dia).
- `dados/catalogo_master.json` — catálogo completo (edite manualmente para
  produtos/cores/tamanhos novos).
- `relatorios/` — pasta onde você salva o PDF do dia (`estoque.pdf`).
- `requirements.txt` — dependência Python (pdfplumber).
- `instalar.bat` — instalação (uma vez só).
- `atualizar_estoque.bat` — uso diário.

## Referências do site que não apareceram no relatório mais recente

Essas referências existem no seu `index.html` mas não foram encontradas no
PDF que você me mandou (provavelmente estão desativadas no Dapic). Vale
conferir se ainda fazem sentido no site:

- CUECA-015 — Cueca Boxer Masculina
- 2243-1 — Top de Renda sem Bojo/Fecho
- 7081-1 — Sutiã Básico Micro c/ Barra
- 0142-L — Camisola Longa Liganete c/ Renda
- 2231-L — Short Doll Liganete
- 4192-2 — Conjunto Bojo Inteiro Renda
