@echo off
echo ========================================
echo Quick NSFW Dataset Tagging
echo ========================================
echo.

REM Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    echo Please run setup_wd14.bat first
    pause
    exit /b 1
)

REM Check if data/train exists
if not exist "data\train\" (
    echo Creating data/train directory...
    mkdir data\train
    echo.
    echo Please put your images in data\train\ folder
    echo Then run this script again
    pause
    exit /b 0
)

REM Count images
echo Scanning for images in data/train/...
echo.

REM Run WD14 tagger
echo Starting WD14 Tagger...
echo Model: SwinV2 (best accuracy)
echo Threshold: 0.35 (balanced - good tags without spam)
echo Format: Danbooru-style tags
echo.

python scripts/utilities/wd14_tagger.py ^
    --input data/train ^
    --model swinv2 ^
    --threshold 0.35 ^
    --prefix "masterpiece, best quality" ^
    --verbose

echo.
echo ========================================
echo ✓ Tagging Complete!
echo ========================================
echo.
echo Your captions are saved as .txt files in data/train/
echo.
echo Next: Train your LoRA
echo   python scripts/training/train_lora.py --config configs/loraplus_config.yaml
echo.
pause
