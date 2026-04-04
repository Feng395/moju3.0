@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "PORT=8888"
cd /d "%SCRIPT_DIR%"

set "DEFAULT_MOJU_PYTHON=C:\Users\Wind\.conda\envs\moju\python.exe"
set "PYTHON_EXE="

if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" (
    set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"
)

if not defined PYTHON_EXE if exist "%DEFAULT_MOJU_PYTHON%" (
    set "PYTHON_EXE=%DEFAULT_MOJU_PYTHON%"
)

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

echo.
echo ========================================
echo   Start Speech Services
echo ========================================
echo.

if not defined PYTHON_EXE (
    echo [ERROR] Python was not found.
    echo [ERROR] Activate the moju conda environment or install Python first.
    pause
    exit /b 1
)

echo [INFO] Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo [ERROR] Failed to run Python.
    pause
    exit /b 1
)

echo.
echo [INFO] Checking FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] FFmpeg was not found in PATH.
    echo [WARN] Audio decoding may fail until FFmpeg is installed.
    echo [WARN] Install FFmpeg manually and add ffmpeg.exe to PATH.
    echo.
)

echo [INFO] Checking Python dependencies...
"%PYTHON_EXE%" -c "import whisper, torch" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Missing dependencies detected. Installing requirements...
    "%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [INFO] Requirements installed.
    echo.
)

echo [INFO] Runtime summary:
"%PYTHON_EXE%" -c "import torch; print('  torch=' + torch.__version__); print('  cuda=' + str(torch.version.cuda)); print('  cuda_available=' + str(torch.cuda.is_available())); print('  device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))"
if errorlevel 1 (
    echo [WARN] Failed to query torch runtime info.
)

echo.
echo [INFO] Checking port %PORT%...
powershell -NoProfile -Command "$conn = Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }; if ($conn) { exit 1 } else { exit 0 }" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Port %PORT% is already in use.
    echo [ERROR] Stop the existing service or change the port before starting again.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting Speech Services...
echo [INFO] Host: 0.0.0.0
echo [INFO] Port: %PORT%
echo [INFO] Model: small
echo [INFO] Docs: http://localhost:%PORT%/docs
echo [INFO] Press Ctrl+C to stop.
echo.

"%PYTHON_EXE%" "%SCRIPT_DIR%main.py" --host 0.0.0.0 --port %PORT% --model small %*

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [INFO] Speech Services exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
