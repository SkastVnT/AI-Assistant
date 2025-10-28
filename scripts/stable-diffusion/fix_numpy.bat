@echo off
echo ================================================================
echo   FIX STABLE DIFFUSION - DOWNGRADE NUMPY
echo ================================================================
echo.

echo Dang downgrade numpy xuong 1.23.5...
pip uninstall numpy -y
pip install numpy==1.23.5 --user

echo.
echo Kiem tra phien ban numpy:
python -c "import numpy; print('NumPy version:', numpy.__version__)"

echo.
echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
pause
