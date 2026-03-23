@echo off
REM Dataset validation and preprocessing script

echo ========================================
echo Dataset Preprocessing Tool
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
echo Choose an action:
echo 1. Validate dataset (check for corrupted/invalid images)
echo 2. Auto-generate captions using BLIP
echo 3. Split dataset into train/validation sets
echo 4. Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto validate
if "%choice%"=="2" goto caption
if "%choice%"=="3" goto split
if "%choice%"=="4" goto end

echo Invalid choice!
pause
exit /b 1

:validate
echo.
set /p data_dir="Enter dataset directory (e.g., data\train): "
set /p fix_issues="Fix issues automatically? (y/n): "

if /i "%fix_issues%"=="y" (
    python -m utils.preprocessing --data_dir %data_dir% --action validate --fix
) else (
    python -m utils.preprocessing --data_dir %data_dir% --action validate
)
goto end

:caption
echo.
set /p data_dir="Enter dataset directory (e.g., data\train): "
set /p prefix="Enter caption prefix (e.g., 'a photo of sks person'): "

python -m utils.preprocessing --data_dir %data_dir% --action caption --prefix "%prefix%"
goto end

:split
echo.
set /p data_dir="Enter source directory with all images: "
set /p val_ratio="Enter validation ratio (e.g., 0.1 for 10%%): "

python -m utils.preprocessing --data_dir %data_dir% --action split --val_ratio %val_ratio%
goto end

:end
echo.
echo ========================================
echo Preprocessing complete!
echo ========================================
echo.
pause
