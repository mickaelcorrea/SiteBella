@echo off
echo ============================================
echo  Instalando dependencias (SiteBella - Estoque)
echo ============================================

where py >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=py
    goto instalar
)

where python >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python
    goto instalar
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python3
    goto instalar
)

echo Nao encontrei o Python instalado neste computador.
echo Instale o Python em https://www.python.org/downloads/ e tente novamente.
pause
exit /b 1

:instalar
echo Usando: %PYCMD%
%PYCMD% -m pip install -r requirements.txt

echo.
echo Instalacao concluida! Voce ja pode usar o atualizar_estoque.bat
pause
