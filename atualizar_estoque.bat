@echo off
cd /d "%~dp0"
echo ===================================================
echo  Atualizando estoque do site a partir do Dapic...
echo ===================================================

python atualizar_estoque.py
if errorlevel 9009 goto tentapy
goto fim

:tentapy
echo Comando python nao encontrado, tentando com py...
py atualizar_estoque.py
if errorlevel 9009 goto tentapy3
goto fim

:tentapy3
echo Comando py nao encontrado, tentando com python3...
python3 atualizar_estoque.py
if errorlevel 9009 goto semPython
goto fim

:semPython
echo(
echo ===================================================
echo  ERRO: Python nao foi encontrado neste computador.
echo ===================================================
echo(
echo  Rode o instalar.bat primeiro para ver como resolver.
echo(

:fim
echo(
echo ===================================================
echo  Terminado. Confira as mensagens acima.
echo ===================================================
pause
