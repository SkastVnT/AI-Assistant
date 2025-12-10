# VistralS2T Branch - Qwen2.5-7B Enhancement

## 🚀 Tổng Quan

Nhánh này sử dụng **Qwen2.5-7B-Instruct** để enhance transcript từ Whisper.

## ⚡ Ưu Điểm

### 1. **SIÊU NHANH với 4-bit Quantization**
- Enhancement: ~15-25s  
- **Tổng: ~40-50s** (vs 700s Gemini!)

### 2. **Hỗ Trợ Tiếng Việt Xuất Sắc**
- Training data chất lượng cao
- Hiểu ngữ cảnh Việt Nam

### 3. **Không Cần API Key**
- Open-source, free
- Chạy local, bảo mật

### 4. **Tối Ưu VRAM**
- 4-bit: Chỉ ~4-5GB VRAM
- Chạy được RTX 3060, 4060

## 📊 So Sánh Performance

| Method | Time | Quality | Cost |
|--------|------|---------|------|
| **Qwen2.5** | **40s** | ⭐⭐⭐⭐⭐ | Free |
| Gemini | 700s | ⭐⭐⭐⭐ | Paid |
| Rules | 1s | ⭐⭐⭐ | Free |

## 🎯 Sử Dụng

```bash
.\run_vistral.bat
```
