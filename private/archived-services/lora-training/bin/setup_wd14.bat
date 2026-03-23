@echo off
echo ========================================
echo WD14 Tagger Setup for NSFW Datasets
echo 100%% Local, Private, No Internet Upload
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install WD14 dependencies
echo.
echo Installing WD14 Tagger dependencies...
echo This may take a few minutes on first run...
echo.

pip install --upgrade pip
pip install onnxruntime huggingface-hub pillow numpy

echo.
echo ========================================
echo ✓ WD14 Tagger Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Put your images in data/train/ folder
echo 2. Run: python scripts/utilities/wd14_tagger.py --input data/train
echo 3. Tags will be saved as .txt files next to images
echo.
echo Privacy guaranteed:
echo - All processing happens locally
echo - Images never leave your computer
echo - No internet upload required (after first model download)
echo - NSFW content fully supported
echo.
pause
