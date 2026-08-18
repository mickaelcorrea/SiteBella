# Atualização automática de estoque (Dapic -> site)

Este pacote atualiza o `index.html` do seu site (Bella Moda Íntima) todos os
dias com base no relatório de estoque do Dapic, e já sobe (`git push`) a
atualização pro GitHub.

## Como funciona, resumindo

1. Você exporta o relatório **Consulta de Estoque** do Dapic em PDF.
2. Salva esse PDF sempre no mesmo lugar: `relatorios/estoque.pdf` (substituindo
   o do dia anterior).
3. Clica duas vezes em `atualizar_estoque.bat`.
4. O script lê o PDF e atualiza DUAS coisas no `index.html`:
   - quais tamanhos/cores aparecem como opção em cada produto;
   - a quantidade exata disponível de cada combinação cor/tamanho (o número
     que trava o seletor de quantidade e valida o carrinho no site).
5. Ele reescreve o `index.html` e já faz commit + push pro GitHub.
6. Em poucos minutos o GitHub Pages publica a versão nova do site.

## Passo a passo detalhado

### 1) Instalação (só na primeira vez)

- Copie todos os arquivos deste pacote para dentro da pasta do seu projeto
  `SiteBella` (a mesma pasta onde já está o `index.html` e a pasta `imagens`).
- Você precisa ter o **Python** instalado (baixe em python.org se não tiver,
  marcando a opção "Add python.exe to PATH" na instalação).
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
  produtos, tamanhos e cores que a loja oferece hoje. Esse arquivo é a fonte
  da verdade sobre o que EXISTE (nome, preço, tamanhos e cores possíveis).
  Ele só deve ser editado manualmente quando você cadastrar um produto, cor
  ou tamanho **novo** que ainda não existe no site.
- Todo dia, o script cruza esse catálogo completo com a coluna "Real" do
  relatório do Dapic e decide o que fica visível:
  - Se uma **cor** não tem estoque em nenhum tamanho, ela some das opções
    daquele produto.
  - Se um **tamanho** não tem estoque em nenhuma cor, ele some das opções.
  - Se o produto inteiro zerar, ele some do catálogo do site.
  - Se uma referência do site **não aparecer** no relatório do Dapic (ex:
    produto desativado no Dapic), o script não mexe nela e avisa na tela,
    pra você decidir manualmente se ainda faz sentido ela estar no site.
- Além disso, o script preenche o `estoquePorCorTamanho` com a quantidade
  exata de cada combinação cor/tamanho que sobrou — é esse número que trava
  o "+" da quantidade no site e bloqueia o "Adicionar" quando não tem
  estoque suficiente.
- Se o Dapic tiver estoque de uma cor que **nunca foi cadastrada** no
  `catalogo_master.json` daquele produto, o script NÃO adiciona ela
  sozinho — só avisa no resumo ("Cores com estoque no Dapic que NÃO estão
  cadastradas"). Você decide se vale a pena cadastrar essa cor (confirmar
  que tem foto, preço certo etc.) antes de colocar pra vender.

### Sobre a precisão

Diferente da primeira versão deste script, agora a trava de quantidade usa
o número exato por cor+tamanho (não uma aproximação). A lista de "quais
tamanhos/cores aparecem como botão" ainda segue a regra de "sumir se
zerar em TODOS os tamanhos/todas as cores" — isso é intencional, é só pra
decidir o que aparece como opção clicável; o número real de peças
disponíveis em cada combinação específica já está certo no
`estoquePorCorTamanho`.

## Arquivos deste pacote

- `dapic_parser.py` — lê o PDF do Dapic e extrai a quantidade (Real e
  Disponível) por produto/cor/tamanho.
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
- 0142-L — Camisola Longa Liganete c/ Renda
- 2231-L — Short Doll Liganete
- 4192-2 — Conjunto Bojo Inteiro Renda
