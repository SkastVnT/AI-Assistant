# NSFW/R18+ Content Training Guide

## ⚠️ IMPORTANT: Gemini Limitations for NSFW Content

**DO NOT use Gemini 2.0 Flash for NSFW/R18+ content!**

### Why?

1. **Safety Filters**
   - Gemini has strict content policies
   - Automatically BLOCKS sexually explicit content
   - Returns errors instead of captions
   - May result in API key ban

2. **Terms of Service Violation**
   - Google prohibits NSFW content in Gemini API
   - Account suspension risk
   - Permanent access loss

3. **Privacy Concerns**
   - Images uploaded to Google servers
   - May be stored/analyzed
   - NOT safe for sensitive content

## ✅ Recommended Solutions for NSFW Training

### Option 1: WD14 Tagger (Best for Anime NSFW)

**Why WD14?**
- ✅ Runs 100% LOCAL (offline)
- ✅ Complete privacy (images never leave your PC)
- ✅ Supports NSFW tags (rating:explicit, nsfw, nude, etc.)
- ✅ Specialized for anime/manga artwork
- ✅ FREE and open-source

**Installation:**

```bash
pip install huggingface-hub
```

**Usage:**

```python
# Create WD14 tagger script
python scripts/utilities/wd14_tagger.py --input data/train --threshold 0.35
```

**Example output:**
```
1girl, solo, nude, nsfw, rating:explicit, breasts, nipples, pussy, 
uncensored, high quality, detailed anatomy, realistic proportions
```

### Option 2: Manual Tagging with Templates

**Best for:**
- Maximum control
- Consistent quality
- Specific character training

**Template Example:**

```
# Base quality tags
masterpiece, best quality, high resolution, detailed

# Character tags
1girl, [character_name], [hair_color] hair, [eye_color] eyes

# NSFW tags (adjust per image)
nude, nsfw, rating:explicit, [body_part], [pose], [expression]

# Style tags
anime style, detailed anatomy, soft lighting
```

**Workflow:**

1. Create category templates
2. Copy template for each image
3. Customize specific details
4. 100% privacy maintained

### Option 3: BLIP (Local, but Limited)

**Usage:**

```bash
python -m utils.preprocessing --data_dir data/train --action caption
```

**Pros:**
- ✅ Runs locally
- ✅ No content restrictions

**Cons:**
- ❌ Poor NSFW recognition
- ❌ Generic/vague captions
- ❌ Not trained on explicit content

**Only use if:** You need basic scene descriptions + manual NSFW tag additions

### Option 4: CogVLM (Advanced Users)

**Best open-source vision model for NSFW:**

```bash
pip install torch transformers pillow
```

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image

# Load model (first time downloads ~20GB)
model = AutoModelForCausalLM.from_pretrained(
    "THUDM/cogvlm-chat-hf",
    torch_dtype=torch.float16,
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained("THUDM/cogvlm-chat-hf")

# Generate caption
image = Image.open("image.jpg")
inputs = tokenizer("Describe this image in detail.", return_tensors="pt")
outputs = model.generate(**inputs, images=image, max_length=512)
caption = tokenizer.decode(outputs[0])
```

**Requirements:**
- GPU with 12GB+ VRAM
- 50GB disk space

**Pros:**
- ✅ High-quality captions
- ✅ No safety filters
- ✅ Local/private

**Cons:**
- ❌ High hardware requirements
- ❌ Complex setup

## 🎯 Recommended Workflow for NSFW LoRA

### Complete Pipeline (Privacy-First)

```bash
# Step 1: Organize dataset
data/
├── train/
│   ├── img001.jpg
│   ├── img002.png
│   └── ...

# Step 2: Generate tags with WD14 (local)
python scripts/utilities/wd14_tagger.py \
    --input data/train \
    --threshold 0.35 \
    --add_rating_tags

# Output: img001.txt, img002.txt with tags

# Step 3: Review and enhance tags manually
# Add specific character details
# Adjust quality tags
# Add context tags

# Step 4: Configure training
# Use configs/advanced_config.yaml or loraplus_config.yaml
cp configs/loraplus_config.yaml configs/nsfw_config.yaml

# Step 5: Train
python scripts/training/train_lora.py --config configs/nsfw_config.yaml
```

## 🔧 WD14 Tagger Script

Create `scripts/utilities/wd14_tagger.py`:

```python
"""
WD14 Tagger for NSFW-safe local tagging
"""

import os
import argparse
from pathlib import Path
from PIL import Image
import numpy as np
from huggingface_hub import hf_hub_download
import onnxruntime as rt

# WD14 models
MODELS = {
    'swinv2': 'SmilingWolf/wd-swinv2-tagger-v3',
    'convnext': 'SmilingWolf/wd-convnext-tagger-v3',
    'vit': 'SmilingWolf/wd-vit-tagger-v3'
}

def load_model(model_name='swinv2'):
    """Load WD14 model"""
    model_repo = MODELS[model_name]
    
    # Download model files
    model_path = hf_hub_download(model_repo, "model.onnx")
    tags_path = hf_hub_download(model_repo, "selected_tags.csv")
    
    # Load ONNX model
    model = rt.InferenceSession(model_path)
    
    # Load tags
    import csv
    with open(tags_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        tags = [row for row in reader]
    
    return model, tags

def predict_tags(model, tags, image_path, threshold=0.35):
    """Predict tags for image"""
    # Load and preprocess image
    img = Image.open(image_path).convert('RGB')
    img = img.resize((448, 448))
    img_array = np.array(img).astype(np.float32) / 255.0
    img_array = np.expand_dims(img_array, 0)
    
    # Run inference
    input_name = model.get_inputs()[0].name
    output = model.run(None, {input_name: img_array})[0][0]
    
    # Filter by threshold
    result_tags = []
    for i, score in enumerate(output):
        if score >= threshold:
            tag_name = tags[i]['name'].replace('_', ' ')
            result_tags.append((tag_name, score))
    
    # Sort by score
    result_tags.sort(key=lambda x: x[1], reverse=True)
    
    return result_tags

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--threshold', type=float, default=0.35)
    parser.add_argument('--model', choices=['swinv2', 'convnext', 'vit'], default='swinv2')
    parser.add_argument('--add_rating_tags', action='store_true')
    args = parser.parse_args()
    
    print("Loading WD14 model...")
    model, tags = load_model(args.model)
    
    input_dir = Path(args.input)
    image_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    
    for img_path in input_dir.iterdir():
        if img_path.suffix.lower() not in image_exts:
            continue
        
        print(f"Processing {img_path.name}...")
        
        # Predict tags
        pred_tags = predict_tags(model, tags, str(img_path), args.threshold)
        
        # Format tags
        tag_string = ', '.join([tag for tag, score in pred_tags])
        
        # Save to .txt file
        txt_path = img_path.with_suffix('.txt')
        txt_path.write_text(tag_string, encoding='utf-8')
        
        print(f"  ✓ Saved {len(pred_tags)} tags")

if __name__ == '__main__':
    main()
```

**Install dependencies:**

```bash
pip install onnxruntime huggingface-hub
```

## 📊 Comparison: NSFW Tagging Methods

| Method | Privacy | Quality | NSFW Support | Speed | Cost |
|--------|---------|---------|--------------|-------|------|
| **WD14 Tagger** | ✅ 100% | ⭐⭐⭐⭐⭐ | ✅ Excellent | ⚡⚡⚡⚡ | FREE |
| **Gemini** | ❌ No | ⭐⭐⭐⭐⭐ | ❌ BLOCKED | ⚡⚡⚡ | ❌ BANNED |
| **BLIP** | ✅ 100% | ⭐⭐ | ⚠️ Poor | ⚡⚡⚡⚡⚡ | FREE |
| **CogVLM** | ✅ 100% | ⭐⭐⭐⭐ | ✅ Good | ⚡⚡ | FREE |
| **Manual** | ✅ 100% | ⭐⭐⭐⭐⭐ | ✅ Perfect | ⚡ | FREE |

## ⚖️ Legal & Ethical Considerations

### Legal
- ✅ Training on NSFW content is LEGAL (for personal use)
- ✅ Using local tools is LEGAL
- ⚠️ Distribution may have restrictions (check local laws)

### Ethical Best Practices
- 🔒 Keep content private and secure
- 🚫 Don't upload to public services
- ✅ Use local/offline tools only
- 📝 Respect copyright and consent

## 🎓 Training Tips for NSFW LoRA

### Dataset Quality
- Use high-resolution images (512x512 minimum)
- Ensure consistent art style
- Remove low-quality/corrupted images
- 50-200 images recommended

### Tagging Best Practices
- Always include quality tags: `masterpiece, best quality, high resolution`
- Add rating tags: `rating:explicit, nsfw`
- Be specific: `nude` vs `partially nude`
- Include anatomical details for accuracy
- Add style tags: `anime style, detailed anatomy`

### Training Configuration

**Recommended config for NSFW:**

```yaml
# configs/nsfw_config.yaml
model:
  pretrained_model_name_or_path: "runwayml/stable-diffusion-v1-5"

lora:
  rank: 64  # Higher rank for anatomical details
  alpha: 128

training:
  num_train_epochs: 15
  train_batch_size: 2
  learning_rate: 5e-5  # Lower LR for NSFW
  
  # Use LoRA+ for faster training
  use_loraplus: true
  loraplus_lr_ratio: 16.0
  
  # Robust loss for varied anatomy
  loss_type: smooth_l1
  
  # Min-SNR for quality
  min_snr_gamma: 5.0
  
  # Noise offset for variety
  noise_offset: 0.1
```

### Common Mistakes to Avoid

❌ **Don't:**
- Upload NSFW content to online services
- Use Gemini/GPT-4/Claude for NSFW
- Share API keys that violated ToS
- Undertag images (missing details)
- Overtrain (causes overfitting)

✅ **Do:**
- Use local tools (WD14, BLIP)
- Manual review all tags
- Test with lower epochs first
- Keep backups of dataset
- Monitor training progress

## 📞 Support

For NSFW training questions:
- Check `docs/GUIDE.md` for general training
- See `FEATURES_v2.3.md` for advanced features
- WD14 Tagger: https://github.com/SmilingWolf/onnxruntime-web
- LoRA training: https://github.com/kohya-ss/sd-scripts

---

**Remember: Privacy first! Always use local tools for sensitive content.**
