@echo off
echo ================================================================
echo   SETUP ALL VIRTUAL ENVIRONMENTS - AI ASSISTANT
echo ================================================================
echo.
echo Script nay se tao 6 virtual environments cho tat ca cac dich vu:
echo   1. venv_chatbot        - ChatBot + Local Models (PyTorch 2.4.0)
echo   2. venv_sd             - Stable Diffusion (PyTorch 2.0.1)
echo   3. venv_dis            - Document Intelligence (PaddleOCR + Gemini)
echo   4. venv_text2sql       - Text2SQL Services (Gemini + DB)
echo   5. venv_s2t            - Speech2Text (Whisper + PhoWhisper)
echo   6. venv_rag            - RAG Services (LangChain + ChromaDB)
echo.
echo Thoi gian du kien: 30-60 phut (tuy toc do mang)
echo.
echo Luu y: Ban co the setup tung dich vu rieng le bang cach:
echo   - Nhan Ctrl+C de dung va chon setup rieng le
echo   - Hoac cho script chay tu dong setup tat ca
echo.
pause

REM Setup ChatBot venv
echo.
echo ================================================================
echo   BUOC 1/6: SETUP CHATBOT VENV
echo ================================================================
cd /d i:\AI-Assistant\ChatBot
if exist scripts\setup_venv_chatbot.bat (
    call scripts\setup_venv_chatbot.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_chatbot.bat
)

echo.
echo Nhan phim bat ky de tiep tuc voi Stable Diffusion setup...
pause > nul

REM Setup Stable Diffusion venv
echo.
echo ================================================================
echo   BUOC 2/6: SETUP STABLE DIFFUSION VENV
echo ================================================================
cd /d i:\AI-Assistant\stable-diffusion-webui
if exist setup_venv_sd.bat (
    call setup_venv_sd.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_sd.bat
)

echo.
echo Nhan phim bat ky de tiep tuc voi Document Intelligence setup...
pause > nul

REM Setup Document Intelligence venv
echo.
echo ================================================================
echo   BUOC 3/6: SETUP DOCUMENT INTELLIGENCE VENV
echo ================================================================
cd /d "i:\AI-Assistant\Document Intelligence Service"
if exist scripts\setup_venv_dis.bat (
    call scripts\setup_venv_dis.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_dis.bat
)

echo.
echo Nhan phim bat ky de tiep tuc voi Text2SQL setup...
pause > nul

REM Setup Text2SQL venv
echo.
echo ================================================================
echo   BUOC 4/6: SETUP TEXT2SQL VENV
echo ================================================================
cd /d "i:\AI-Assistant\Text2SQL Services"
if exist scripts\setup_venv_text2sql.bat (
    call scripts\setup_venv_text2sql.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_text2sql.bat
)

echo.
echo Nhan phim bat ky de tiep tuc voi Speech2Text setup...
pause > nul

REM Setup Speech2Text venv
echo.
echo ================================================================
echo   BUOC 5/6: SETUP SPEECH2TEXT VENV
echo ================================================================
cd /d "i:\AI-Assistant\Speech2Text Services"
if exist scripts\setup_venv_s2t.bat (
    call scripts\setup_venv_s2t.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_s2t.bat
)

echo.
echo Nhan phim bat ky de tiep tuc voi RAG Services setup...
pause > nul

REM Setup RAG Services venv
echo.
echo ================================================================
echo   BUOC 6/6: SETUP RAG SERVICES VENV
echo ================================================================
cd /d "i:\AI-Assistant\RAG Services"
if exist scripts\setup_venv_rag.bat (
    call scripts\setup_venv_rag.bat
) else (
    echo [ERROR] Khong tim thay setup_venv_rag.bat
)

echo.
echo ================================================================
echo   HOAN THANH TAT CA!
echo ================================================================
echo.
echo Da setup xong 6 virtual environments:
echo   [OK] i:\AI-Assistant\ChatBot\venv_chatbot
echo   [OK] i:\AI-Assistant\stable-diffusion-webui\venv_sd
echo   [OK] i:\AI-Assistant\Document Intelligence Service\venv_dis
echo   [OK] i:\AI-Assistant\Text2SQL Services\venv_text2sql
echo   [OK] i:\AI-Assistant\Speech2Text Services\venv_s2t
echo   [OK] i:\AI-Assistant\RAG Services\venv_rag
echo.
echo De khoi dong cac dich vu, vao thu muc tuong ung va:
echo.
echo CHATBOT:
echo   cd i:\AI-Assistant\ChatBot
echo   venv_chatbot\Scripts\activate.bat
echo   python app.py
echo.
echo STABLE DIFFUSION:
echo   cd i:\AI-Assistant\stable-diffusion-webui
echo   venv_sd\Scripts\activate.bat
echo   python webui.py --api --xformers
echo.
echo DOCUMENT INTELLIGENCE:
echo   cd "i:\AI-Assistant\Document Intelligence Service"
echo   venv_dis\Scripts\activate.bat
echo   python app.py
echo.
echo TEXT2SQL:
echo   cd "i:\AI-Assistant\Text2SQL Services"
echo   venv_text2sql\Scripts\activate.bat
echo   python app.py
echo.
echo SPEECH2TEXT:
echo   cd "i:\AI-Assistant\Speech2Text Services"
echo   venv_s2t\Scripts\activate.bat
echo   python app.py
echo.
echo RAG SERVICES:
echo   cd "i:\AI-Assistant\RAG Services"
echo   venv_rag\Scripts\activate.bat
echo.
pause
