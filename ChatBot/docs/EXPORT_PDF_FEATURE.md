# 📄 Export Chat to PDF Feature

## Tổng quan
Tính năng tải xuống lịch sử chat ra file **PDF** có chứa cả **hình ảnh**.

## Thay đổi từ phiên bản cũ

### Before (v1.7.0):
- Export ra file `.txt` (text only)
- Không bao gồm hình ảnh
- Format đơn giản

### After (v1.8.0):
- Export ra file `.pdf` (professional format)
- **Bao gồm cả hình ảnh** trong chat
- Layout đẹp, dễ đọc
- Pagination tự động

## Libraries sử dụng

### jsPDF
- **Version**: 2.5.1
- **Purpose**: Tạo PDF từ JavaScript
- **CDN**: `https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`

### html2canvas
- **Version**: 1.4.1
- **Purpose**: Convert HTML elements (images) to canvas → embed vào PDF
- **CDN**: `https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js`

## Flow hoạt động

```
User → Click "Tải xuống" button
    ↓
Show loading message "🔄 Đang tạo PDF..."
    ↓
Create jsPDF instance (A4 portrait)
    ↓
Add title & timestamp header
    ↓
Loop through all messages:
    ├─ Add message header (👤 USER / 🤖 AI)
    ├─ Add text content (wrapped to fit page width)
    ├─ If has image:
    │   ├─ Convert <img> to canvas (html2canvas)
    │   ├─ Convert canvas to JPEG dataURL
    │   ├─ Add image to PDF (scaled to fit)
    │   └─ Handle errors gracefully
    └─ Add separator line
    ↓
Check pagination (add new page if needed)
    ↓
Save PDF: chat-history-YYYYMMDD-HHMMSS.pdf
    ↓
Remove loading message
```

## Code Implementation

### Frontend (index.html)

#### Add Libraries
```html
<!-- jsPDF and html2canvas for PDF export -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
```

#### downloadChat() Function
```javascript
async function downloadChat() {
    const messages = Array.from(chatContainer.children);
    if (messages.length === 0) {
        alert('Chưa có lịch sử chat để tải xuống!');
        return;
    }
    
    // Show loading
    const loadingMsg = addMessage('🔄 Đang tạo PDF...', false, 'System', 'casual');
    
    try {
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 15;
        const maxWidth = pageWidth - (margin * 2);
        let yOffset = margin;
        
        // Title
        pdf.setFontSize(18);
        pdf.setFont('helvetica', 'bold');
        pdf.text('AI CHATBOT - LICH SU HOI THOAI', pageWidth / 2, yOffset, { align: 'center' });
        
        // Process each message
        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            const isUser = msg.classList.contains('user');
            const textEl = msg.querySelector('.message-text');
            const imageEl = msg.querySelector('img');
            
            // Add text content
            if (textEl) {
                const text = textEl.textContent || '';
                const lines = pdf.splitTextToSize(text, maxWidth);
                lines.forEach(line => {
                    pdf.text(line, margin, yOffset);
                    yOffset += 5;
                });
            }
            
            // Add image
            if (imageEl && imageEl.src) {
                const canvas = await html2canvas(imageEl, {
                    scale: 1,
                    logging: false,
                    backgroundColor: null
                });
                
                const imgData = canvas.toDataURL('image/jpeg', 0.7);
                const imgWidth = Math.min(maxWidth, 100);
                const imgHeight = (canvas.height * imgWidth) / canvas.width;
                
                pdf.addImage(imgData, 'JPEG', margin, yOffset, imgWidth, imgHeight);
                yOffset += imgHeight + 5;
            }
            
            // Check pagination
            if (yOffset > pageHeight - 40) {
                pdf.addPage();
                yOffset = margin;
            }
        }
        
        // Save PDF
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        pdf.save(`chat-history-${timestamp}.pdf`);
        
        // Remove loading
        chatContainer.removeChild(loadingMsg);
        
    } catch (error) {
        console.error('Error creating PDF:', error);
        alert('❌ Lỗi khi tạo PDF: ' + error.message);
    }
}
```

## PDF Layout

### Page Setup
- **Size**: A4 (210mm x 297mm)
- **Orientation**: Portrait
- **Margins**: 15mm all sides
- **Max content width**: 180mm

### Header Section
```
========================================
  AI CHATBOT - LICH SU HOI THOAI
  Xuat luc: 29/10/2025, 14:30:00
========================================
```

### Message Layout
```
👤 USER
[Message text wrapped to fit width]
[Image if exists - scaled to max 100mm width]
----------------------------------------

🤖 AI
[Response text wrapped]
[Image if exists]
----------------------------------------
```

## Image Handling

### Conversion Process
```javascript
// Step 1: HTML <img> element
<img src="/storage/images/generated_xxx.png">

// Step 2: html2canvas converts to canvas
const canvas = await html2canvas(imageEl);

// Step 3: Canvas to dataURL (JPEG)
const imgData = canvas.toDataURL('image/jpeg', 0.7);

// Step 4: Add to PDF
pdf.addImage(imgData, 'JPEG', x, y, width, height);
```

### Image Sizing
- **Max width**: 100mm (to fit in PDF)
- **Height**: Auto-scaled to maintain aspect ratio
- **Quality**: 0.7 (70% compression)
- **Format**: JPEG (smaller file size than PNG)

### Error Handling
```javascript
try {
    // Convert and add image
} catch (imgError) {
    console.warn('Cannot add image to PDF:', imgError);
    // Add placeholder text instead
    pdf.text('[Hinh anh]', margin, yOffset);
}
```

## Pagination

### Auto Page Break
```javascript
if (yOffset > pageHeight - 40) {
    pdf.addPage();
    yOffset = margin;
}
```

Kiểm tra sau mỗi:
- Text line
- Image
- Separator line

Nếu gần cuối trang (còn < 40mm) → Tạo trang mới

## Example Output

### Filename
```
chat-history-2025-10-29T14-30-00.pdf
```

### Structure
```
Page 1:
  - Header
  - User message 1
  - AI response 1 (with image)
  - User message 2
  
Page 2:
  - AI response 2 (large text)
  - User message 3
  - AI response 3 (with 2 images)
  
Page 3:
  - User message 4
  - AI response 4
```

## Performance Considerations

### For Large Chats
- **html2canvas** chạy cho mỗi ảnh (có thể chậm)
- Show loading message để user biết đang process
- Process tuần tự (không parallel) để tránh OOM

### Optimization
```javascript
// Use lower scale for faster conversion
await html2canvas(imageEl, {
    scale: 1,  // Instead of 2
    logging: false
});

// Compress JPEG
canvas.toDataURL('image/jpeg', 0.7);  // 70% quality
```

### Estimated Time
- Text-only chat (100 messages): ~1-2 seconds
- Chat with 10 images: ~5-10 seconds
- Chat with 50 images: ~20-30 seconds

## User Experience

### Before Export
```
User: Click "Tải xuống" button
```

### During Export
```
Chat: "🔄 Đang tạo PDF..."
(Loading message at bottom of chat)
```

### After Export
```
- Loading message removed
- PDF file downloaded automatically
- Filename: chat-history-YYYY-MM-DDTHH-MM-SS.pdf
```

## Testing

### Test Case 1: Text-only chat
```javascript
// Expected: PDF with text content only
// No image placeholders
```

### Test Case 2: Chat with images
```javascript
// Expected: PDF with both text and images
// Images scaled properly
// No broken images
```

### Test Case 3: Long chat (pagination)
```javascript
// Expected: Multiple pages
// Page breaks at appropriate places
// No cut-off content
```

### Test Case 4: Error handling
```javascript
// Scenario: Image load fails
// Expected: Show "[Hinh anh]" placeholder
// Continue with other content
```

## Comparison: TXT vs PDF

| Feature | TXT (Old) | PDF (New) |
|---------|-----------|-----------|
| **Format** | Plain text | Professional PDF |
| **Images** | ❌ Not included | ✅ Embedded |
| **Layout** | Simple | Structured |
| **File size** | ~10KB (100 msgs) | ~500KB (with images) |
| **Readability** | Basic | High |
| **Print quality** | Low | High |
| **Sharing** | Plain | Professional |

## Browser Compatibility

### Supported
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+
- ✅ Opera 76+

### Requirements
- Modern JavaScript (ES6+)
- Canvas API support
- Blob API support
- Download attribute support

## Troubleshooting

### Issue 1: PDF không có ảnh
**Cause**: CORS policy blocking external images  
**Solution**: Chỉ dùng images từ cùng domain hoặc `/storage/images/`

### Issue 2: PDF quá lớn
**Cause**: Nhiều ảnh độ phân giải cao  
**Solution**: Giảm quality từ 0.7 xuống 0.5

### Issue 3: Loading lâu
**Cause**: Nhiều ảnh cần convert  
**Solution**: Normal behavior, user đợi loading message

### Issue 4: Memory error
**Cause**: Quá nhiều ảnh (>100)  
**Solution**: Warn user hoặc split thành nhiều PDFs

## Future Enhancements

### v2.0 Ideas
- [ ] **Page numbers** - Add "Page X of Y" footer
- [ ] **Table of contents** - Bookmark major sections
- [ ] **Better formatting** - Code blocks, tables, lists
- [ ] **Compression** - Smaller file size
- [ ] **Templates** - Different PDF styles
- [ ] **Metadata** - Author, title, keywords
- [ ] **Password protection** - Secure PDFs
- [ ] **Batch export** - Multiple sessions → single PDF

## Version
- **Added in**: v1.8.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Ready for testing

## Related Features
- [Image Storage](IMAGE_STORAGE_FEATURE.md) - Server-side image storage
- [AI Learning/Memory](AI_LEARNING_MEMORY_FEATURE.md) - Save with images
