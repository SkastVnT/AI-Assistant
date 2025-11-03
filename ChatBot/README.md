# ChatBot Service - AI Assistant

Multi-model intelligent chatbot with local LLM support, image generation capabilities, and memory features.

## 🌟 Features

- **Multi-Model Support**: OpenAI GPT-4, Google Gemini, Local Qwen 1.5-1.8B
- **Image Generation**: Integration with Stable Diffusion WebUI API
  - Text-to-Image (txt2img)
  - Image-to-Image (img2img) with LoRA and VAE support
  - Advanced parameters control
- **Memory System**: Conversation history with image storage
- **Message Editing**: Edit and regenerate responses
- **Export**: PDF export for conversations
- **Modern UI**: Responsive design with Tailwind CSS

## 📋 Requirements

- Python 3.10.6
- NVIDIA GPU with CUDA 11.8 (for local models)
- 8GB+ RAM (16GB recommended for local models)
- Stable Diffusion WebUI running (for image generation)

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv_chatbot

# Activate (Windows)
.\venv_chatbot\Scripts\activate

# Activate (Linux/Mac)
source venv_chatbot/bin/activate
```

### 2. Install Dependencies

```bash
# Install PyTorch with CUDA (for GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your API keys:
# - OPENAI_API_KEY (for GPT-4)
# - GOOGLE_API_KEY (for Gemini)
# - SD_API_URL (Stable Diffusion API, default: http://127.0.0.1:7860)
```

### 4. Run Application

```bash
python app.py
```

Access at: http://localhost:5000

## 🎨 Image Generation Setup

1. Start Stable Diffusion WebUI with API enabled:
   ```bash
   cd ../stable-diffusion-webui
   python webui.py --api
   ```

2. Image generation features:
   - **Text-to-Image**: Generate images from text prompts
   - **Image-to-Image**: Transform existing images
   - **LoRA Models**: Apply style transformations
   - **VAE**: Use custom VAE models
   - **Advanced Settings**: Steps, CFG Scale, Sampling methods

## 📁 Project Structure

```
ChatBot/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── templates/
│   └── index.html        # Main UI
├── static/
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       ├── app.js        # Main JavaScript
│       ├── image-gen.js  # Image generation
│       ├── memory.js     # Memory features
│       └── pdf-export.js # PDF export
├── src/
│   └── utils/
│       ├── local_model_loader.py  # Local model management
│       └── sd_client.py           # Stable Diffusion API client
├── models/
│   └── Qwen1.5-1.8B-Chat/        # Local LLM model
├── Storage/
│   └── Image_Gen/                 # Generated images
└── data/
    └── memory/                    # Conversation memories
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# API Keys
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Stable Diffusion
SD_API_URL=http://127.0.0.1:7860

# Server
FLASK_PORT=5000
FLASK_DEBUG=False
```

### Model Selection

- **GPT-4**: Best quality, requires API key
- **Gemini**: Fast and capable, requires API key
- **Qwen (Local)**: Free, runs locally, requires GPU

## 📖 Usage Guide

### Basic Chat

1. Select a model from the dropdown
2. Type your message
3. Click Send or press Enter

### Image Generation

1. Click "Generate Image" button
2. Enter your prompt
3. Configure parameters (optional):
   - Steps: 20-50 (higher = better quality)
   - CFG Scale: 7-12 (higher = follow prompt more)
   - Select LoRA or VAE models
4. Click "Generate"

### Memory Features

1. Save conversation with "Save Memory"
2. Load previous conversations from sidebar
3. Continue from where you left off

### Export to PDF

1. Click "Export to PDF" button
2. PDF includes messages and images
3. Saved automatically to downloads

## 🐛 Troubleshooting

### Local Model Issues

```bash
# If Qwen model fails to load:
1. Check GPU memory (requires ~4GB VRAM)
2. Verify CUDA installation: nvidia-smi
3. Try CPU mode (slower): Edit app.py, set device='cpu'
```

### Image Generation Issues

```bash
# If SD API connection fails:
1. Verify SD WebUI is running with --api flag
2. Check SD_API_URL in .env
3. Test connection: http://127.0.0.1:7860/docs
```

### Dependencies Issues

```bash
# If torch installation fails:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# If bitsandbytes fails on Windows:
# It's optional, comment out in requirements.txt
```

## 📚 Documentation

- [Image Generation Guide](docs/IMAGE_GENERATION_TOOL_GUIDE.md)
- [LoRA & VAE Guide](docs/LORA_VAE_GUIDE.md)
- [Memory Features](docs/MEMORY_WITH_IMAGES_FEATURE.md)
- [UI Improvements](docs/UI_IMPROVEMENTS.md)

## 🔄 Updates

### Version 1.8.0
- Added img2img support with LoRA and VAE
- Improved UI with Tailwind CSS
- Enhanced memory system with images
- Added PDF export functionality

### Version 1.5.0
- Added local Qwen model support
- Implemented conversation memory
- Added image generation tool

## 📝 License

Part of AI-Assistant project. See root LICENSE file.

## 🤝 Contributing

This is a sub-service of AI-Assistant project. For contributions, please refer to the main project repository.

## 📧 Support

For issues and questions, please create an issue in the main AI-Assistant repository.
