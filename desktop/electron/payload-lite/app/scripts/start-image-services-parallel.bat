@echo off
chcp 65001 >nul 2>&1

cd /d "%~dp0.."

if not exist "venv-image\Scripts\python.exe" (
    echo [ERROR] venv-image not found. Please create/install image profile first.
    echo Run: pyenv exec python -m venv venv-image ^&^& venv-image\Scripts\python -m pip install -r requirements\profile_image_ai_services.txt
    pause
    exit /b 1
)

echo ==================================================
echo   Start Image-AI Services (Parallel)
echo   Environment: venv-image (except dedicated local env services)
echo ==================================================

start "image-upscale" cmd /k "cd /d services\image-upscale && set PYTHONPATH=%CD%\src;%PYTHONPATH% && ..\..\venv-image\Scripts\python.exe -m upscale_tool.app"
start "lora-training" cmd /k "cd /d services\lora-training && ..\..\venv-image\Scripts\python.exe webui.py --port 7862"

rem Stable Diffusion uses its own internal venv under services\stable-diffusion\venv
if exist "services\stable-diffusion\webui.bat" (
    start "stable-diffusion" cmd /k "cd /d services\stable-diffusion && set PYTHON=%CD%\venv\Scripts\python.exe && call webui.bat --port 7861 --api --skip-python-version-check --skip-torch-cuda-test --no-half"
)

rem Edit Image currently manages its own local venv in services\edit-image\venv
if exist "services\edit-image\run_grok_ui.py" (
    start "edit-image-grok" cmd /k "cd /d services\edit-image && if not exist venv\Scripts\python.exe (python -m venv venv && call venv\Scripts\activate && pip install -r requirements.txt) else (call venv\Scripts\activate) && python run_grok_ui.py"
)

echo [OK] Image services launched in separate terminals.
echo Stable Diffusion: http://127.0.0.1:7861
echo LoRA Training: http://127.0.0.1:7862
echo Image Upscale: http://127.0.0.1:7863
echo Edit Image (Grok UI): http://127.0.0.1:7860
