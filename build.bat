@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Preparando entorno...
if not exist .venv-build (
    python -m venv .venv-build || goto :error
)
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt pyinstaller || goto :error

echo [2/3] Compilando...
pyinstaller --noconfirm --clean --onefile --windowed ^
    --name OptiSolver_Desktop gui.py || goto :error

echo [3/3] Listo.
echo Ejecutable: dist\OptiSolver_Desktop.exe
pause
exit /b 0

:error
echo.
echo Error durante la compilacion. Revisa los mensajes anteriores.
pause
exit /b 1