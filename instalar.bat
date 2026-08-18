@echo off
cd /d "%~dp0"
echo Instalando dependencias (isso so precisa ser feito uma vez)...

python -m pip install -r requirements.txt
if errorlevel 9009 goto tentapy
goto fim

:tentapy
echo Comando python nao encontrado, tentando com py...
py -m pip install -r requirements.txt
if errorlevel 9009 goto tentapy3
goto fim

:tentapy3
echo Comando py nao encontrado, tentando com python3...
python3 -m pip install -r requirements.txt
if errorlevel 9009 goto semPython
goto fim

:semPython
echo(
echo ===================================================
echo  ERRO: Python nao foi encontrado neste computador.
echo ===================================================
echo(
echo  1) Baixe e instale o Python em python.org/downloads
echo  2) Na instalacao, marque a opcao Add python.exe to PATH
echo     antes de clicar em Install.
echo  3) Depois de instalar, feche esta janela e rode
echo     instalar.bat de novo.
echo(
echo  Se voce ja tem Python instalado e ainda ve esta mensagem,
echo  o Windows pode estar redirecionando o comando python para
echo  a Microsoft Store. Va em Configuracoes, Aplicativos,
echo  Configuracoes avancadas do aplicativo, Aliases de
echo  execucao do aplicativo, e desligue o python.exe.
echo(
goto pausar

:fim
echo(
echo Pronto! Agora use o atualizar_estoque.bat todos os dias.

:pausar
pause
