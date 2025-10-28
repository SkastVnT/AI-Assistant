@echo off
echo ================================================================
echo   FIX STABLE DIFFUSION DEPENDENCIES
echo   Cai dat dung phien ban de tranh conflict
echo ================================================================
echo.

echo LUU Y: Script nay se:
echo 1. Downgrade numpy ve phien ban 1.x (tương thích torch 2.0.1)
echo 2. Downgrade pytorch-lightning ve phien ban tuong thich torch 2.0.1
echo 3. Cai dat pyre-extensions cho xformers
echo.
pause

echo [1/5] Downgrade numpy xuong phien ban 1.26.4...
pip install "numpy<2.0" --user --force-reinstall

echo.
echo [2/5] Downgrade pytorch-lightning xuong phien ban 1.9.5...
pip install pytorch-lightning==1.9.5 --user --force-reinstall

echo.
echo [3/5] Cai dat pyre-extensions cho xformers...
pip install pyre-extensions==0.0.29 --user

echo.
echo [4/5] Cai dat open-clip-torch (da co trong SD webui)...
pip install open-clip-torch==2.7.0 --user

echo.
echo [5/5] Kiem tra cac package quan trong...
pip list | findstr /i "torch numpy lightning gradio"

echo.
echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Da fix cac dependencies conflict:
echo   - numpy: 2.2.6 ^> 1.26.4 (tuong thich torch 2.0.1)
echo   - pytorch-lightning: 2.5.5 ^> 1.9.5 (tuong thich torch 2.0.1)
echo   - pyre-extensions: da cai dat cho xformers
echo.
echo Bay gio thu khoi dong Stable Diffusion:
echo   .\scripts\stable-diffusion\start_sd_no_install.bat
echo.
pause
