# 🚀 Quick Start Guide - AI Assistant Hub

## Khởi động nhanh (Recommended)

### Cách 1: Khởi động Hub đơn giản
```bash
python hub.py
```
Sau đó truy cập: **http://localhost:3000**

### Cách 2: Khởi động tất cả services (Windows)
```bash
start_all.bat
```

### Cách 3: Khởi động tất cả services (Linux/Mac)
```bash
chmod +x start_all.sh
./start_all.sh
```

---

## 📋 Checklist trước khi chạy

- [ ] Đã cài Python 3.8+
- [ ] Đã cài đặt dependencies: `pip install -r requirements.txt`
- [ ] Đã cấu hình API keys trong file `.env`
- [ ] Ports 5000, 5001, 5002, 3000 chưa bị sử dụng

---

## 🎯 Sử dụng từng service riêng lẻ

### ChatBot (Port 5000)
```bash
cd ChatBot
pip install -r requirements.txt
python app.py
```

### Speech2Text (Port 5001)
```bash
cd "Speech2Text Services/app"
pip install -r ../requirements.txt
python web_ui.py --port 5001
```

### Text2SQL (Port 5002)
```bash
cd "Text2SQL Services"
pip install -r requirements.txt
python app.py --port 5002
```

---

## 🔥 Lưu ý quan trọng

⚠️ **Chạy riêng lẻ để tránh quá tải:**
- Mỗi service chạy trên terminal/window riêng
- Hub Gateway chỉ là điểm truy cập tập trung
- Services hoạt động độc lập, không phụ thuộc lẫn nhau

⚠️ **Yêu cầu tài nguyên:**
- ChatBot: 2GB RAM
- Speech2Text: 4-8GB RAM (có GPU tốt hơn)
- Text2SQL: 2GB RAM
- Hub: < 512MB RAM

---

## ✅ Kiểm tra services đang chạy

```bash
# Windows
netstat -ano | findstr "5000 5001 5002 3000"

# Linux/Mac
lsof -i :5000,5001,5002,3000
```

---

## 🎨 Giao diện Hub

Hub Gateway có giao diện web đẹp với:
- ✨ Tailwind CSS
- 🎭 Animations mượt mà
- 📱 Responsive design
- 🌙 Dark theme
- 🚀 Fast loading

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, xem chi tiết trong `HUB_README.md`

---

**Made with ❤️ by AI Assistant Team**
