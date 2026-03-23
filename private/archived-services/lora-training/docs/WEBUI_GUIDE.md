# 🌐 LoRA Training WebUI

## Overview

Web-based interface for LoRA training with real-time monitoring, similar to Stable Diffusion WebUI.

**Features:**
- 🎨 Modern dark theme UI
- ⚡ Real-time training monitoring with Socket.IO
- 📊 Live charts for loss and learning rate
- 🏷️ Integrated WD14 tagger
- ⚙️ Interactive configuration editor
- 📝 Live training logs
- 💾 Save/load configurations

## Quick Start

### Windows
```bash
start_webui.bat
```

### Linux/Mac
```bash
chmod +x start_webui.sh
./start_webui.sh
```

### Manual
```bash
# Activate venv
.\lora\Scripts\activate  # Windows
source ./lora/bin/activate  # Linux/Mac

# Install dependencies
pip install flask flask-socketio flask-cors python-socketio eventlet

# Start WebUI
python webui.py
```

## Access

Open your browser to:
```
http://127.0.0.1:7860
```

## Usage

### 1. **Dataset Tab**
- Select dataset from dropdown
- Auto-tag with WD14 tagger
- Analyze dataset quality
- Set validation split ratio

### 2. **Model Tab**
- Choose base model (SD 1.5, SD 2.1, SDXL)
- Set LoRA rank and alpha
- Configure architecture

### 3. **Training Tab**
- Set learning rate and epochs
- Choose optimizer (AdamW, Prodigy, Lion)
- Configure batch size

### 4. **Advanced Tab**
- Enable LoRA+ (2-3x faster)
- Enable Min-SNR weighting
- Enable EMA
- Choose loss type (MSE, Huber, Scheduled Huber)
- Set noise offset

### 5. **Start Training**
- Click "▶️ Start Training"
- Monitor real-time progress
- View live metrics and charts
- Check logs for details

## Features

### Real-Time Monitoring

**Progress Bar:**
- Current epoch and step
- Total progress percentage
- ETA estimation

**Metrics Dashboard:**
- Current loss value
- Learning rate
- GPU memory usage
- Training speed

**Live Charts:**
- Loss curve over time
- Learning rate schedule
- Auto-updating graphs

**Live Logs:**
- Real-time training output
- Error messages
- Status updates
- Auto-scroll option

### Configuration Management

**Load Config:**
- Load from existing YAML files
- Pre-filled form fields
- Quick configuration switching

**Save Config:**
- Save current settings
- Create named configs
- Reuse for future training

### Dataset Tools

**WD14 Auto-Tagging:**
- One-click tagging
- Adjustable threshold
- Progress tracking
- NSFW-safe (100% local)

**Dataset Analysis:**
- Image count
- Average resolution
- Caption coverage
- Quality scoring

## API Endpoints

### GET Endpoints

- `/` - Main WebUI page
- `/api/configs` - List available configs
- `/api/config/<name>` - Get specific config
- `/api/datasets` - List datasets
- `/api/models` - List base models
- `/api/status` - Current training status
- `/api/logs` - Training logs

### POST Endpoints

- `/api/start_training` - Start training
- `/api/stop_training` - Stop training
- `/api/config/<name>` - Save config
- `/api/tag_dataset` - Run WD14 tagger
- `/api/analyze_dataset` - Analyze dataset

### WebSocket Events

- `connect` - Client connected
- `disconnect` - Client disconnected
- `training_update` - Training progress update
- `log` - New log entry
- `request_update` - Request current state

## Configuration

### Command Line Arguments

```bash
python webui.py [OPTIONS]

Options:
  --host HOST       Host to bind to (default: 127.0.0.1)
  --port PORT       Port to bind to (default: 7860)
  --share           Create public URL (gradio share)
  --debug           Enable debug mode
```

### Examples

**Local only:**
```bash
python webui.py
```

**Accessible from network:**
```bash
python webui.py --host 0.0.0.0 --port 7860
```

**Public URL (requires ngrok or similar):**
```bash
python webui.py --share
```

**Debug mode:**
```bash
python webui.py --debug
```

## Architecture

```
webui.py              # Flask + Socket.IO server
├── webui/
│   ├── templates/
│   │   └── index.html      # Main UI template
│   └── static/
│       ├── css/
│       │   └── style.css   # Dark theme styles
│       └── js/
│           └── main.js     # Socket.IO client + UI logic
├── start_webui.bat         # Windows launcher
└── start_webui.sh          # Linux/Mac launcher
```

## Technology Stack

**Backend:**
- Flask - Web framework
- Flask-SocketIO - WebSocket support
- Eventlet - Async WSGI server

**Frontend:**
- Vanilla JavaScript (no frameworks)
- Socket.IO client
- Chart.js for graphs
- Modern CSS (dark theme)

## Browser Support

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

## Performance

**Optimizations:**
- Async training thread
- Efficient data streaming
- Chart data limiting (last 100 points)
- Log limiting (last 1000 entries)
- No animation on charts for performance

## Troubleshooting

### WebUI won't start

```bash
# Check if port is in use
netstat -ano | findstr :7860  # Windows
lsof -i :7860  # Linux/Mac

# Try different port
python webui.py --port 7861
```

### Can't connect to WebUI

```bash
# Check firewall settings
# Ensure 127.0.0.1:7860 is accessible

# Try network access
python webui.py --host 0.0.0.0
```

### Training doesn't start

- Check dataset path is valid
- Ensure virtual environment is activated
- Check logs for error messages
- Verify GPU is available

### Real-time updates not working

- Refresh browser page
- Check browser console for errors
- Verify Socket.IO connection
- Try different browser

## Security Notes

**Local Use (Default):**
- Binds to 127.0.0.1 (localhost only)
- Safe for personal use
- No external access

**Network Access:**
- Use `--host 0.0.0.0` with caution
- Only on trusted networks
- Consider authentication if exposed

**Public Access:**
- Not recommended for sensitive datasets
- Use VPN or SSH tunnel instead
- Be aware of privacy implications

## Comparison with CLI

| Feature | WebUI | CLI |
|---------|-------|-----|
| Ease of use | ✅✅✅ | ⚠️ |
| Real-time monitoring | ✅ | ⚠️ |
| Live charts | ✅ | ❌ |
| Configuration | ✅ GUI | YAML |
| Dataset tools | ✅ Integrated | Separate scripts |
| Accessibility | Browser | Terminal |
| Remote access | ✅ Easy | SSH required |

## Tips & Best Practices

### 1. **Monitor Training**
- Keep WebUI open during training
- Watch loss curve for anomalies
- Check logs for errors
- Monitor GPU memory

### 2. **Configuration**
- Start with presets
- Save working configs
- Test with small datasets first
- Document changes

### 3. **Performance**
- Close unused tabs
- Disable auto-scroll if slow
- Clear logs periodically
- Use recommended browsers

### 4. **Workflow**
1. Prepare dataset
2. Auto-tag with WD14
3. Analyze quality
4. Configure training
5. Start and monitor
6. Save successful configs

## Future Enhancements

Planned features:
- [ ] Sample image generation during training
- [ ] TensorBoard integration
- [ ] Multi-GPU support UI
- [ ] Training presets library
- [ ] Dataset augmentation preview
- [ ] Model comparison tools
- [ ] Export training report
- [ ] Mobile responsive design

## Support

For issues:
1. Check browser console (F12)
2. Check terminal/logs
3. Verify dependencies installed
4. Try different browser
5. Restart WebUI

## Credits

Inspired by:
- Stable Diffusion WebUI
- Automatic1111 WebUI
- Kohya SS GUI

---

**🎉 Enjoy the modern WebUI for LoRA training!**

Access: http://127.0.0.1:7860
