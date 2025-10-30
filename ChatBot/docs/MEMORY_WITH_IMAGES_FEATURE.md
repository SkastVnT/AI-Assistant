# 🧠 AI Learning/Memory with Images

## Tổng quan
Tính năng lưu chat làm "bài học" cho AI đã được nâng cấp để **lưu cả hình ảnh** vào folder riêng.

## Thay đổi chính (v1.8.0)

### Before:
```
ChatBot/data/memory/
├── uuid1.json
├── uuid2.json
└── uuid3.json
```

### After:
```
ChatBot/data/memory/
├── Hướng dẫn Python_20251029_143000/
│   ├── memory.json
│   └── image_gen/
│       ├── image_1_generated_xxx.png
│       ├── image_1_generated_xxx.json
│       ├── image_2_generated_yyy.png
│       └── image_2_generated_yyy.json
│
└── Cách dùng Docker_20251029_150000/
    ├── memory.json
    └── image_gen/
        └── image_1_generated_zzz.png
```

## Folder Structure

### Memory Folder Name
```
{title}_{timestamp}/
```

**Example**:
```
Hướng dẫn Python cơ bản_20251029_143000/
```

### Components:
1. **Title** (max 30 chars): User-provided title
2. **Timestamp**: `YYYYMMDD_HHMMSS`
3. **Sanitization**: Replace `/` and `\` with `-`

### Contents:
```
memory_folder/
├── memory.json          # Text content + metadata
└── image_gen/           # Images from chat
    ├── image_1_xxx.png
    ├── image_1_xxx.json (optional metadata)
    ├── image_2_yyy.png
    └── image_2_yyy.json
```

## API Changes

### POST /api/memory/save

#### Request
```json
{
  "title": "Hướng dẫn Python",
  "content": "User: Giải thích list comprehension\nAI: List comprehension là...",
  "tags": ["python", "programming"],
  "images": [
    {
      "url": "/storage/images/generated_20251029_101530.png"
    },
    {
      "base64": "data:image/png;base64,iVBORw0KGgo..."
    }
  ]
}
```

#### Response
```json
{
  "success": true,
  "memory": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "folder_name": "Hướng dẫn Python_20251029_143000",
    "title": "Hướng dẫn Python",
    "content": "...",
    "tags": ["python", "programming"],
    "images": ["image_1_generated_20251029_101530.png"],
    "created_at": "2025-10-29T14:30:00.123456",
    "updated_at": "2025-10-29T14:30:00.123456"
  },
  "message": "Saved with 1 images"
}
```

#### Image Handling

**Case 1: Server-stored image** (URL starts with `/storage/images/`)
```javascript
{
  "url": "/storage/images/generated_20251029_101530.png"
}
```
→ Copy từ `./Storage/Image_Gen/` sang `./data/memory/{folder}/image_gen/`

**Case 2: Base64 image**
```javascript
{
  "base64": "data:image/png;base64,..."
}
```
→ Decode và save trực tiếp vào `./data/memory/{folder}/image_gen/`

#### Image Naming
```
image_{index}_{original_filename}
```

**Examples**:
- `image_1_generated_20251029_101530.png`
- `image_2_generated_20251029_102045.png`
- `image_1.png` (for base64 images)

### GET /api/memory/list

**Updated**: Hỗ trợ cả 2 formats:
1. Old format: Direct `.json` files
2. New format: Folders with `memory.json`

#### Response
```json
{
  "memories": [
    {
      "id": "uuid1",
      "folder_name": "Hướng dẫn Python_20251029_143000",
      "title": "Hướng dẫn Python",
      "content": "...",
      "tags": ["python"],
      "images": ["image_1_xxx.png", "image_2_yyy.png"],
      "created_at": "2025-10-29T14:30:00"
    }
  ]
}
```

### DELETE /api/memory/delete/<memory_id>

**Updated**: Xóa cả folder (không chỉ JSON file)

```python
import shutil
shutil.rmtree(memory_folder)  # Delete entire folder
```

## Frontend Implementation

### Save Memory Button

```javascript
saveMemoryBtn.addEventListener('click', async function() {
    const messages = Array.from(chatContainer.children);
    
    let content = '';
    const images = [];
    
    // Collect text and images
    messages.forEach(msg => {
        const textEl = msg.querySelector('.message-text');
        const imageEl = msg.querySelector('img');
        
        if (textEl) {
            content += textEl.textContent + '\n\n';
        }
        
        if (imageEl && imageEl.src) {
            if (imageEl.src.startsWith('/storage/images/')) {
                images.push({ url: imageEl.src });
            } else if (imageEl.src.startsWith('data:image')) {
                images.push({ base64: imageEl.src });
            }
        }
    });
    
    // Show confirmation
    if (images.length > 0) {
        const confirmMsg = `Bài học có ${images.length} ảnh.\nẢnh sẽ được lưu vào:\n./ChatBot/data/memory/${title}_[timestamp]/image_gen/\n\nTiếp tục?`;
        if (!confirm(confirmMsg)) return;
    }
    
    // Save
    const response = await fetch('/api/memory/save', {
        method: 'POST',
        body: JSON.stringify({ title, content, tags, images })
    });
    
    const data = await response.json();
    alert(`✅ Đã lưu bài học thành công (với ${images.length} ảnh)!`);
});
```

## Backend Implementation

### app.py

```python
@app.route('/api/memory/save', methods=['POST'])
def save_memory():
    data = request.json
    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', [])
    images = data.get('images', [])
    
    # Create folder structure
    memory_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder_name = f"{title[:30].replace('/', '-').replace('\\', '-')}_{timestamp}"
    
    memory_folder = MEMORY_DIR / folder_name
    memory_folder.mkdir(parents=True, exist_ok=True)
    
    image_folder = memory_folder / 'image_gen'
    image_folder.mkdir(parents=True, exist_ok=True)
    
    # Save images
    saved_images = []
    for idx, img_data in enumerate(images):
        img_url = img_data.get('url', '')
        img_base64 = img_data.get('base64', '')
        
        if img_url and img_url.startswith('/storage/images/'):
            # Copy from storage
            source_filename = img_url.split('/')[-1]
            source_path = IMAGE_STORAGE_DIR / source_filename
            
            dest_filename = f"image_{idx + 1}_{source_filename}"
            dest_path = image_folder / dest_filename
            
            import shutil
            shutil.copy2(source_path, dest_path)
            saved_images.append(dest_filename)
            
            # Copy metadata
            meta_source = source_path.with_suffix('.json')
            if meta_source.exists():
                meta_dest = dest_path.with_suffix('.json')
                shutil.copy2(meta_source, meta_dest)
                
        elif img_base64:
            # Save base64
            if ',' in img_base64:
                img_base64 = img_base64.split(',')[1]
            
            image_bytes = base64.b64decode(img_base64)
            dest_filename = f"image_{idx + 1}.png"
            dest_path = image_folder / dest_filename
            
            with open(dest_path, 'wb') as f:
                f.write(image_bytes)
            
            saved_images.append(dest_filename)
    
    # Save memory.json
    memory = {
        'id': memory_id,
        'folder_name': folder_name,
        'title': title,
        'content': content,
        'tags': tags,
        'images': saved_images,
        'created_at': datetime.now().isoformat()
    }
    
    memory_file = memory_folder / 'memory.json'
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'success': True,
        'memory': memory,
        'message': f'Saved with {len(saved_images)} images'
    })
```

## Use Case Examples

### Example 1: Programming Tutorial
```
Title: "Python List Comprehension"
Content: 
  User: Explain list comprehension
  AI: List comprehension is a concise way to create lists...
  
  User: Show examples
  AI: Sure! Here's a visualization:
  [Image: Code examples diagram]
  
Images: 1 diagram
Folder: Python List Comprehension_20251029_140000/image_gen/
```

### Example 2: Design Discussion
```
Title: "Website Design Ideas"
Content:
  User: Create a modern landing page
  AI: Here's a design concept...
  [Image 1: Header design]
  [Image 2: Hero section]
  [Image 3: Footer layout]
  
Images: 3 design mockups
Folder: Website Design Ideas_20251029_150000/image_gen/
```

### Example 3: Math Problem
```
Title: "Calculus Problem Solving"
Content:
  User: Solve this integral
  AI: Let's break it down step by step...
  [Image: Step-by-step solution with LaTeX]
  
Images: 1 solution diagram
Folder: Calculus Problem Solving_20251029_160000/image_gen/
```

## Confirmation Dialog

When saving with images:

```
┌────────────────────────────────────────┐
│ Bài học có 3 ảnh.                      │
│ Ảnh sẽ được lưu vào:                   │
│                                        │
│ ./ChatBot/data/memory/                 │
│   Python Tutorial_20251029_140000/     │
│     image_gen/                         │
│                                        │
│ Tiếp tục?                              │
│                                        │
│        [Hủy]        [OK]               │
└────────────────────────────────────────┘
```

## Success Message

```
┌────────────────────────────────────────┐
│ ✅ Đã lưu bài học thành công           │
│    (với 3 ảnh)!                        │
│                                        │
│           [OK]                         │
└────────────────────────────────────────┘
```

## Backward Compatibility

### Old format support
Memories saved in old format (direct `.json` files) vẫn hoạt động bình thường:

```python
# List memories
for memory_file in MEMORY_DIR.glob('*.json'):
    # Load old format
    
for memory_folder in MEMORY_DIR.iterdir():
    # Load new format
```

### Migration path
- Old memories: Keep as-is (no images)
- New memories: Auto-save to new format with images
- No breaking changes

## Benefits

### 1. Complete Knowledge Base
- Text + Images = Full context
- AI có thể "nhớ" cả visual information

### 2. Better Organization
- Mỗi memory có folder riêng
- Images tách biệt khỏi text
- Dễ quản lý và backup

### 3. Metadata Preservation
- Original image metadata được giữ nguyên
- Có thể trace back prompt, settings

### 4. Storage Efficiency
- Copy instead of duplicate
- Metadata shared between storage locations
- Consistent naming

## Testing Checklist

### Test 1: Save text-only memory
```
✅ Creates folder structure
✅ Saves memory.json
✅ No image_gen folder (or empty)
```

### Test 2: Save memory with server images
```
✅ Copies images from /storage/images/
✅ Copies metadata .json files
✅ Renames with image_X_ prefix
✅ memory.images array populated
```

### Test 3: Save memory with base64 images
```
✅ Decodes base64 to bytes
✅ Saves as image_X.png
✅ memory.images array populated
```

### Test 4: Delete memory
```
✅ Removes entire folder
✅ Removes all images
✅ No orphan files
```

### Test 5: List memories
```
✅ Shows both old and new format
✅ Sorted by created_at
✅ Image count displayed
```

## Troubleshooting

### Issue 1: Folder creation fails
**Cause**: Permission denied  
**Solution**: Check write permissions on `./ChatBot/data/memory/`

### Issue 2: Image copy fails
**Cause**: Source file not found  
**Solution**: Verify image exists in `/storage/images/`

### Issue 3: Base64 decode error
**Cause**: Invalid base64 string  
**Solution**: Check image format, remove data URI prefix

### Issue 4: Folder name too long
**Cause**: Title > 30 chars + timestamp  
**Solution**: Title truncated to 30 chars automatically

## Version
- **Updated in**: v1.8.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Ready for testing

## Related Features
- [Export PDF](EXPORT_PDF_FEATURE.md) - Export chat with images
- [Image Storage](IMAGE_STORAGE_FEATURE.md) - Server-side image storage
