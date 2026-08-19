@echo off
echo ============================================
echo  Atualizando estoque do site (Bella Moda Intima)
echo ============================================

where py >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=py
    goto rodar
)

where python >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python
    goto rodar
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python3
    goto rodar
)

echo Nao encontrei o Python instalado neste computador.
echo Instale o Python em https://www.python.org/downloads/ e rode o instalar.bat.
pause
exit /b 1

:rodar
if not exist relatorios\estoque.pdf (
    echo.
    echo ATENCAO: coloque o PDF do relatorio "Consulta de estoque" do Dapic
    echo em relatorios\estoque.pdf antes de continuar.
    echo.
    pause
    exit /b 1
)

%PYCMD% atualizar_estoque.py relatorios\estoque.pdf

echo.
pause
