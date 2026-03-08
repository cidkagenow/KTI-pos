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

:: Run tests inside docker
echo [2/3] Running tests...
docker compose run --rm --no-deps backend python -m pytest tests/ -v --tb=short
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo  TESTS FAILED - DEPLOY ABORTED
    echo ========================================
    echo Fix the failing tests before deploying.
    pause
    exit /b 1
)
echo.

:: Rebuild and restart
echo [3/3] Rebuilding and restarting...
docker compose up -d --build
echo.
echo ========================================
echo  DEPLOY SUCCESS - All tests passed
echo ========================================
pause
