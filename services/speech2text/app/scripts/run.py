# -*- coding: utf-8 -*-
"""
Speech-to-Text System - Main Launcher
Whisper large-v3 + PhoWhisper-large + Qwen2.5-1.5B Fusion
"""
import sys
import os
import subprocess

def main():
    print("=" * 80)
    print("SPEECH-TO-TEXT SYSTEM - QWEN2.5-1.5B FUSION")
    print("=" * 80)
    print()
    
    # Paths
    app_dir = os.path.join(os.path.dirname(__file__), 'app')
    venv_python = os.path.join(app_dir, 's2t', 'Scripts', 'python.exe')
    main_script = os.path.join(app_dir, 'core', 'run_dual_vistral.py')
    
    # Run with venv python
    subprocess.run([venv_python, main_script])

if __name__ == "__main__":
    main()
