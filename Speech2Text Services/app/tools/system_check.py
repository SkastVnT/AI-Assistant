# -*- coding: utf-8 -*-
"""
System Health Check - Ki[?]m tra s[?]c kh[?]e h[?] th[?]ng
Ki[?]m tra t[?]t c[?] file quan tr[?]ng v[?] c[?]u h[?]nh
"""
import os
import sys
from pathlib import Path

def check_files():
    """Ki[?]m tra t[?]t c[?] file quan tr[?]ng"""
    print("=" * 80)
    print("[SEARCH] KI[?]M TRA FILE QUAN TR[?]NG")
    print("=" * 80)
    
    important_files = {
        "Scripts ch[?]nh": [
            "run_dual_models.py",
            "Phowhisper.py",
            "run_whisper_with_gemini.py",
            "check_health.py"
        ],
        "C[?]u h[?]nh": [
            ".env",
            ".gitignore",
            "README.md",
            "QUICKSTART.md"
        ],
        "Virtual Environment": [
            "s2t/Scripts/activate",
            "s2t/Scripts/python.exe"
        ]
    }
    
    for category, files in important_files.items():
        print(f"\n[FOLDER] {category}:")
        for file in files:
            path = Path(file)
            if path.exists():
                size = path.stat().st_size
                print(f"   [OK] {file:<40} ({size:,} bytes)")
            else:
                print(f"   [ERROR] {file:<40} [MISSING]")

def check_directories():
    """Ki[?]m tra th[?] m[?]c"""
    print("\n" + "=" * 80)
    print("[FOLDER] KI[?]M TRA TH[?] M[?]C")
    print("=" * 80)
    
    directories = [
        "result/dual",
        "result/gemini",
        "result/raw",
        "audio",
        "No use",
        "s2t"
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        if path.exists():
            # [?][?]m file trong th[?] m[?]c
            file_count = len(list(path.glob("*")))
            print(f"   [OK] {dir_path:<30} ({file_count} items)")
        else:
            print(f"   [ERROR] {dir_path:<30} [MISSING]")

def check_env_config():
    """Ki[?]m tra c[?]u h[?]nh .env"""
    print("\n" + "=" * 80)
    print("[?] KI[?]M TRA CONFIGURATION")
    print("=" * 80)
    
    env_path = Path(".env")
    if env_path.exists():
        print("   [OK] File .env t[?]n t[?]i")
        
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ki[?]m tra c[?]c key quan tr[?]ng
        if "GEMINI_API_KEY=" in content:
            if "your_api_key_here" in content or "YOUR_" in content:
                print("   [WARN]  GEMINI_API_KEY ch[?]a d[?][?]c c[?]u h[?]nh d[?]ng")
            else:
                key_length = len(content.split("GEMINI_API_KEY=")[1].split("\n")[0].strip())
                print(f"   [OK] GEMINI_API_KEY: Configured ({key_length} chars)")
        else:
            print("   [ERROR] GEMINI_API_KEY kh[?]ng t[?]n t[?]i trong .env")
            
        if "AUDIO_PATH=" in content:
            audio_path = content.split("AUDIO_PATH=")[1].split("\n")[0].strip()
            if os.path.exists(audio_path):
                print(f"   [OK] AUDIO_PATH: {audio_path}")
            else:
                print(f"   [WARN]  AUDIO_PATH: File kh[?]ng t[?]n t[?]i")
        else:
            print("   [WARN]  AUDIO_PATH ch[?]a c[?]u h[?]nh (s[?] d[?]ng default)")
    else:
        print("   [ERROR] File .env kh[?]ng t[?]n t[?]i!")

def check_python_packages():
    """Ki[?]m tra Python packages"""
    print("\n" + "=" * 80)
    print("[?] KI[?]M TRA PYTHON PACKAGES")
    print("=" * 80)
    
    required_packages = [
        "faster_whisper",
        "transformers",
        "torch",
        "google.generativeai",
        "librosa",
        "soundfile",
        "scipy",
        "numpy",
        "dotenv"
    ]
    
    for package in required_packages:
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package.replace("-", "_"))
            print(f"   [OK] {package}")
        except ImportError:
            print(f"   [ERROR] {package} [MISSING - pip install {package}]")

def check_results():
    """Ki[?]m tra file k[?]t qu[?]"""
    print("\n" + "=" * 80)
    print("[CHART] KI[?]M TRA K[?]T QU[?]")
    print("=" * 80)
    
    result_dirs = {
        "Dual Model (T[?]t nh[?]t)": "result/dual",
        "Gemini Cleaned": "result/gemini",
        "Raw Transcripts": "result/raw"
    }
    
    total_files = 0
    for name, dir_path in result_dirs.items():
        path = Path(dir_path)
        if path.exists():
            files = list(path.glob("*.txt"))
            total_files += len(files)
            print(f"\n   [FOLDER] {name}:")
            if files:
                print(f"      Total: {len(files)} files")
                # Hi[?]n th[?] 3 file m[?]i nh[?]t
                sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
                for i, file in enumerate(sorted_files[:3], 1):
                    size = file.stat().st_size
                    print(f"      {i}. {file.name} ({size:,} bytes)")
            else:
                print("      No files yet")
        else:
            print(f"\n   [ERROR] {name}: Directory not found")
    
    print(f"\n   [GROWTH] TOTAL RESULTS: {total_files} files")

def print_recommendations():
    """Khuy[?]n ngh[?]"""
    print("\n" + "=" * 80)
    print("[IDEA] KHUY[?]N NGH[?]")
    print("=" * 80)
    
    recommendations = []
    
    # Ki[?]m tra .env
    if not Path(".env").exists():
        recommendations.append("[?] T[?]o file .env v[?] c[?]u h[?]nh GEMINI_API_KEY")
    
    # Ki[?]m tra virtual environment
    if not Path("s2t/Scripts/activate").exists():
        recommendations.append("[?] Virtual environment c[?] th[?] ch[?]a d[?][?]c t[?]o d[?]ng")
    
    # Ki[?]m tra k[?]t qu[?]
    if not list(Path("result/dual").glob("*.txt")):
        recommendations.append("[IDEA] Ch[?]a c[?] k[?]t qu[?]. Ch[?]y: python run_dual_models.py")
    
    if recommendations:
        for rec in recommendations:
            print(f"   {rec}")
    else:
        print("   [OK] H[?] th[?]ng dang ho[?]t d[?]ng t[?]t!")
        print("   [LAUNCH] S[?]n s[?]ng x[?] l[?] audio!")

def main():
    """Main function"""
    print("\n")
    print("[?]" * 40)
    print("VIETNAMESE SPEECH-TO-TEXT - HEALTH CHECK")
    print("[?]" * 40)
    print()
    
    check_files()
    check_directories()
    check_env_config()
    check_python_packages()
    check_results()
    print_recommendations()
    
    print("\n" + "=" * 80)
    print("[?] HEALTH CHECK COMPLETED!")
    print("=" * 80)
    print()
    print("[?] [?][?] bi[?]t th[?]m chi ti[?]t, d[?]c:")
    print("   - README.md ([?][?]y d[?])")
    print("   - QUICKSTART.md (Nhanh)")
    print()

if __name__ == "__main__":
    main()
