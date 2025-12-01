# ✅ LoRA Training WebUI Setup Complete!

## 🎉 What's New (v2.3.1)

### WebUI Features
- ✅ Flask + Socket.IO server (`webui.py`)
- ✅ Modern dark theme UI (`webui/templates/index.html`)
- ✅ Real-time monitoring with live charts
- ✅ Interactive configuration editor
- ✅ Integrated WD14 tagger
- ✅ Live training logs
- ✅ Windows launcher (`start_webui.bat`)
- ✅ Linux/Mac launcher (`start_webui.sh`)

### Dependencies Installed
- ✅ flask 3.1.2
- ✅ flask-socketio 5.5.1
- ✅ flask-cors 6.0.1
- ✅ python-socketio 5.15.0
- ✅ eventlet 0.40.4
- ✅ Chart.js (CDN)

## 🚀 How to Start

### Method 1: Batch Script (Easiest)
```bash
.\start_webui.bat
```

### Method 2: Python Direct
```bash
# Activate venv first
.\lora\Scripts\Activate.ps1

# Run WebUI
python webui.py
```

### Method 3: Custom Port
```bash
python webui.py --port 7861
```

## 🌐 Access WebUI

Once started, open your browser to:
```
http://127.0.0.1:7860
```

## 📋 WebUI Interface

### Left Panel: Configuration
- **Dataset Tab**: Select dataset, auto-tag, analyze
- **Model Tab**: Choose base model, set LoRA rank/alpha
- **Training Tab**: Learning rate, epochs, batch size, optimizer
- **Advanced Tab**: LoRA+, Min-SNR, EMA, loss type, noise offset

### Right Panel: Monitoring
- **Progress Bar**: Real-time epoch/step progress
- **Metrics**: Loss, Learning Rate, ETA, GPU memory
- **Charts**: Live loss curve and LR schedule
- **Logs**: Real-time training output with auto-scroll

### Action Buttons
- ▶️ **Start Training**: Begin training with current config
- ⏹️ **Stop Training**: Stop current training
- 📁 **Load Config**: Load from YAML file
- 💾 **Save Config**: Save current settings

## 🎯 Quick Workflow

1. **Open WebUI** → `start_webui.bat`
2. **Select Dataset** → Choose from dropdown
3. **Auto-Tag (Optional)** → Click "🏷️ Auto-Tag with WD14"
4. **Configure** → Set model, training params, advanced features
5. **Start Training** → Click "▶️ Start Training"
6. **Monitor** → Watch real-time progress, charts, logs
7. **Done!** → Trained LoRA saved in `output/`

## 🔧 Features

### Real-Time Updates
- ⚡ Socket.IO connection
- 📊 Live charts (Chart.js)
- 📈 Progress tracking
- 🔄 Auto-refresh every 5s

### Integrated Tools
- 🏷️ WD14 Tagger (NSFW-safe, local)
- 📊 Dataset quality analyzer
- 💾 Config save/load
- 📝 Log viewer with download

### Configuration
- 🎨 Dark theme (Stable Diffusion style)
- ⚙️ All v2.3 features accessible
- 📋 Pre-configured presets
- 💡 Smart defaults

## 🆚 WebUI vs CLI

| Feature | WebUI | CLI |
|---------|-------|-----|
| Ease of use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Real-time monitoring | ✅ | ⚠️ |
| Live charts | ✅ | ❌ |
| WD14 integration | ✅ | Script |
| Remote access | ✅ | SSH |
| Configuration | GUI | YAML |
| Logs | Live view | Terminal |

## 📂 File Structure

```
train_LoRA_tool/
├── webui.py                    # Flask server (NEW)
├── start_webui.bat             # Windows launcher (NEW)
├── start_webui.sh              # Linux launcher (NEW)
├── webui/
│   ├── templates/
│   │   └── index.html          # Main UI (NEW)
│   └── static/
│       ├── css/
│       │   └── style.css       # Dark theme (NEW)
│       └── js/
│           └── main.js         # Socket.IO client (NEW)
├── data/
│   └── train/                  # Your datasets
├── configs/
│   └── *.yaml                  # Configuration files
└── output/                     # Trained LoRAs
```

## 🔒 Security Notes

**Default (Safe):**
- Binds to `127.0.0.1` (localhost only)
- No external access
- Safe for NSFW content

**Network Access:**
```bash
python webui.py --host 0.0.0.0  # Accessible from LAN
```
⚠️ Only use on trusted networks!

## 📱 Remote Access

### Option 1: SSH Tunnel (Recommended)
```bash
ssh -L 7860:localhost:7860 user@remote-server
# Access via: http://localhost:7860
```

### Option 2: Ngrok
```bash
ngrok http 7860
# Get public URL
```

⚠️ Not recommended for NSFW content!

## ⚡ Performance

**Optimizations:**
- Async training thread (non-blocking)
- Efficient Socket.IO streaming
- Chart data limiting (last 100 points)
- Log limiting (last 1000 entries)
- No animation on chart updates

**Recommended:**
- Modern browser (Chrome/Edge)
- Keep WebUI tab active
- Close unused tabs
- Good internet (for remote access)

## 🐛 Troubleshooting

### WebUI won't start
```bash
# Check if venv activated
.\lora\Scripts\Activate.ps1

# Reinstall dependencies
pip install flask flask-socketio flask-cors python-socketio eventlet

# Try different port
python webui.py --port 7861
```

### Can't access WebUI
```bash
# Check if running
# Browser → http://127.0.0.1:7860

# Check firewall
# Windows Defender → Allow Python

# Try localhost alternatives
http://localhost:7860
http://127.0.0.1:7860
```

### Training won't start
- ✅ Check dataset path exists
- ✅ Verify venv activated
- ✅ Check browser console (F12)
- ✅ Review logs for errors

### Real-time updates not working
- 🔄 Refresh page (Ctrl+R)
- 🔌 Check Socket.IO connection (green dot)
- 🌐 Try different browser
- 📡 Check network connectivity

## 💡 Tips

### 1. Monitor Training
- Watch loss curve for convergence
- Check logs for errors/warnings
- Monitor GPU memory usage
- Save working configs

### 2. Optimize Performance
- Close unused browser tabs
- Disable auto-scroll if slow
- Clear logs periodically
- Use recommended browsers

### 3. Save Configurations
- Save successful configs
- Name descriptively
- Document changes
- Share with team

### 4. Dataset Preparation
- Use WD14 tagger first
- Analyze quality before training
- Review first few captions
- Adjust threshold if needed

## 🎓 Next Steps

### For Beginners
1. ✅ Read `WD14_QUICKSTART.md`
2. ✅ Prepare small test dataset (10-20 images)
3. ✅ Tag with WD14 via WebUI
4. ✅ Start with default config
5. ✅ Monitor training
6. ✅ Test generated LoRA

### For Advanced Users
1. ✅ Read `docs/WEBUI_GUIDE.md` (detailed)
2. ✅ Explore API endpoints
3. ✅ Customize configs
4. ✅ Enable LoRA+ and advanced features
5. ✅ Experiment with hyperparameters
6. ✅ Benchmark different settings

## 📚 Documentation

- 🌐 **WebUI Guide**: `docs/WEBUI_GUIDE.md`
- 🏷️ **WD14 Quickstart**: `WD14_QUICKSTART.md`
- 🔒 **NSFW Guide**: `docs/NSFW_TRAINING_GUIDE.md`
- 🤖 **Gemini Integration**: `docs/GEMINI_INTEGRATION.md`
- 📖 **Complete Guide**: `docs/GUIDE.md`
- ⚙️ **Features v2.3**: `FEATURES_v2.3.md`

## 🎉 You're All Set!

**Everything is ready:**
- ✅ WebUI installed and configured
- ✅ WD14 Tagger ready (NSFW-safe)
- ✅ All dependencies installed
- ✅ Launchers created
- ✅ Documentation complete

**Just run:**
```bash
.\start_webui.bat
```

**And start training! 🚀**

---

**Version**: 2.3.1 (WebUI)  
**Date**: December 1, 2025  
**Status**: ✅ Production Ready
