pip install torchcodec

@echo off
REM ============================================================================
REM VistralS2T - FFmpeg Installation Script (Windows)
REM Purpose: Install FFmpeg to fix torchcodec audio loading error
REM ============================================================================

echo.
echo ================================================================================
echo  FFmpeg Installation for VistralS2T
echo ================================================================================
echo.

REM Check if running in app\s2t venv
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please activate the virtual environment first:
    echo         .\app\s2t\Scripts\activate
    echo.
    pause
    exit /b 1
)

REM Check FFmpeg installation
echo [1/5] Checking existing FFmpeg installation...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] FFmpeg already installed!
    ffmpeg -version | findstr "ffmpeg version"
    echo.
    echo Do you want to reinstall FFmpeg? (y/n)
    set /p REINSTALL=
    if /i not "%REINSTALL%"=="y" (
        echo Skipping FFmpeg installation.
        goto :CHECK_TORCHCODEC
    )
)

echo.
echo [2/5] Installing FFmpeg via Chocolatey...
echo.
echo Chocolatey is a Windows package manager. Installing FFmpeg...
echo.

REM Check if Chocolatey is installed
where choco >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Chocolatey not found. Installing Chocolatey first...
    echo This requires Administrator privileges.
    echo.
    
    REM Install Chocolatey (requires admin)
    powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install Chocolatey.
        echo Please install FFmpeg manually:
        echo 1. Download from: https://www.gyan.dev/ffmpeg/builds/
        echo 2. Extract to C:\ffmpeg
        echo 3. Add C:\ffmpeg\bin to PATH
        echo.
        pause
        exit /b 1
    )
    
    echo [OK] Chocolatey installed successfully!
    echo Refreshing environment variables...
    call refreshenv
)

REM Install FFmpeg using Chocolatey
echo Installing FFmpeg...
choco install ffmpeg -y

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] FFmpeg installation failed.
    echo.
    echo MANUAL INSTALLATION STEPS:
    echo 1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
    echo 2. Choose "ffmpeg-release-full.7z"
    echo 3. Extract to C:\ffmpeg
    echo 4. Add C:\ffmpeg\bin to System PATH:
    echo    - Open System Properties ^> Environment Variables
    echo    - Edit PATH variable
    echo    - Add: C:\ffmpeg\bin
    echo 5. Restart your terminal
    echo.
    pause
    exit /b 1
)

echo [OK] FFmpeg installed successfully!
echo.

REM Refresh environment variables
echo [3/5] Refreshing environment variables...
call refreshenv

REM Verify FFmpeg installation
echo [4/5] Verifying FFmpeg installation...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] FFmpeg not found in PATH.
    echo Please restart your terminal and run this script again.
    pause
    exit /b 1
)

echo [OK] FFmpeg version:
ffmpeg -version | findstr "ffmpeg version"
echo.

:CHECK_TORCHCODEC
echo [5/5] Checking torchcodec installation...
python -c "import torchcodec; print('TorchCodec version:', torchcodec.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] TorchCodec not installed. Installing...
    pip install torchcodec>=0.1.0
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install torchcodec.
        echo Please run: pip install torchcodec
        pause
        exit /b 1
    )
    
    echo [OK] TorchCodec installed successfully!
) else (
    echo [OK] TorchCodec already installed!
)

echo.
echo ================================================================================
echo  Installation Complete!
echo ================================================================================
echo.
echo FFmpeg and TorchCodec are now installed.
echo You can now run PhoWhisper without audio loading errors.
echo.
echo Next steps:
echo 1. Configure HuggingFace token in .env file (for diarization)
echo 2. Run: .\start_webui.bat
echo.
pause
