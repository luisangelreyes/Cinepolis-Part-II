@echo off
echo ==============================================
echo  INICIANDO PROYECTO CINEPOLIS
echo ==============================================

echo Iniciando Backend (FastAPI)...
start "Backend - Cinepolis" cmd /k "cd backend && uvicorn main:app --reload"

echo Iniciando Frontend (Vite)...
start "Frontend - Cinepolis" cmd /k "cd cinepolis-frontend\cinepolis-frontend && pnpm dev"

echo.
echo Todo se esta iniciando en ventanas separadas.
echo - Backend correra en http://localhost:8000
echo - Frontend correra en http://localhost:5173
echo.
pause
