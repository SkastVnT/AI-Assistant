@echo off
echo ============================================
echo   KHOI DONG STABLE DIFFUSION - NO INSTALL
echo   (Skip installation, chay truc tiep)
echo ============================================
echo.

cd i:\AI-Assistant\stable-diffusion-webui

echo QUAN TRONG: Script nay se KHONG cai dat lai dependencies
echo Chi khoi dong SD voi nhung gi da co san
echo.
echo Neu thieu dependencies, se bao loi va can cai them
echo.
echo Dang khoi dong...
echo.

REM Skip prepare environment completely
python webui.py --api --xformers --no-half-vae --disable-safe-unpickle --skip-prepare-environment --skip-version-check --skip-torch-cuda-test

pause
