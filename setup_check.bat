@echo off
echo ============================================
echo  ScanStation - System Check
echo ============================================
echo.
set ERRORS=0

echo Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   OK: %%i
) else (
    echo   FAIL: Python not found. Install from https://www.python.org/downloads/
    echo         Make sure to tick "Add Python to PATH" during install.
    set /a ERRORS+=1
)

echo.
echo Checking Tesseract OCR...
tesseract --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=1,2" %%a in ('tesseract --version 2^>^&1') do (
        if "%%a"=="tesseract" echo   OK: Tesseract %%b
    )
) else (
    echo   FAIL: Tesseract not found. Install from:
    echo         https://github.com/UB-Mannheim/tesseract/wiki
    echo         Then add C:\Program Files\Tesseract-OCR\ to your PATH.
    set /a ERRORS+=1
)

echo.
echo Checking ImageMagick...
magick --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo   OK: ImageMagick available on PATH
) else (
    echo   FAIL: ImageMagick not found. Install from:
    echo         https://imagemagick.org/script/download.php^#windows
    echo         Tick Add to system path during install.
    set /a ERRORS+=1
)

echo.
echo Checking OCRmyPDF...
ocrmypdf --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%i in ('ocrmypdf --version 2^>^&1') do echo   OK: OCRmyPDF %%i
) else (
    echo   FAIL: OCRmyPDF not found. Run: pip install ocrmypdf
    set /a ERRORS+=1
)

echo.
echo Checking openpyxl...
python -c "import openpyxl; print('  OK: openpyxl', openpyxl.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   FAIL: openpyxl not found. Run: pip install openpyxl
    set /a ERRORS+=1
)

echo.
echo Checking deploy folder - same directory as this script...
if exist "%~dp0auto_ocr_watch.py" (
    echo   OK: auto_ocr_watch.py found next to setup_check.bat
) else (
    echo   FAIL: auto_ocr_watch.py not found: "%~dp0auto_ocr_watch.py"
    echo         Run this script from your deploy root - folder containing the pipeline files.
    set /a ERRORS+=1
)

echo.
echo Checking Templates...
if exist "%~dp0Templates\tenancy_agreement.json" (
    echo   OK: Templates folder has document type templates
) else (
    echo   WARN: No templates found at "%~dp0Templates\tenancy_agreement.json"
    echo         The system will use a fallback template.
)

echo.
echo Checking Flask (API server)...
python -c "import flask; print('  OK: Flask', flask.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   FAIL: Flask not found. Run: pip install flask
    set /a ERRORS+=1
)

echo.
echo Checking flask-cors...
python -c "import flask_cors; print('  OK: flask-cors')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   FAIL: flask-cors not found. Run: pip install flask-cors
    set /a ERRORS+=1
)

echo.
echo Checking pdfminer.six...
python -c "import pdfminer; print('  OK: pdfminer.six')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   FAIL: pdfminer.six not found. Run: pip install pdfminer.six
    set /a ERRORS+=1
)

echo.
echo ============================================
if %ERRORS% == 0 (
    echo  ALL CHECKS PASSED - System is ready!
    echo  Double-click Start_System_v2.bat to begin.
) else (
    echo  %ERRORS% issues found - Fix the items above
    echo  then run this check again.
)
echo ============================================
echo.
pause
