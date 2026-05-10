# 🎨 Hướng dẫn sử dụng Tool "Tạo ảnh"

## Tính năng mới: Text-to-Image trong ChatBot

### Cách sử dụng:

1. **Bật tool "Tạo ảnh"**
   - Nhấn nút `🎨 Tạo ảnh` ở thanh tools (bên dưới input)
   - Nút sẽ chuyển sang màu xanh khi đã bật

2. **Nhập mô tả ảnh bạn muốn**
   - Ví dụ: "Một cô gái anime đẹp với mái tóc dài, đứng dưới cây anh đào"
   - Hoặc: "A cyberpunk city at night with neon lights"
   - Bạn có thể viết bằng tiếng Việt hoặc tiếng Anh

3. **Bật Deep Thinking (tùy chọn)**
   - Nếu bật, AI sẽ suy nghĩ kỹ hơn để tạo prompt tốt hơn
   - Kết quả sẽ chi tiết và sáng tạo hơn

4. **Nhấn "Gửi"**
   - ChatBot sẽ tự động:
     - Phân tích mô tả của bạn
     - Tạo prompt chuyên nghiệp cho Stable Diffusion
     - Đổi sang model AnythingV4_v45
     - Tạo ảnh với cấu hình tối ưu
     - Hiển thị ảnh trong đoạn chat

## Cấu hình tự động:

| Tham số | Giá trị |
|---------|---------|
| **Model** | AnythingV4_v45.safetensors |
| **Negative Prompt** | Random + r18 + nsfw filters |
| **Kích thước** | 1024 x 1280 (tỷ lệ dọc) |
| **Steps** | 10 (nhanh) |
| **CFG Scale** | 8 (cân bằng) |
| **Sampler** | DPM++ 2M Karras |
| **Restore Faces** | Tắt |
| **Hires Fix** | Tắt |

## Ví dụ:

### Input:
```
Một chiến binh anime với áo giáp sáng bóng, cầm kiếm, đứng trên đỉnh núi lúc hoàng hôn
```

### Prompt được tạo (ví dụ):
```
anime warrior, shining armor, holding sword, mountain peak, sunset, dramatic lighting, 
golden hour, epic scene, detailed armor, fantasy art, cinematic composition, 
highly detailed, masterpiece, best quality
```

### Kết quả:
- Ảnh anime chất lượng cao 1024x1280
- Không có nội dung nhạy cảm (r18/nsfw)
- Hiển thị ngay trong chat với thông tin chi tiết

## Lưu ý:

- ✅ Tool tự động tắt sau khi tạo ảnh thành công
- ✅ Ảnh được tạo với seed ngẫu nhiên mỗi lần
- ✅ Negative prompt tự động thêm filter r18/nsfw
- ⏱️ Thời gian tạo: 10-30 giây (tùy GPU)
- 🚫 Không lưu ảnh vào disk (chỉ hiển thị trong chat)

## Yêu cầu:

- Stable Diffusion WebUI phải đang chạy
- API phải được enable (`--api` flag)
- Model AnythingV4_v45.safetensors phải có trong thư mục models

## Troubleshooting:

**Q: Lỗi "Stable Diffusion WebUI chưa chạy"?**
- A: Chạy `.\scripts\startup\start_chatbot_with_sd.bat`

**Q: Lỗi "Model not found"?**
- A: Tải AnythingV4_v45.safetensors về thư mục `stable-diffusion-webui/models/Stable-diffusion/`

**Q: Ảnh bị lỗi hoặc không đúng mô tả?**
- A: Thử bật Deep Thinking để AI tạo prompt tốt hơn

**Q: Muốn tạo nhiều ảnh liên tiếp?**
- A: Tool sẽ tự tắt sau mỗi lần tạo, bật lại và gửi request mới

## Kết hợp với các tool khác:

- ❌ Không nên dùng cùng lúc với Google Search hoặc GitHub
- ✅ Có thể dùng với các context khác nhau (casual, programming, etc.)
- ✅ Deep Thinking giúp tạo prompt sáng tạo hơn

---

**Created:** 2025-10-29  
**Version:** 1.0  
**Author:** AI Assistant Team
