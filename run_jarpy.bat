@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: 1. DEPENDENCY CHECK
:: Ensures the 'requests' library for Python is installed.
:: ============================================================================
echo [*] Checking for required Python library 'requests'...
python -c "import requests" 2>nul
if errorlevel 1 (
    echo [!] 'requests' not found. Attempting to install via pip...
    python -m pip install requests
    if errorlevel 1 (
        echo.
        echo [X] ERROR: Failed to install 'requests'.
        echo Please install it manually: python -m pip install requests
        echo.
        pause
        exit /b
    )
) else (
    echo [+] 'requests' is already installed.
)

:: ============================================================================
:: 2. SCRIPT EXECUTION
:: Gathers user input and calls the Python script with the correct arguments.
:: ============================================================================
echo.
echo Jarpy Decompiler and Archiver
echo ===============================

set "SCRIPT_NAME=jarpy.py"
if "%~1"=="" (
    echo [X] ERROR: Drag and drop a FOLDER containing .jar files onto this script.
    pause
    exit /b
)
if not exist "%~1\" (
    echo [X] ERROR: The item you dragged is not a valid folder.
    pause
    exit /b
)

set "INPUT_FOLDER=%~1"

:: --- User Interface ---
echo.
echo Target Folder: "!INPUT_FOLDER!"
echo.
echo Select archiving mode:
echo   1. Context Mode (Separate folder for each JAR)
echo   2. Direct Mode  (Separate folder for each JAR)
echo   3. Combined Context (All JARs merged into one folder)
echo.
set "MODE_CHOICE="
choice /c 123 /n /m "Enter your choice (1, 2, or 3): "

set "FINAL_ARGS="

if errorlevel 3 (
    set "ZIP_MODE=combined context"
    set "FINAL_ARGS="!INPUT_FOLDER!" --combine --mode context"
) else if errorlevel 2 (
    set "ZIP_MODE=direct"
    set "FINAL_ARGS="!INPUT_FOLDER!" --mode direct"
) else (
    set "ZIP_MODE=context"
    set "FINAL_ARGS="!INPUT_FOLDER!" --mode context"
)

echo.
echo --- Starting Python Script in !ZIP_MODE! mode ---
echo.

python "%~dp0%SCRIPT_NAME%" !FINAL_ARGS!

echo.
echo --- Script Finished ---
pause
endlocal

