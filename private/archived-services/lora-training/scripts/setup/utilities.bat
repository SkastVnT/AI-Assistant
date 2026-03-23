@echo off
REM Advanced LoRA utilities menu

echo ========================================
echo LoRA Advanced Utilities
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

:menu
echo.
echo Choose a utility:
echo 1. Resume training from checkpoint
echo 2. Generate samples with trained LoRA
echo 3. Analyze LoRA model
echo 4. Merge multiple LoRAs
echo 5. Merge LoRA into base model
echo 6. Exit
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto resume
if "%choice%"=="2" goto generate
if "%choice%"=="3" goto analyze
if "%choice%"=="4" goto merge_loras
if "%choice%"=="5" goto merge_base
if "%choice%"=="6" goto end

echo Invalid choice!
goto menu

:resume
echo.
echo ========================================
echo Resume Training
echo ========================================
echo.
set /p checkpoint_dir="Enter checkpoint directory (default: outputs/checkpoints): "
if "%checkpoint_dir%"=="" set checkpoint_dir=outputs/checkpoints

python resume_training.py --checkpoint_dir %checkpoint_dir%
echo.
pause
goto menu

:generate
echo.
echo ========================================
echo Generate Samples
echo ========================================
echo.
set /p lora_path="Enter LoRA model path: "
set /p num_samples="Number of samples to generate: "

echo.
echo Enter prompts (one per line, empty line to finish):
set prompts=
:prompt_loop
set /p prompt="Prompt: "
if "%prompt%"=="" goto generate_exec
set prompts=%prompts% "%prompt%"
goto prompt_loop

:generate_exec
echo.
echo Generating samples...
python generate_samples.py --lora_path %lora_path% --prompts %prompts%
echo.
pause
goto menu

:analyze
echo.
echo ========================================
echo Analyze LoRA Model
echo ========================================
echo.
set /p lora_path="Enter LoRA model path: "
set /p detailed="Show detailed layer info? (y/n): "
set /p weights="Analyze weight distribution? (y/n): "

set args=
if /i "%detailed%"=="y" set args=%args% --detailed
if /i "%weights%"=="y" set args=%args% --weights

python analyze_lora.py %lora_path% %args%
echo.
pause
goto menu

:merge_loras
echo.
echo ========================================
echo Merge Multiple LoRAs
echo ========================================
echo.
echo Enter LoRA paths and weights (e.g., lora1.safetensors 0.5)
echo Empty line to finish
echo.

set lora_paths=
set lora_weights=

:merge_loop
set /p lora_input="LoRA path and weight: "
if "%lora_input%"=="" goto merge_exec

REM Split input into path and weight
for /f "tokens=1,2" %%a in ("%lora_input%") do (
    set lora_paths=%lora_paths% %%a
    set lora_weights=%lora_weights% %%b
)
goto merge_loop

:merge_exec
set /p output_path="Output path for merged LoRA: "
if "%output_path%"=="" set output_path=outputs/lora_models/merged_lora.safetensors

python merge_lora.py merge_loras --loras %lora_paths% --weights %lora_weights% --output %output_path%
echo.
pause
goto menu

:merge_base
echo.
echo ========================================
echo Merge LoRA into Base Model
echo ========================================
echo.
set /p base_model="Base model path: "
set /p lora_path="LoRA model path: "
set /p output_path="Output path for merged model: "
set /p alpha="LoRA strength (default: 1.0): "
if "%alpha%"=="" set alpha=1.0

python merge_lora.py merge_to_base --base_model %base_model% --lora %lora_path% --output %output_path% --alpha %alpha%
echo.
pause
goto menu

:end
echo.
echo ========================================
echo Goodbye!
echo ========================================
pause
