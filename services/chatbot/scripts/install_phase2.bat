@echo off
REM Phase 2: Advanced Features - Installation Script
REM Installs all required dependencies for Phase 2 components

echo ========================================
echo Phase 2: Advanced Features Installation
echo ========================================
echo.

REM Check if virtual environment is activated
python -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 1)" 2>nul
if errorlevel 1 (
    echo ERROR: Virtual environment not activated!
    echo Please run: .\venv_chatbot\Scripts\activate
    pause
    exit /b 1
)

echo [1/6] Installing sentence-transformers for semantic search...
pip install sentence-transformers>=2.2.2
if errorlevel 1 (
    echo ERROR: Failed to install sentence-transformers
    pause
    exit /b 1
)

echo.
echo [2/6] Installing PyTorch for embeddings...
pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 (
    echo WARNING: CUDA version of PyTorch failed, trying CPU version...
    pip install torch>=2.0.0
)

echo.
echo [3/6] Installing Pillow for image processing...
pip install pillow>=10.0.0
if errorlevel 1 (
    echo ERROR: Failed to install Pillow
    pause
    exit /b 1
)

echo.
echo [4/6] Installing numpy for vector operations...
pip install numpy>=1.24.0
if errorlevel 1 (
    echo ERROR: Failed to install numpy
    pause
    exit /b 1
)

echo.
echo [5/6] Installing scikit-learn for additional ML features...
pip install scikit-learn>=1.3.0
if errorlevel 1 (
    echo WARNING: Failed to install scikit-learn (optional)
)

echo.
echo [6/6] Verifying installations...
python -c "import sentence_transformers; print(f'✅ sentence-transformers: {sentence_transformers.__version__}')"
python -c "import torch; print(f'✅ torch: {torch.__version__}')"
python -c "from PIL import Image; print('✅ Pillow: OK')"
python -c "import numpy; print(f'✅ numpy: {numpy.__version__}')"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next Steps:
echo 1. Test multimodal handler:
echo    python src/handlers/multimodal_handler.py
echo.
echo 2. Test advanced image generator:
echo    python src/handlers/advanced_image_gen.py
echo.
echo 3. Test conversation manager:
echo    python src/utils/conversation_manager.py
echo.
echo 4. Run integration tests:
echo    python test_phase2.py
echo.
echo Documentation: docs/PHASE2_PROGRESS.md
echo ========================================

pause
