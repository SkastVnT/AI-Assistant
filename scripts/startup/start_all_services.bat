@echo off
echo ================================================================
echo   START ALL AI ASSISTANT SERVICES
echo ================================================================
echo.
echo Script nay se khoi dong TAT CA cac services trong cac cua so rieng:
echo   1. Hub Gateway (Port 3000)
echo   2. ChatBot (Port 5000)
echo   3. Text2SQL (Port 5001)
echo   4. Speech2Text (Port 5002)
echo   5. Document Intelligence (Port 5003)
echo   6. RAG Services (Port 5004)
echo   7. Stable Diffusion (Port 7860)
echo.
echo Luu y: Moi service se chay trong terminal rieng
echo.
pause

REM Start Hub Gateway
echo [1/7] Starting Hub Gateway...
start "AI Hub (3000)" cmd /k "cd /d i:\AI-Assistant && scripts\startup\start_hub.bat"
timeout /t 3 > nul

REM Start ChatBot
echo [2/7] Starting ChatBot...
start "ChatBot (5000)" cmd /k "cd /d i:\AI-Assistant\ChatBot && venv_chatbot\Scripts\activate.bat && python app.py"
timeout /t 3 > nul

REM Start Text2SQL
echo [3/7] Starting Text2SQL...
start "Text2SQL (5001)" cmd /k "cd /d i:\AI-Assistant\Text2SQL Services && venv_text2sql\Scripts\activate.bat && python app.py"
timeout /t 3 > nul

REM Start Speech2Text
echo [4/7] Starting Speech2Text...
start "Speech2Text (5002)" cmd /k "cd /d i:\AI-Assistant\Speech2Text Services && venv_s2t\Scripts\activate.bat && python app.py"
timeout /t 3 > nul

REM Start Document Intelligence
echo [5/7] Starting Document Intelligence...
start "Document Intelligence (5003)" cmd /k "cd /d i:\AI-Assistant\Document Intelligence Service && venv_dis\Scripts\activate.bat && python app.py"
timeout /t 3 > nul

REM Start RAG Services
echo [6/7] Starting RAG Services...
start "RAG Services (5004)" cmd /k "cd /d i:\AI-Assistant\RAG Services && venv_rag\Scripts\activate.bat && python app.py"
timeout /t 3 > nul

REM Start Stable Diffusion
echo [7/7] Starting Stable Diffusion...
start "Stable Diffusion (7860)" cmd /k "cd /d i:\AI-Assistant\stable-diffusion-webui && venv_sd\Scripts\activate.bat && python webui.py --api --xformers"

echo.
echo ================================================================
echo   TAT CA SERVICES DANG KHOI DONG
echo ================================================================
echo.
echo Cac services dang duoc khoi dong trong cac cua so rieng.
echo Doi 30-60 giay de tat ca services khoi dong xong.
echo.
echo Sau do truy cap Hub tai:
echo   http://localhost:3000
echo.
echo De dung tat ca services, dong tat ca cac cua so terminal.
echo.
pause
