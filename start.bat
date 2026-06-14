@echo off
echo Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo Frontend build failed
    exit /b 1
)
cd ..
echo Starting server on http://localhost:8000
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
