@echo off
echo Stopping ScanStation system...

:: Stop the watcher
taskkill /FI "WINDOWTITLE eq ScanStation Watcher" /F >nul 2>&1

:: Stop the API server
taskkill /FI "WINDOWTITLE eq ScanStation API" /F >nul 2>&1

echo.
echo All ScanStation processes stopped.
pause
