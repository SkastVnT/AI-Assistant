@echo off
echo ================================================================
echo   STARTING AI CHATBOT
echo ================================================================
echo.

REM Check if virtual environment exists
if not exist "venv_chatbot\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup_venv_chatbot.bat first
    pause
    exit /b 1
)

REM Check NumPy version
echo [1/3] Checking NumPy version...
call venv_chatbot\Scripts\activate.bat
python -c "import numpy; v=numpy.__version__; assert v.startswith('1.'), f'NumPy 2.x detected: {v}. Run: pip install numpy<2.0'; print(f'✅ NumPy {v}')" 2>nul
if errorlevel 1 (
    echo ⚠️  NumPy 2.x detected! Installing NumPy 1.x...
    pip install "numpy<2.0" --force-reinstall
)

echo.
echo [2/3] Checking Stable Diffusion WebUI...
powershell -Command "$response = Invoke-WebRequest -Uri 'http://127.0.0.1:7860' -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue; if ($response.StatusCode -eq 200) { Write-Host '✅ Stable Diffusion is running on port 7860' } else { Write-Host '⚠️  Stable Diffusion not detected. Image generation will be unavailable.' }" 2>nul
if errorlevel 1 (
    echo ⚠️  Stable Diffusion not detected. Image generation will be unavailable.
    echo.
    echo To start Stable Diffusion, run in another terminal:
    echo   cd I:\AI-Assistant\stable-diffusion-webui
    echo   .\webui-user.bat
    echo.
)

echo.
echo [3/3] Starting ChatBot Flask server...
echo ================================================================
echo   ChatBot will be available at:
echo   - Local:   http://127.0.0.1:5000
echo   - Network: http://192.168.1.14:5000 (if available)
echo.
echo   Press CTRL+C to stop the server
echo ================================================================
echo.

REM Start Flask app
python app.py

pause
