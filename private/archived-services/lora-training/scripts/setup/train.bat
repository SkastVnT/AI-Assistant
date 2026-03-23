@echo off
REM Training script for LoRA models
REM Automatically activates virtual environment and starts training

echo ========================================
echo LoRA Training Tool - Start Training
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if config file is specified
set CONFIG_FILE=configs\default_config.yaml

if "%1" NEQ "" (
    set CONFIG_FILE=%1
)

echo.
echo Configuration: %CONFIG_FILE%
echo.

REM Check if config file exists
if not exist %CONFIG_FILE% (
    echo ERROR: Configuration file not found: %CONFIG_FILE%
    echo.
    echo Available configurations:
    dir /b configs\*.yaml
    echo.
    echo Usage: train.bat [config_file]
    echo Example: train.bat configs\small_dataset_config.yaml
    pause
    exit /b 1
)

echo Starting training...
echo.
echo ========================================
echo.

REM Start training
python train_lora.py --config %CONFIG_FILE%

if errorlevel 1 (
    echo.
    echo ========================================
    echo Training failed with errors!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Training completed successfully!
echo ========================================
echo.
echo Check outputs/lora_models for trained models
echo Check outputs/logs for training logs
echo.
pause
