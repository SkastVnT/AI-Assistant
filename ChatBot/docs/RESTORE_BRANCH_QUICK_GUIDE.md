# 🚀 Quick Guide: Restore & Branch Conversation

## Tính năng mới: Khôi phục phiên bản cũ (giống ChatGPT)

### 📖 Tóm tắt
Bây giờ bạn có thể **quay lại phiên bản cũ** của tin nhắn và **tiếp tục chat từ đó**, tạo ra nhiều nhánh conversation khác nhau - giống như ChatGPT!

---

## 🎯 Cách sử dụng

### Bước 1: Edit tin nhắn như bình thường
```
1. Bấm "✏️ Edit" ở tin nhắn user
2. Thay đổi nội dung
3. Bấm "💾 Lưu & Tạo lại response"
```

### Bước 2: Xem lịch sử
```
1. Bấm "📜 Xem lịch sử" (xuất hiện sau khi edit)
2. Modal hiển thị tất cả phiên bản
```

### Bước 3: Khôi phục & Branch
```
1. Chọn phiên bản cũ muốn quay lại
2. Bấm "↩️ Khôi phục & Chat từ đây"
3. Xác nhận → Hệ thống restore và tạo response mới
4. Chat tiếp từ phiên bản cũ này!
```

---

## 💡 Ví dụ thực tế

### Tình huống: Hỏi về code Python

```
You: "Viết code Python đọc file CSV"
AI: [Response 1]

You: Edit → "Viết code Python đọc file CSV và plot graph"
AI: [Response 2 - có graph]

You: Hmm, mình muốn xem lại cách đọc CSV đơn giản
     → Bấm "Xem lịch sử"
     → Chọn phiên bản 1: "Viết code Python đọc file CSV"
     → Bấm "Khôi phục & Chat từ đây"
AI: [Quay lại Response 1]

You: "Thêm error handling"
AI: [Response mới từ nhánh cũ]
```

### Kết quả
- Nhánh 1: CSV → CSV + Graph → [tiếp tục chat về graph]
- Nhánh 2: CSV → CSV với error handling → [tiếp tục chat về error handling]

---

## 🎨 Giao diện

### Modal lịch sử:
```
┌──────────────────────────────────────────┐
│ 📜 Lịch sử chỉnh sửa          [Đóng]    │
├──────────────────────────────────────────┤
│ Tổng số phiên bản: 3                    │
│ 💡 Tip: Bấm nút để quay lại phiên bản   │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ ✅ Phiên bản hiện tại (viền xanh) │  │
│ │ "Viết code Python đọc CSV + plot" │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📝 Phiên bản 2 (viền tím)         │  │
│ │ "Viết code Python đọc file CSV"   │  │
│ │ [↩️ Khôi phục & Chat từ đây]      │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ 📝 Phiên bản 1                     │  │
│ │ "Viết code Python"                 │  │
│ │ [↩️ Khôi phục & Chat từ đây]      │  │
│ └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## ⚠️ Lưu ý quan trọng

### ✅ Được lưu:
- ✅ Phiên bản hiện tại được tự động lưu trước khi restore
- ✅ Có thể restore bao nhiêu lần tùy thích
- ✅ Mỗi restore tạo một "timeline" mới

### ❌ Sẽ bị xóa:
- ❌ Tất cả tin nhắn SAU tin nhắn được restore
- ❌ AI response của các tin nhắn đó

### 💾 Lưu trữ:
- Lịch sử chỉ tồn tại trong session hiện tại
- Reload page = mất lịch sử
- (Có thể thêm localStorage persistence sau)

---

## 🎮 Workflow Examples

### Example 1: Thử nhiều cách hỏi
```
1. "Giải thích Docker"
   → Response quá kỹ thuật
   
2. Edit → "Giải thích Docker cho người mới"
   → Response dễ hiểu hơn
   
3. Hmm, muốn thử hỏi cách khác
   → Restore về "Giải thích Docker"
   → Edit → "Giải thích Docker bằng ví dụ thực tế"
   → Response với examples
```

### Example 2: A/B Testing prompts
```
Branch A: "Viết story về robot" → Response A → "Tiếp tục với twist"
Branch B: Restore → "Viết story về alien" → Response B → "Thêm action"

So sánh 2 nhánh để xem cái nào hay hơn!
```

### Example 3: Undo mạnh mẽ
```
1. Hỏi câu A → Response OK
2. Edit → Câu B → Response không thích
3. Edit → Câu C → Response vẫn không thích
4. Restore về Câu A → Quay lại response OK
5. Thử hỏi theo hướng khác
```

---

## 🔑 Key Features

| Feature | Description |
|---------|-------------|
| 📜 **Version History** | Xem tất cả các phiên bản đã edit |
| ↩️ **Restore** | Quay lại bất kỳ phiên bản nào |
| 🌿 **Branch** | Tiếp tục chat từ phiên bản cũ (tạo nhánh mới) |
| 💾 **Auto-save** | Tự động lưu trước khi restore |
| ♾️ **Unlimited** | Không giới hạn số lần restore |
| ⏱️ **Timestamp** | Mỗi phiên bản có thời gian chính xác |

---

## 🆚 So sánh với Edit thông thường

### Edit thông thường:
- Edit tin nhắn → Response mới
- Mất response cũ
- Không thể quay lại

### Edit + Restore:
- Edit tin nhắn → Response mới
- Giữ tất cả phiên bản cũ
- Có thể quay lại bất kỳ lúc nào
- Tạo nhiều nhánh từ một điểm

---

## 🎯 Best Practices

### ✅ Nên:
1. **Thử nhiều cách hỏi**: Đừng ngại edit và restore
2. **Lưu ý naming**: Đặt câu hỏi rõ ràng để dễ nhận biết trong history
3. **Experiment**: Thử A/B testing các prompts khác nhau
4. **Branch early**: Nếu thấy có thể đi 2 hướng, tạo branch sớm

### ❌ Tránh:
1. **Edit quá nhiều**: Nhiều quá khó theo dõi (nên tạo chat mới)
2. **Restore liên tục**: Có thể gây loạn timeline
3. **Quên context**: Nhớ rằng restore sẽ xóa messages sau đó

---

## 🎓 Tips & Tricks

### Tip 1: Planning multiple approaches
```
Hỏi câu general trước → Branch ra các câu cụ thể
"Học Python" 
  ├─ Branch 1: "Học Python cho data science"
  ├─ Branch 2: "Học Python cho web dev"
  └─ Branch 3: "Học Python cho automation"
```

### Tip 2: Iterative refinement
```
Prompt 1 → Not good → Restore
Prompt 2 → Better → Restore  
Prompt 3 → Best! → Continue
```

### Tip 3: Preserve good conversations
```
Found good response? 
→ Đừng edit nữa, tạo chat mới thay vì
→ Hoặc export before experimenting
```

---

## 🐛 Troubleshooting

### Q: Không thấy nút "Xem lịch sử"?
**A:** Nút chỉ xuất hiện sau khi bạn edit lần đầu tiên.

### Q: Restore rồi mất hết chat?
**A:** Đúng vậy! Restore sẽ xóa tất cả messages sau message được restore.

### Q: Reload page thì lịch sử mất?
**A:** Có, lịch sử chỉ tồn tại trong session (chưa persist vào storage).

### Q: Có giới hạn số lần restore không?
**A:** Không, restore bao nhiêu lần cũng được!

### Q: Restore có ảnh hưởng đến chat sessions khác?
**A:** Không, mỗi chat session độc lập.

---

## 🎬 Demo Flow

```
1. 🧑 You: "Ôi, bạn hỏi là ai nào ?"
   🤖 AI: "hê hê chào bạn! Có chuyện vui gì mà cười tươi thế?"
   
2. 🧑 You: [Edit] → "hê hê, tôi đẹp trai"
   🤖 AI: "Hè hè, tự tin là tốt đó! 😊"
   
3. 🧑 You: [Xem lịch sử]
   📜 Modal shows:
      ✅ "hê hê, tôi đẹp trai" (current)
      📝 "Ôi, bạn hỏi là ai nào ?" [↩️ Khôi phục]
   
4. 🧑 You: [Bấm ↩️ Khôi phục ở phiên bản 1]
   ⚠️ Confirm: "Bạn có chắc muốn khôi phục..."
   
5. 🧑 You: [Yes]
   🤖 AI: Quay lại response của "Ôi, bạn hỏi là ai nào ?"
   
6. 🧑 You: "Tôi là người yêu bạn"
   🤖 AI: [Response theo nhánh mới]
   
→ Bây giờ có 2 branches:
   Branch A: "ai nào ?" → "đẹp trai" → ...
   Branch B: "ai nào ?" → "người yêu" → ...
```

---

## 🎉 Kết luận

Tính năng **Restore & Branch** giúp bạn:
- 🔄 Linh hoạt thử nghiệm nhiều hướng
- 💪 Mạnh mẽ hơn Edit thông thường
- 🌳 Tạo "conversation tree" như ChatGPT
- 🎯 Tối ưu hóa prompts hiệu quả

**Thử ngay và tận hưởng sức mạnh của branching conversations!** 🚀
