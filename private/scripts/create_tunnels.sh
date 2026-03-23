#!/bin/bash

echo "🌐 Creating Cloudflare tunnels..."

# Kill old tunnels
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 2

# Start tunnels
cloudflared tunnel --url http://localhost:5000 > /workspace/AI-Assistant/logs/tunnel-chatbot.log 2>&1 &
sleep 3
cloudflared tunnel --url http://localhost:8189 > /workspace/AI-Assistant/logs/tunnel-comfyui.log 2>&1 &
sleep 3
cloudflared tunnel --url http://localhost:5002 > /workspace/AI-Assistant/logs/tunnel-text2sql.log 2>&1 &
sleep 3
cloudflared tunnel --url http://localhost:5001 > /workspace/AI-Assistant/logs/tunnel-speech2text.log 2>&1 &

echo "⏳ Waiting 20 seconds for tunnels..."
sleep 20

# Extract URLs
echo ""
echo "==================================="
echo "🔗 PUBLIC URLS"
echo "==================================="

chatbot_url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-chatbot.log 2>/dev/null | head -1)
comfyui_url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-comfyui.log 2>/dev/null | head -1)
text2sql_url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-text2sql.log 2>/dev/null | head -1)
speech2text_url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-speech2text.log 2>/dev/null | head -1)

echo "chatbot: $chatbot_url"
echo "comfyui: $comfyui_url"
echo "text2sql: $text2sql_url"
echo "speech2text: $speech2text_url"
echo ""

# Save to file
cat > /workspace/AI-Assistant/public_urls.txt << EOF
chatbot: $chatbot_url
comfyui: $comfyui_url
text2sql: $text2sql_url
speech2text: $speech2text_url
EOF

echo "✅ URLs saved to: /workspace/AI-Assistant/public_urls.txt"
echo ""
echo "📋 Copy these URLs and send to me!"
