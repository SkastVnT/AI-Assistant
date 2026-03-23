# Speaker Diarization - Quick Reference

## 🚀 Quick Start (3 Steps)

```bash
# 1. Install
pip install pyannote.audio

# 2. Accept license at https://huggingface.co/pyannote/speaker-diarization-3.1

# 3. Run
run_diarization.bat
```

## 📋 Usage Examples

### Basic Usage

```python
from app.core.llm import SpeakerDiarizationClient

diarizer = SpeakerDiarizationClient(min_speakers=2, max_speakers=5)
diarizer.load()
segments = diarizer.diarize("audio.wav")

for seg in segments:
    print(f"{seg.speaker_id}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")
```

### Full Pipeline

```bash
# Set in app/config/.env
AUDIO_PATH=C:\path\to\audio.mp3

# Run
run_diarization.bat

# Output in: app/data/results/sessions/session_TIMESTAMP/
```

## 📊 Output Files

| File | Description |
|------|-------------|
| `timeline_transcript.txt` | ⭐ **Main output** - Transcript with timestamps |
| `speaker_segments.txt` | Diarization segments list |
| `audio_segments/*.wav` | Individual speaker audio chunks |
| `enhanced_transcript.txt` | Qwen-enhanced (optional) |

## ⚙️ Configuration

```python
# Default (recommended)
SpeakerDiarizationClient(
    model_name="pyannote/speaker-diarization-3.1",
    min_speakers=2,
    max_speakers=5
)

# For meetings (many speakers)
SpeakerDiarizationClient(
    min_speakers=3,
    max_speakers=20
)

# Fixed 2 speakers (faster)
SpeakerDiarizationClient(
    min_speakers=2,
    max_speakers=2
)
```

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| `pyannote.audio not installed` | `pip install pyannote.audio` |
| `Failed to load model` | Accept license at HF model page |
| `HF token required` | Set `HF_TOKEN` in `.env` |
| `CUDA out of memory` | Uses ~1.5GB VRAM, runs on CPU if needed |

## 📈 Performance

- **Accuracy:** 95-98% speaker detection
- **Speed:** ~8s diarization for 60s audio (GPU)
- **VRAM:** ~1.5GB (diarization) + 3GB (Whisper) = 4.5GB total

## 🆚 When to Use?

**Use Diarization (v3.1) if:**
- ✅ Need precise speaker timing
- ✅ Multiple speakers with similar roles
- ✅ Have 4GB+ VRAM

**Use Label-based (v3.0) if:**
- ✅ Need role inference (System/Employee/Customer)
- ✅ Speed is priority
- ✅ Limited resources

## 💡 Pro Tips

1. **16kHz optimal** for diarization
2. **Filter segments** <2s for better quality
3. **Cache results** to avoid re-processing
4. **Batch process** multiple files (load model once)

## 📚 Full Documentation

See `SPEAKER_DIARIZATION.md` for complete guide.
