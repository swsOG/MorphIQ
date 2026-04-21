@echo off

cd /d "%~dp0"

set "PYTHON_CMD="
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if %ERRORLEVEL% == 0 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if %ERRORLEVEL% == 0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    echo ERROR: Python not found. Run setup_check.bat and install/configure Python first.
    pause
    exit /b 1
)

if exist ".env" (
    for /f "tokens=1,* delims==" %%a in ('findstr /i "ANTHROPIC_API_KEY" .env') do set ANTHROPIC_API_KEY=%%b
)

echo ============================================

echo  ScanStation v2 — Starting System

echo ============================================

echo.

:: Start the document watcher in a minimized window

echo Starting document watcher...

start "ScanStation Watcher" /min cmd /c ""%PYTHON_CMD%" auto_ocr_watch.py"

:: Start the API server in a minimized window

echo Starting API server on http://127.0.0.1:8765 ...

start "ScanStation API" /min cmd /c ""%PYTHON_CMD%" server.py"

:: Start the MorphIQ portal (portal_new) in a minimized window

echo Starting MorphIQ portal on http://127.0.0.1:5000 ...

start "MorphIQ Portal" /min cmd /c ""%PYTHON_CMD%" portal_new\app.py"

:: Wait for background services to start

timeout /t 3 /nobreak >nul

:: Open ScanStation in default browser

echo Opening ScanStation in browser...

start "" scan_station.html

echo.

echo System is running:

echo   - Watcher:    processing documents in background

echo   - API Server: http://127.0.0.1:8765

echo   - Portal:     http://127.0.0.1:5000 (MorphIQ client viewer)

echo   - ScanStation: open in browser

echo.

echo To stop everything, run Stop_System.bat

echo ============================================

pause
