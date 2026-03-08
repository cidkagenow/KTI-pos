@echo off
echo ========================================
echo  KTI-POS Deploy
echo ========================================
echo.

:: Pull latest code
echo [1/3] Pulling latest code...
git pull origin main
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: git pull failed
    pause
    exit /b 1
)
echo.

:: Run tests
echo [2/3] Running tests...
cd backend
.venv\Scripts\python -m pytest tests/ -v --tb=short
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo  TESTS FAILED - DEPLOY ABORTED
    echo ========================================
    echo Fix the failing tests before deploying.
    cd ..
    pause
    exit /b 1
)
echo.

:: Restart the server
echo [3/3] Restarting server...
taskkill /F /IM uvicorn.exe 2>nul
start /B .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..

echo.
echo ========================================
echo  DEPLOY SUCCESS - All tests passed
echo ========================================
pause
