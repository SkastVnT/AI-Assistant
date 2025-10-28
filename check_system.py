"""
System Check Script - Kiểm tra toàn bộ hệ thống
Kiểm tra dependencies, file .env, và sẵn sàng chạy
"""

import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.ENDC} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {text}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {text}")

def check_python_version():
    """Check Python version"""
    print_header("PYTHON VERSION CHECK")
    version = sys.version.split()[0]
    major, minor = sys.version_info[:2]
    
    if major == 3 and minor >= 10:
        print_success(f"Python {version} - OK")
        return True
    else:
        print_error(f"Python {version} - Cần Python 3.10+")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print_header("DEPENDENCIES CHECK")
    
    required_packages = {
        'flask': 'Flask',
        'openai': 'OpenAI',
        'google': 'Google Generative AI',
        'dotenv': 'python-dotenv',
        'flask_cors': 'flask-cors'
    }
    
    all_installed = True
    for package, name in required_packages.items():
        try:
            __import__(package)
            print_success(f"{name} - Installed")
        except ImportError:
            print_error(f"{name} - NOT Installed")
            all_installed = False
    
    return all_installed

def check_env_files():
    """Check if .env files exist"""
    print_header("ENVIRONMENT FILES CHECK")
    
    root_env = Path('.env')
    chatbot_env = Path('ChatBot/.env')
    
    has_root = root_env.exists()
    has_chatbot = chatbot_env.exists()
    
    if has_root:
        print_success(".env (Root) - Tồn tại")
    else:
        print_warning(".env (Root) - Chưa có (tùy chọn)")
        print_info("  Copy từ .env.example và thêm API keys nếu dùng Hub Gateway")
    
    if has_chatbot:
        print_success("ChatBot/.env - Tồn tại")
    else:
        print_error("ChatBot/.env - CHƯA CÓ (bắt buộc)")
        print_info("  Copy từ ChatBot/.env.example và thêm API keys")
        return False
    
    return has_chatbot

def check_api_keys():
    """Check if API keys are configured"""
    print_header("API KEYS CHECK")
    
    chatbot_env = Path('ChatBot/.env')
    if not chatbot_env.exists():
        print_error("Không tìm thấy file ChatBot/.env")
        return False
    
    # Read .env file
    with open(chatbot_env) as f:
        content = f.read()
    
    keys_to_check = {
        'OPENAI_API_KEY': 'OpenAI',
        'DEEPSEEK_API_KEY': 'DeepSeek',
        'GEMINI_API_KEY_1': 'Gemini',
    }
    
    all_configured = True
    for key, name in keys_to_check.items():
        if key in content:
            value = [line.split('=', 1)[1].strip() for line in content.split('\n') if line.startswith(key)]
            if value and value[0] and 'YOUR_KEY_HERE' not in value[0]:
                print_success(f"{name} API Key - Đã cấu hình")
            else:
                print_warning(f"{name} API Key - Chưa đúng (vẫn là YOUR_KEY_HERE)")
                all_configured = False
        else:
            print_error(f"{name} API Key - Không tìm thấy")
            all_configured = False
    
    return all_configured

def check_folder_structure():
    """Check if all required folders exist"""
    print_header("FOLDER STRUCTURE CHECK")
    
    required_folders = [
        'ChatBot',
        'ChatBot/templates',
        'config',
        'src',
    ]
    
    all_exist = True
    for folder in required_folders:
        path = Path(folder)
        if path.exists():
            print_success(f"{folder}/ - Tồn tại")
        else:
            print_error(f"{folder}/ - KHÔNG TỒN TẠI")
            all_exist = False
    
    return all_exist

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          AI ASSISTANT - SYSTEM CHECK SCRIPT                ║")
    print("║                                                            ║")
    print("║  Kiểm tra toàn bộ hệ thống trước khi khởi động           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.ENDC)
    
    checks = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Environment Files': check_env_files(),
        'API Keys': check_api_keys(),
        'Folder Structure': check_folder_structure(),
    }
    
    print_header("SUMMARY")
    
    all_passed = all(checks.values())
    
    for check_name, result in checks.items():
        if result:
            print_success(f"{check_name}")
        else:
            print_error(f"{check_name}")
    
    print()
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}╔════════════════════════════════════════════════════════════╗")
        print("║                  ✓ HỆ THỐNG SẴN SÀNG                      ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.ENDC)
        print_info("Khởi động ChatBot:")
        print(f"  {Colors.BOLD}cd ChatBot && python app.py{Colors.ENDC}")
        print_info("Mở trình duyệt:")
        print(f"  {Colors.BOLD}http://127.0.0.1:5000{Colors.ENDC}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}╔════════════════════════════════════════════════════════════╗")
        print("║                ✗ CÓ LỖI CẦN SỬA                           ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.ENDC)
        print_warning("Vui lòng kiểm tra các mục bị lỗi ở trên")
        print_info("Xem hướng dẫn chi tiết trong SETUP_NEW_DEVICE.txt")
        return 1

if __name__ == '__main__':
    sys.exit(main())
