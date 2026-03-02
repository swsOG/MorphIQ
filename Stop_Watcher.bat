@echo off
echo Stopping ScanStation watcher...
taskkill /FI "WINDOWTITLE eq ScanStation Watcher" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq auto_ocr_watch" /F >nul 2>&1
echo Done.
pause
