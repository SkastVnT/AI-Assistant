@echo off
echo ================================================================
echo   SETUP RAG SERVICES VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho RAG Services...
echo Moi truong nay su dung Retrieval-Augmented Generation
echo.

cd /d "i:\AI-Assistant\RAG Services"

REM Create venv
echo [1/4] Dang tao virtual environment venv_rag...
python -m venv venv_rag
echo [OK] Da tao venv_rag
echo.

REM Activate venv
echo [2/4] Dang kich hoat venv_rag...
call venv_rag\Scripts\activate.bat
echo [OK] Da kich hoat venv_rag
echo.

REM Upgrade pip
echo [3/4] Dang nang cap pip...
python -m pip install --upgrade pip
echo [OK] Da nang cap pip
echo.

REM Install common RAG dependencies
echo [4/4] Dang cai cac dependencies cua RAG Services...
pip install flask>=3.0.0 flask-cors>=4.0.0 python-dotenv>=1.0.0
pip install langchain>=0.1.0 chromadb>=0.4.0 sentence-transformers>=2.2.0
pip install google-generativeai>=0.3.0
echo [OK] Da cai tat ca dependencies
echo.

REM Verify installation
echo ================================================================
echo   KIEM TRA CAI DAT
echo ================================================================
python -c "import flask; import langchain; print('Flask: OK'); print('LangChain: OK')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_rag
echo.
echo De khoi dong RAG Services:
echo   cd "i:\AI-Assistant\RAG Services"
echo   venv_rag\Scripts\activate.bat
echo.
echo FEATURES:
echo   - Document Retrieval
echo   - Vector Embeddings
echo   - Context-Aware Question Answering
echo.
pause
