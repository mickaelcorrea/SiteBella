# Atualização automática de estoque — Bella Moda Íntima

Este pacote atualiza o site (bellamodaintima.com.br) com o estoque que sai do
relatório "Consulta de estoque" do sistema Dapic, todos os dias.

## Instalação (só precisa fazer uma vez)

1. Extraia esta pasta em algum lugar fixo do computador (ex: `Documentos\SiteBella-automacao-estoque`).
2. Dê dois cliques em **`instalar.bat`**. Ele instala a dependência necessária (`pdfplumber`).
3. Confirme que a pasta `SiteBella` (o repositório clonado do GitHub) está configurada
   com o `git` já autenticado (push funcionando), como combinamos.

## Uso diário

1. No Dapic, gere o relatório **"Consulta de estoque"** em PDF.
2. Salve esse PDF como `relatorios\estoque.pdf`, substituindo o anterior.
3. Dê dois cliques em **`atualizar_estoque.bat`**.
4. O script vai:
   - Ler o PDF e calcular o novo estoque por produto/cor/tamanho;
   - Atualizar o `index.html` do site (sem mexer em preço, nome, foto ou frases);
   - Mostrar um resumo do que mudou (cores/tamanhos removidos, avisos, etc.);
   - Fazer commit e push automaticamente para o GitHub (o site atualiza sozinho
     em 1–2 minutos via GitHub Pages).

## Muito importante — preços

O script **nunca** mexe em preço. Os preços "oficiais" ficam em
`dados\catalogo_master.json`. Se precisar mudar um preço, altere nesse
arquivo (campo `preco` e `precoPlus`) — **não edite o preço direto no
`index.html`**, porque na próxima atualização de estoque o script vai usar
o preço do `catalogo_master.json` outra vez.

## Cadastrando produto/cor/tamanho novo

O script só ESCONDE ou MOSTRA cores/tamanhos que já existem no
`catalogo_master.json`, baseado no estoque do Dapic. Ele nunca inventa uma
cor ou tamanho novo sozinho. Se uma cor nova aparecer no Dapic e você quiser
vender ela no site, adicione essa cor na lista `cores` do produto
correspondente em `dados\catalogo_master.json`. O script sempre avisa, no
resumo final, quando encontra estoque de uma cor que ainda não está
cadastrada.

## Se der algum erro

- Copie a mensagem de erro que apareceu na tela (pode tirar print) e me envie.
- O relatório PDF precisa ser o "Consulta de estoque" padrão do Dapic — outros
  relatórios não têm o formato esperado.
