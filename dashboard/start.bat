@echo off
echo Starting NiftyQuant Dashboard...
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API docs: http://localhost:8000/docs
echo.
start "NiftyQuant Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "NiftyQuant Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
