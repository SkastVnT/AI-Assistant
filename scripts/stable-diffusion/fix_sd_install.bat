@echo off
echo ============================================
echo   FIX STABLE DIFFUSION INSTALLATION
echo ============================================
echo.
echo Dang sua loi protobuf conflict...
echo.

REM Stop any running Python processes
taskkill /F /IM python.exe 2>nul

echo Cho 2 giay...
timeout /t 2 /nobreak

echo.
echo Gỡ protobuf cu...
pip uninstall protobuf -y

echo.
echo Cai dat lai protobuf phien ban tuong thich...
pip install protobuf==4.25.3

echo.
echo Cai dat lai google-generativeai...
pip install --upgrade google-generativeai==0.8.5

echo.
echo ============================================
echo   DA SUA LOI!
echo ============================================
echo.
echo Bay gio chay lai: start_stable_diffusion_api.bat
echo.
pause
