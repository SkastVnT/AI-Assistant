# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Script d[?] t[?]i tr[?][?]c model PhoWhisper-large v[?] local
Gi[?]p tr[?]nh l[?]i khi ch[?]y script ch[?]nh
"""

import os
os.environ['HF_HUB_DISABLE_SAFETENSORS_LOAD_WARNING'] = '1'

from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch

print("=" * 80)
print("[?] DOWNLOADING PHOWHISPER-LARGE MODEL")
print("=" * 80)

print("\n[?] Step 1: Downloading Processor...")
try:
    processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
    print("[OK] Processor downloaded successfully!")
except Exception as e:
    print(f"[?] Processor download failed: {e}")
    exit(1)

print("\n[?] Step 2: Downloading Model...")
try:
    # Th[?] t[?]i v[?]i safetensors tr[?][?]c
    try:
        model = WhisperForConditionalGeneration.from_pretrained(
            "vinai/PhoWhisper-large",
            trust_remote_code=True,
            use_safetensors=True
        )
        print("[OK] Model downloaded with safetensors format!")
    except:
        # Fallback sang PyTorch format
        model = WhisperForConditionalGeneration.from_pretrained(
            "vinai/PhoWhisper-large",
            trust_remote_code=True,
            use_safetensors=False
        )
        print("[OK] Model downloaded with PyTorch format!")
    
    print(f"\n[CHART] Model Info:")
    print(f"   - Parameters: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")
    print(f"   - Device: {next(model.parameters()).device}")
    
except Exception as e:
    print(f"[?] Model download failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 80)
print("[OK] PHOWHISPER-LARGE DOWNLOADED SUCCESSFULLY!")
print("=" * 80)
print("\n[IDEA] B[?]y gi[?] b[?]n c[?] th[?] ch[?]y script ch[?]nh:")
print("   python run_dual_models.py")
print("\nModel d[?] d[?][?]c cache t[?]i:")
print("   C:\\Users\\%USERNAME%\\.cache\\huggingface\\hub\\")
