@echo off
REM Quick start script - Interactive setup and training

echo ========================================
echo LoRA Training Tool - Quick Start
echo ========================================
echo.

echo This script will guide you through setting up and training a LoRA model.
echo.
pause

REM Step 1: Setup
if not exist venv (
    echo [Step 1/5] Setting up environment...
    call setup.bat
    if errorlevel 1 exit /b 1
) else (
    echo [Step 1/5] Environment already set up. Skipping...
)

echo.
echo ========================================

REM Step 2: Check dataset
echo [Step 2/5] Dataset Check
echo.
echo Please ensure your dataset is prepared in one of these locations:
echo   - data\train\  (training images and .txt caption files)
echo   - data\val\    (optional validation images)
echo.
set /p dataset_ready="Is your dataset ready? (y/n): "

if /i not "%dataset_ready%"=="y" (
    echo.
    echo Please prepare your dataset first:
    echo 1. Create folder: data\train
    echo 2. Add your images (.jpg, .png, etc.)
    echo 3. Add caption files (.txt) with same name as images
    echo.
    echo Example:
    echo   data\train\image1.jpg
    echo   data\train\image1.txt  (contains: "a photo of sks person")
    echo.
    pause
    exit /b 0
)

echo.
echo ========================================

REM Step 3: Validate dataset
echo [Step 3/5] Dataset Validation
echo.
set /p validate_dataset="Would you like to validate your dataset? (y/n): "

if /i "%validate_dataset%"=="y" (
    call venv\Scripts\activate.bat
    python -m utils.preprocessing --data_dir data\train --action validate --fix
)

echo.
echo ========================================

REM Step 4: Choose configuration
echo [Step 4/5] Choose Configuration
echo.
echo Available configurations:
echo 1. Small dataset (500-1000 images) - More epochs, lower rank
echo 2. Default (1000-1500 images) - Balanced settings
echo 3. Large dataset (1500-2000+ images) - Fewer epochs, higher rank
echo 4. SDXL (high resolution training)
echo 5. Custom (you provide config file path)
echo.

set /p config_choice="Enter your choice (1-5): "

set CONFIG_FILE=configs\default_config.yaml

if "%config_choice%"=="1" set CONFIG_FILE=configs\small_dataset_config.yaml
if "%config_choice%"=="2" set CONFIG_FILE=configs\default_config.yaml
if "%config_choice%"=="3" set CONFIG_FILE=configs\large_dataset_config.yaml
if "%config_choice%"=="4" set CONFIG_FILE=configs\sdxl_config.yaml
if "%config_choice%"=="5" (
    set /p CONFIG_FILE="Enter path to your config file: "
)

echo.
echo Using configuration: %CONFIG_FILE%
echo.
set /p edit_config="Would you like to edit the configuration? (y/n): "

if /i "%edit_config%"=="y" (
    notepad %CONFIG_FILE%
)

echo.
echo ========================================

REM Step 5: Start training
echo [Step 5/5] Start Training
echo.
echo Configuration: %CONFIG_FILE%
echo.
echo Training will start now. This may take several hours depending on:
echo   - Dataset size
echo   - Number of epochs
echo   - GPU performance
echo.
set /p start_training="Start training now? (y/n): "

if /i not "%start_training%"=="y" (
    echo Training cancelled.
    pause
    exit /b 0
)

echo.
echo ========================================
echo Starting Training...
echo ========================================
echo.

call train.bat %CONFIG_FILE%

echo.
echo ========================================
echo Quick Start Complete!
echo ========================================
echo.
echo Your trained LoRA model can be found in:
echo   outputs\lora_models\
echo.
echo To use it:
echo 1. Copy the .safetensors file to your SD WebUI models\Lora folder
echo 2. Use in prompt: ^<lora:model_name:0.8^>
echo.
pause
