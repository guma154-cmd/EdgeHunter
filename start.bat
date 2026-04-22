@echo off
echo [EdgeHunter] Iniciando sistema...

:: Iniciar Backend Flask
echo [1/2] Iniciando backend Flask na porta 5000...
start cmd /k "cd /d %~dp0backend && ..\venv\Scripts\python run.py"

:: Aguardar backend iniciar
timeout /t 3 /nobreak >nul

:: Iniciar Frontend Vite
echo [2/2] Iniciando frontend React na porta 5173...
start cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo [EdgeHunter] Sistema iniciado!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
echo.
pause
