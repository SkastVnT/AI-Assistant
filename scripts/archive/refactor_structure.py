"""
Auto-Refactor Script for AI Assistant Project
Automatically reorganize project structure following Generative AI template
"""

import os
import shutil
from pathlib import Path


def create_standard_structure(base_path, service_name):
    """Create standard directory structure for a service."""
    print(f"\n📁 Creating standard structure for {service_name}...")
    
    directories = [
        "config",
        "src",
        "src/handlers",
        "src/utils",
        "data",
        "data/cache",
        "data/outputs",
        "examples",
        "notebooks",
        "logs"
    ]
    
    for directory in directories:
        dir_path = Path(base_path) / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py for Python packages
        if directory.startswith("src") or directory == "config":
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""{ directory.replace("/", ".") } package"""')
    
    print(f"✅ Standard structure created for {service_name}")


def create_standard_files(base_path, service_name):
    """Create standard configuration files."""
    print(f"\n📄 Creating standard files for {service_name}...")
    
    # .env.example
    env_example = Path(base_path) / ".env.example"
    if not env_example.exists():
        env_example.write_text(f"""# Environment Variables for {service_name}

# API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...

# Flask Configuration  
FLASK_SECRET_KEY=change-this-secret-key
DEBUG=True
PORT=5000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
""")
    
    # .gitignore (if not exists)
    gitignore = Path(base_path) / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Logs
logs/
*.log

# Data
data/cache/
data/outputs/
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
""")
    
    # README (template)
    readme = Path(base_path) / "README_NEW.md"
    readme.write_text(f"""# {service_name}

## Overview
[Add description here]

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run service
python app.py
```

## Project Structure

```
{service_name}/
├── config/              # Configuration files
├── src/                 # Source code
│   ├── handlers/       # Request handlers
│   └── utils/          # Utility functions
├── data/               # Data storage
├── examples/           # Usage examples
├── notebooks/          # Jupyter notebooks
├── logs/               # Log files
├── requirements.txt    # Dependencies
└── app.py             # Main application
```

## Configuration

See `.env.example` for available environment variables.

## Documentation

[Add links to detailed docs]

## Contributing

[Add contribution guidelines]
""", encoding='utf-8')
    
    print(f"✅ Standard files created for {service_name}")


def main():
    """Main refactoring function."""
    print("=" * 70)
    print("🔧 AI Assistant Project - Auto Refactor")
    print("=" * 70)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    services = {
        "ChatBot": project_root / "ChatBot",
        "Speech2Text Services": project_root / "Speech2Text Services",
        "Text2SQL Services": project_root / "Text2SQL Services"
    }
    
    for service_name, service_path in services.items():
        if service_path.exists():
            print(f"\n{'='*70}")
            print(f"Processing: {service_name}")
            print(f"{'='*70}")
            
            create_standard_structure(service_path, service_name)
            create_standard_files(service_path, service_name)
        else:
            print(f"⚠️ Warning: {service_name} not found at {service_path}")
    
    print("\n" + "=" * 70)
    print("✅ Refactoring completed!")
    print("=" * 70)
    print("\n📝 Next steps:")
    print("1. Review the new structure in each service")
    print("2. Move existing code to appropriate directories")
    print("3. Update import statements")
    print("4. Test each service")
    print("5. Update documentation")


if __name__ == "__main__":
    main()
