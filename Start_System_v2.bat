@echo off
cd /d C:\ScanSystem_v2

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

:: Wait for both to start
timeout /t 3 /nobreak >nul

:: Open ScanStation in default browser
echo Opening ScanStation in browser...
start "" scan_station.html

echo.
echo System is running:
echo   - Watcher:    processing documents in background
echo   - API Server: http://127.0.0.1:8765
echo   - ScanStation: open in browser
echo.
echo To stop everything, run Stop_System.bat
echo ============================================
pause
