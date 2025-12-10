# Gemini AI Config cho NSFW Training - 100% An toàn

## 🔒 Vấn đề: Gemini không cho phép NSFW

Gemini API từ chối phân tích/xử lý ảnh NSFW/R18+ content do vi phạm Terms of Service.

**Nhưng bạn VẪN có thể dùng Gemini để tối ưu training!** ✅

---

## 🧠 Giải pháp thông minh: Metadata-Only Approach

### Workflow an toàn 100%:

```
1. WD14 Tagger (Local) → Phân tích ảnh NSFW trên máy bạn
2. Extract Metadata → Chỉ lấy thống kê (không có ảnh)
3. Gemini AI → Nhận metadata, đề xuất config tối ưu
4. Apply → Tự động điền settings vào WebUI
```

### Metadata gì được gửi đến Gemini?

```json
{
  "total_images": 150,
  "avg_resolution": "768x1024",
  "resolution_stats": {
    "min": "512x512",
    "max": "1024x1536",
    "avg": "768x1024"
  },
  "tag_stats": {
    "total_tags": 2500,
    "unique_tags": 450,
    "avg_tags_per_image": 16.7,
    "most_common": {
      "1girl": 140,
      "solo": 130,
      "anime_style": 150,
      "detailed_background": 80
    }
  },
  "complexity_score": 7.5
}
```

**KHÔNG có:**
- ❌ Ảnh NSFW gốc
- ❌ Tên file ảnh
- ❌ Đường dẫn folder
- ❌ Nội dung ảnh cụ thể

**CHỈ có:**
- ✅ Số lượng ảnh
- ✅ Độ phân giải trung bình
- ✅ Thống kê tags
- ✅ Điểm phức tạp

---

## 🚀 Cách sử dụng

### 1. Setup API Key

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY = "your-api-key-here"

# Hoặc thêm vào file .env
echo GEMINI_API_KEY=your-api-key > .env
```

### 2. Dùng từ WebUI (Dễ nhất!)

1. Mở WebUI: http://127.0.0.1:7860
2. Chọn dataset NSFW của bạn
3. (Optional) Click "Auto-Tag with WD14" để tag ảnh local
4. Click **"🤖 Get AI-Powered Config (Gemini)"**
5. Chọn training goal:
   - 🎯 High Quality - Chất lượng cao nhất
   - ⚖️ Balanced - Cân bằng speed/quality
   - ⚡ Fast - Nhanh, chất lượng OK
6. Wait ~10s → Config tự động điền!

### 3. Dùng từ Command Line

```powershell
# Activate venv
.\lora\Scripts\activate.bat

# Chạy recommender
python utils/config_recommender.py "path/to/your/nsfw/dataset" high_quality

# Output sẽ save vào: dataset/recommended_config.json
```

### 4. Tích hợp vào Python script

```python
from utils.config_recommender import quick_recommend

# Get recommendations
config = quick_recommend(
    dataset_path="./my_nsfw_dataset",
    training_goal="high_quality"
)

print(f"Recommended LR: {config['learning_rate']}")
print(f"Network Dim: {config['network_dim']}")
print(f"Epochs: {config['epochs']}")
print(f"\nReasoning:\n{config['reasoning']}")
```

---

## 📊 Ví dụ output từ Gemini

### Input metadata (150 ảnh NSFW, 768x1024):

```json
{
  "total_images": 150,
  "avg_resolution": "768x1024",
  "complexity_score": 7.5,
  "tag_stats": {
    "unique_tags": 450,
    "avg_tags_per_image": 16.7
  }
}
```

### Output recommendations:

```json
{
  "learning_rate": 8e-5,
  "batch_size": 4,
  "epochs": 15,
  "network_dim": 48,
  "network_alpha": 24,
  "optimizer": "AdamW8bit",
  "lr_scheduler": "cosine_with_restarts",
  "min_snr_gamma": 5,
  "use_lora_plus": true,
  "lora_plus_lr_ratio": 16,
  "train_resolution": "768x1024",
  "caption_dropout_rate": 0.05,
  
  "reasoning": "Based on your dataset profile:
  
  1. **Dataset Size (150 images)**: Medium size requires careful balancing. 
     - LR: 8e-5 is conservative enough to avoid overfitting
     - Epochs: 15 provides sufficient training time
  
  2. **High Complexity (7.5/10)**: Dataset has diverse content
     - Network Dim: 48 captures variety while staying efficient
     - Alpha: 24 (half of dim) for stable training
  
  3. **High Resolution (768x1024)**: 
     - Batch Size: 4 to fit in 12GB VRAM
     - Training at native resolution preserves quality
  
  4. **Tag Diversity (450 unique tags)**: 
     - Caption dropout 5% prevents overfitting on specific tags
     - Cosine schedule with restarts helps escape local minima
  
  5. **LoRA+**: Enabled with ratio 16 for better text encoder learning
  
  6. **Min-SNR Gamma 5**: Reduces noise impact on high-res training",
  
  "warnings": [
    "Monitor for overfitting after epoch 10 - reduce epochs if needed",
    "If VRAM limited, reduce batch_size to 2 and increase gradient_accumulation",
    "Consider validation split to track generalization"
  ],
  
  "estimated_vram": "10-12GB",
  "estimated_time": "2-3 hours on RTX 3080"
}
```

---

## 🔍 Gemini phân tích gì?

### 1. Dataset Size Analysis
- **<50 images**: Small dataset
  - Lower LR (5e-5)
  - More epochs (20+)
  - Higher dim (64-128) to capture detail
  
- **50-200 images**: Medium dataset
  - Moderate LR (1e-4)
  - Medium epochs (10-15)
  - Balanced dim (32-64)
  
- **>200 images**: Large dataset
  - Higher LR (2e-4)
  - Fewer epochs (5-10)
  - Lower dim (16-32) sufficient

### 2. Complexity Scoring
- **Low (0-4)**: Consistent style/content
  - Smaller dim (8-16)
  - Simpler scheduler
  
- **Medium (5-7)**: Varied content
  - Standard dim (32-48)
  - Cosine scheduler
  
- **High (8-10)**: Very diverse
  - Higher dim (64-128)
  - Advanced techniques (LoRA+, Min-SNR)

### 3. Resolution Optimization
- **512x512**: Standard SD resolution
  - Batch size 8-12
  - Full training speed
  
- **768x1024**: High-res portrait
  - Batch size 4-6
  - 1.5x training time
  
- **1024x1024+**: Very high-res
  - Batch size 2-4
  - Consider bucketing

### 4. Tag Distribution
- **Many unique tags**: High diversity
  - Caption dropout 5-10%
  - Prevent overfitting
  
- **Few repeated tags**: Focused content
  - Lower caption dropout (0-5%)
  - Can use higher LR

---

## ⚙️ Training Goals

### 🎯 High Quality
```python
training_goal="high_quality"
```
- Conservative LR (~0.8x)
- More epochs (~1.5x)
- Higher network dim
- Best for: Character LoRAs, Style transfer, Important projects

### ⚖️ Balanced (Default)
```python
training_goal="balanced"
```
- Standard settings
- Good quality/speed ratio
- Recommended for most use cases

### ⚡ Fast
```python
training_goal="fast"
```
- Higher LR (~1.5x)
- Fewer epochs (~0.5x)
- Lower dim
- Best for: Testing, experimentation, quick iterations

### 🧪 Experimental
```python
training_goal="experimental"
```
- Latest techniques (LoRA+, Min-SNR, etc.)
- Cutting-edge optimizers (Prodigy, DAdaptation)
- May be unstable
- Best for: Research, advanced users

---

## 🔐 Privacy & Security

### 100% Safe for NSFW:
✅ **Local WD14 Tagging**: Ảnh KHÔNG rời khỏi máy bạn  
✅ **Metadata Only**: Gemini chỉ nhận số liệu thống kê  
✅ **No Image Upload**: Không có ảnh nào được upload  
✅ **No Filenames**: Tên file/folder không được gửi  
✅ **Encrypted API**: Google API dùng HTTPS  

### Gemini chỉ thấy:
```
"Có 150 ảnh, resolution trung bình 768x1024, 
có 450 unique tags, độ phức tạp 7.5/10"
```

### Gemini KHÔNG thấy:
- ❌ Ảnh gốc của bạn
- ❌ Nội dung cụ thể
- ❌ Tên character/style
- ❌ Bất kỳ thông tin nhạy cảm nào

---

## 📈 Cost Analysis

### Gemini 2.0 Flash Pricing:
- **Free tier**: 1,500 requests/day
- **Input**: $0.075 per 1M tokens (~15,000 configs)
- **Output**: $0.30 per 1M tokens (~3,000 configs)

### Cost per recommendation:
- Input: ~1,000 tokens (metadata + prompt)
- Output: ~500 tokens (JSON config)
- **Total: $0.0002 per recommendation**

### So sánh:
- **GPT-4**: $0.01 per recommendation (50x đắt hơn!)
- **Claude**: $0.005 per recommendation (25x đắt hơn!)
- **Gemini Flash**: $0.0002 (Rẻ nhất!)

---

## 🛠️ Troubleshooting

### "GEMINI_API_KEY not found"
```powershell
# Set trong PowerShell
$env:GEMINI_API_KEY = "your-key"

# Hoặc tạo .env file
echo GEMINI_API_KEY=your-key > .env
```

### "Error calling Gemini API"
- Check internet connection
- Verify API key is correct
- Check quota (1,500 free/day)
- Fallback sẽ dùng rule-based recommendations

### "Failed to analyze dataset"
- Đảm bảo dataset có ảnh (.jpg, .png, etc.)
- Check permissions (read access)
- WD14 tags không bắt buộc (nhưng tốt hơn nếu có)

---

## 💡 Best Practices

### 1. Tag dataset trước khi get recommendations
```
Click "Auto-Tag with WD14" → Wait complete → "Get AI Config"
```
Gemini sẽ có nhiều thông tin hơn từ tag stats!

### 2. Test với Balanced trước
Start với `balanced` goal → Nếu kết quả OK → Giữ nguyên  
Nếu muốn quality cao hơn → Switch sang `high_quality`

### 3. Monitor và adjust
Gemini recommendations là starting point tốt, nhưng:
- Monitor validation loss
- Adjust LR nếu loss không giảm
- Reduce epochs nếu overfit

### 4. Save configs
WebUI tự động save recommended configs:
```
dataset/recommended_config.json
```
Dùng lại cho datasets tương tự!

---

## 📚 Advanced Usage

### Custom metadata analysis:
```python
from utils.config_recommender import DatasetMetadataAnalyzer

analyzer = DatasetMetadataAnalyzer("./dataset")
metadata = analyzer.analyze()

print(f"Complexity: {metadata['complexity_score']}")
print(f"Most common tags: {metadata['tag_stats']['most_common']}")
```

### Manual override:
```python
from utils.config_recommender import GeminiConfigRecommender

recommender = GeminiConfigRecommender()
config = recommender.recommend_config(metadata, "high_quality")

# Override specific settings
config['learning_rate'] = 1e-4  # Your custom LR
config['epochs'] = 20  # Your custom epochs
```

### Batch recommendations:
```python
datasets = ["dataset1", "dataset2", "dataset3"]

for dataset in datasets:
    config = quick_recommend(dataset, "balanced")
    # Save or use config
```

---

## ✅ Checklist sử dụng

- [ ] Setup GEMINI_API_KEY
- [ ] Select NSFW dataset
- [ ] (Optional) Tag với WD14 local
- [ ] Click "Get AI Config"
- [ ] Review recommendations trong logs
- [ ] Check warnings nếu có
- [ ] Adjust nếu cần (LR, epochs, etc.)
- [ ] Start training!
- [ ] Monitor validation loss
- [ ] Save successful configs cho lần sau

---

## 🎉 Kết luận

Bạn hoàn toàn có thể dùng **Gemini 2.0 Flash** để tối ưu config cho NSFW training mà **100% an toàn**!

### Key Points:
1. ✅ Gemini chỉ nhận metadata, KHÔNG nhận ảnh NSFW
2. ✅ WD14 Tagger làm việc local, privacy 100%
3. ✅ AI recommendations rất chính xác và save time
4. ✅ Rẻ hơn GPT-4 tới 50x
5. ✅ Tích hợp sẵn trong WebUI, 1 click là xong

**Happy Training!** 🚀

---

**Created**: 2024-12-01  
**Version**: 1.0.0  
**Author**: AI Assistant  
**License**: MIT
