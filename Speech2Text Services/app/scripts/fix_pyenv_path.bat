@echo off
REM ============================================
REM Fix Pyenv PATH - VistralS2T
REM Run this if pyenv command not found
REM ============================================

echo [FIX] Fixing pyenv PATH issue...

REM Set environment variables
setx PYENV "%USERPROFILE%\.pyenv\pyenv-win\" >nul
setx PYENV_ROOT "%USERPROFILE%\.pyenv\pyenv-win\" >nul
setx PYENV_HOME "%USERPROFILE%\.pyenv\pyenv-win\" >nul

REM Add to PATH if not exists
powershell -Command "$currentPath = [System.Environment]::GetEnvironmentVariable('Path', 'User'); if ($currentPath -notlike '*pyenv*') { $newPath = \"$currentPath;%USERPROFILE%\.pyenv\pyenv-win\bin;%USERPROFILE%\.pyenv\pyenv-win\shims\"; [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'User'); Write-Host '[OK] PATH updated' } else { Write-Host '[OK] Pyenv already in PATH' }"

REM Temporary fix for current session
set PATH=%PATH%;%USERPROFILE%\.pyenv\pyenv-win\bin;%USERPROFILE%\.pyenv\pyenv-win\shims

echo.
echo [OK] Pyenv PATH fixed!
echo.
echo To verify, run: pyenv --version
echo.
echo NOTE: You may need to restart your terminal/IDE for changes to take effect.
echo.

pause
