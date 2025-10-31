# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Vietnamese Speech-to-Text System
Main Entry Point

Available Models:
1. Smart Dual (Recommended) - Rule-based fusion, fastest & most accurate
2. Fast Dual - Ultra fast processing for quick tasks  
3. Whisper + Gemini - Baseline with cloud AI
4. PhoWhisper - Vietnamese specialized model

Usage:
    python s2t.py [--model smart|fast|whisper|pho] [--audio path/to/audio.mp3]
    
Examples:
    python s2t.py                                    # Interactive mode
    python s2t.py --model smart                      # Smart dual model
    python s2t.py --model fast --audio audio.mp3     # Fast processing
"""

import argparse
import os
import sys
from pathlib import Path

# Add core module to path
current_dir = Path(__file__).parent
core_dir = current_dir / "core"
sys.path.insert(0, str(core_dir))

def main():
    parser = argparse.ArgumentParser(
        description="Vietnamese Speech-to-Text System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--model", 
        choices=["smart", "fast", "whisper", "pho"],
        default="smart",
        help="Model to use (default: smart)"
    )
    
    parser.add_argument(
        "--audio",
        help="Path to audio file (if not provided, uses .env AUDIO_PATH)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode to choose model"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("[MIC]  VIETNAMESE SPEECH-TO-TEXT SYSTEM")
    print("=" * 80)
    
    # Interactive mode
    if args.interactive:
        print("\n[?] Available Models:")
        print("1. [BEST] Smart Dual (Recommended) - Rule-based fusion")
        print("2. [FAST] Fast Dual - Ultra fast processing")  
        print("3. [STAR] Whisper + Gemini - Baseline with cloud AI")
        print("4. [?][?] PhoWhisper - Vietnamese specialized")
        
        while True:
            try:
                choice = input("\nSelect model [1-4]: ").strip()
                if choice == "1":
                    args.model = "smart"
                    break
                elif choice == "2":
                    args.model = "fast"
                    break
                elif choice == "3":
                    args.model = "whisper"
                    break
                elif choice == "4":
                    args.model = "pho"
                    break
                else:
                    print("Invalid choice. Please select 1-4.")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
    
    # Set audio path
    if args.audio:
        os.environ["AUDIO_PATH"] = str(Path(args.audio).resolve())
        print(f"[FOLDER] Audio file: {args.audio}")
    
    print(f"[AI] Using model: {args.model}")
    print("=" * 80)
    
    # Import and run the selected model
    try:
        if args.model == "smart":
            print("[BEST] Starting Smart Dual Model...")
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
            import run_dual_smart
            run_dual_smart.main()
            
        elif args.model == "fast":
            print("[FAST] Starting Fast Dual Model...")
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
            import run_dual_fast
            run_dual_fast.main()
            
        elif args.model == "whisper":
            print("[STAR] Starting Whisper + Gemini...")
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            import run_whisper_with_gemini
            run_whisper_with_gemini.main()
            
        elif args.model == "pho":
            print("[TARGET] Starting PhoWhisper...")
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            import Phowhisper
            Phowhisper.main()
            
    except ImportError as e:
        print(f"[ERROR] Error importing model: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"[ERROR] Error running model: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()