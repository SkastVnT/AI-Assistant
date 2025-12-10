@echo off
REM Batch generation script - Generate samples for all trained LoRAs

echo ========================================
echo Batch Sample Generation
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
call venv\Scripts\activate.bat

echo.
echo Searching for trained LoRA models...
echo.

REM Find all LoRA models in outputs
set model_dir=outputs\lora_models
if not exist %model_dir% (
    echo No trained models found in %model_dir%
    pause
    exit /b 1
)

REM List available models
echo Available LoRA models:
dir /b %model_dir%\*.safetensors
echo.

set /p model_name="Enter LoRA model filename: "
set lora_path=%model_dir%\%model_name%

if not exist %lora_path% (
    echo Model not found: %lora_path%
    pause
    exit /b 1
)

echo.
echo Choose prompt set:
echo 1. Character prompts (prompts\character_prompts.txt)
echo 2. Style prompts (prompts\style_prompts.txt)
echo 3. Custom prompts file
echo 4. Enter prompts manually
echo.

set /p prompt_choice="Enter choice (1-4): "

set prompts_file=
set manual_prompts=

if "%prompt_choice%"=="1" set prompts_file=prompts\character_prompts.txt
if "%prompt_choice%"=="2" set prompts_file=prompts\style_prompts.txt
if "%prompt_choice%"=="3" (
    set /p prompts_file="Enter path to prompts file: "
)
if "%prompt_choice%"=="4" (
    echo.
    echo Enter prompts (one per line, type 'done' when finished):
    set manual_prompts=
    :manual_loop
    set /p prompt_line="Prompt: "
    if /i "%prompt_line%"=="done" goto generate_start
    set manual_prompts=%manual_prompts% "%prompt_line%"
    goto manual_loop
)

:generate_start
echo.
echo ========================================
echo Generating Samples
echo ========================================
echo LoRA: %lora_path%

if not "%prompts_file%"=="" (
    echo Prompts: %prompts_file%
    python generate_samples.py --lora_path %lora_path% --prompts_file %prompts_file% --steps 30 --cfg_scale 7.5
) else (
    python generate_samples.py --lora_path %lora_path% --prompts %manual_prompts% --steps 30 --cfg_scale 7.5
)

echo.
echo ========================================
echo Generation Complete!
echo ========================================
echo Samples saved to: outputs\samples\
echo.
pause
