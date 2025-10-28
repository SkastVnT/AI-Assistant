#!/bin/bash

echo "========================================"
echo "  Starting All AI Assistant Services"
echo "========================================"
echo ""
echo "This will start all services:"
echo "  - Hub Gateway (Port 8080)"
echo "  - ChatBot (Port 5000)"
echo "  - Speech2Text (Port 5001)"
echo "  - Text2SQL (Port 5002)"
echo ""

# Start Hub Gateway
echo "Starting Hub Gateway..."
python3 hub.py &
HUB_PID=$!
sleep 3

# Start ChatBot
echo "Starting ChatBot Service..."
cd ChatBot && python3 app.py &
CHATBOT_PID=$!
cd ..
sleep 3

# Start Speech2Text
echo "Starting Speech2Text Service..."
cd "Speech2Text Services/app" && python3 web_ui.py --port 5001 &
SPEECH_PID=$!
cd ../..
sleep 3

# Start Text2SQL
echo "Starting Text2SQL Service..."
cd "Text2SQL Services" && python3 app.py --port 5002 &
TEXT2SQL_PID=$!
cd ..

echo ""
echo "========================================"
echo "  All Services Started!"
echo "========================================"
echo ""
echo "Open your browser and go to:"
echo "  http://localhost:8080"
echo ""
echo "Process IDs:"
echo "  Hub: $HUB_PID"
echo "  ChatBot: $CHATBOT_PID"
echo "  Speech2Text: $SPEECH_PID"
echo "  Text2SQL: $TEXT2SQL_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap "kill $HUB_PID $CHATBOT_PID $SPEECH_PID $TEXT2SQL_PID 2>/dev/null; exit" INT
wait
