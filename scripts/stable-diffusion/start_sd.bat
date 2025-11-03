@echo off
echo ================================================================
echo   START STABLE DIFFUSION WEB UI
echo   Fixed for PyTorch 2.4.0 + CUDA 12.1
echo ================================================================
echo.

cd /d "I:\AI-Assistant\stable-diffusion-webui"

REM Activate virtual environment
call venv_sd\Scripts\activate.bat

echo Starting Stable Diffusion WebUI...
echo.
echo Notes:
echo   - xformers warnings can be ignored (model will use fallback optimization)
echo   - API errors are non-critical if you're not using the API
echo.
echo WebUI will be available at: http://127.0.0.1:7860
echo API will be available at: http://127.0.0.1:7860/docs
echo.

REM Start without xformers flag due to version conflicts
REM Use Doggettx optimization instead (fallback, works fine)
python webui.py --api --no-half-vae --skip-prepare-environment --skip-version-check --opt-sdp-attention

pause
