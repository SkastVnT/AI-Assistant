@echo off
echo ========================================
echo   Starting All AI Assistant Services
echo ========================================
echo.
echo This will start all services in separate windows:
echo   - Hub Gateway (Port 8080)
echo   - ChatBot (Port 5000)
echo   - Speech2Text (Port 5001)
echo   - Text2SQL (Port 5002)
echo.
pause

echo Starting Hub Gateway...
start "AI Hub Gateway" cmd /k "python hub.py"
timeout /t 3

echo Starting ChatBot Service...
start "ChatBot Service" cmd /k "cd ChatBot && python app.py"
timeout /t 3

echo Starting Speech2Text Service...
start "Speech2Text Service" cmd /k "cd Speech2Text Services\app && python web_ui.py --port 5001"
timeout /t 3

echo Starting Text2SQL Service...
start "Text2SQL Service" cmd /k "cd Text2SQL Services && python app.py --port 5002"

echo.
echo ========================================
echo   All Services Started!
echo ========================================
echo.
echo Open your browser and go to:
echo   http://localhost:8080
echo.
echo Press any key to exit this window...
pause > nul
