@echo off

cd /d "%~dp0"

for /f "tokens=1,* delims==" %%a in ('findstr /i "ANTHROPIC_API_KEY" .env') do set ANTHROPIC_API_KEY=%%b

echo ============================================

echo  ScanStation v2 — Starting System

echo ============================================

echo.

:: Start the document watcher in a minimized window

echo Starting document watcher...

start "ScanStation Watcher" /min python auto_ocr_watch.py

:: Start the API server in a minimized window

echo Starting API server on http://127.0.0.1:8765 ...

start "ScanStation API" /min python server.py

:: Start the MorphIQ portal (portal_new) in a minimized window

echo Starting MorphIQ portal on http://127.0.0.1:5000 ...

start "MorphIQ Portal" /min python portal_new\app.py

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