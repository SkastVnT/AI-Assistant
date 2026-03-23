# Deploy to Custom Domain: skastapp.online

## Tổng quan

Hướng dẫn này giúp bạn deploy AI-Assistant lên domain `skastapp.online`.

## Các phương pháp deploy

### Phương pháp 1: Cloudflare Tunnel (Khuyến nghị - Free)

Sử dụng Cloudflare Tunnel để expose local service qua domain tùy chỉnh.

#### Bước 1: Thêm domain vào Cloudflare
1. Đăng nhập vào [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click "Add a Site"
3. Nhập `skastapp.online`
4. Chọn plan Free
5. Cloudflare sẽ cung cấp 2 nameservers

#### Bước 2: Cập nhật Nameservers tại nhà đăng ký domain
1. Đăng nhập vào nhà đăng ký domain của bạn
2. Tìm mục "Nameservers" hoặc "DNS"
3. Thay đổi thành nameservers của Cloudflare:
   - `xxxxx.ns.cloudflare.com`
   - `yyyyy.ns.cloudflare.com`
4. Chờ 24-48h để DNS propagate (thường nhanh hơn)

#### Bước 3: Cài đặt Cloudflared
```bash
# Ubuntu/Debian
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Authenticate
cloudflared tunnel login
```

#### Bước 4: Tạo Tunnel
```bash
# Tạo tunnel mới
cloudflared tunnel create ai-assistant

# Lấy tunnel ID (ví dụ: a1b2c3d4-xxxx-yyyy-zzzz-123456789abc)
cloudflared tunnel list
```

#### Bước 5: Cấu hình config.yml
Tạo file `~/.cloudflared/config.yml`:
```yaml
tunnel: ai-assistant
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  # Main chatbot
  - hostname: skastapp.online
    service: http://localhost:5000
  
  # www subdomain
  - hostname: www.skastapp.online
    service: http://localhost:5000
  
  # ComfyUI (optional)
  - hostname: comfy.skastapp.online
    service: http://localhost:8189
  
  # API subdomain (optional)
  - hostname: api.skastapp.online
    service: http://localhost:5000
  
  # Catch-all
  - service: http_status:404
```

#### Bước 6: Thêm DNS Records
```bash
# Tạo CNAME records trong Cloudflare
cloudflared tunnel route dns ai-assistant skastapp.online
cloudflared tunnel route dns ai-assistant www.skastapp.online
cloudflared tunnel route dns ai-assistant comfy.skastapp.online
cloudflared tunnel route dns ai-assistant api.skastapp.online
```

#### Bước 7: Chạy Tunnel
```bash
# Test
cloudflared tunnel run ai-assistant

# Chạy như service (production)
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

---

### Phương pháp 2: Cloudflare DNS + Temporary Tunnel

Nếu bạn đang chạy trên RunPod/cloud với IP động:

#### Bước 1: Thêm domain vào Cloudflare (như trên)

#### Bước 2: Tạo script tự động update DNS
Tạo file `update_cloudflare_dns.sh`:
```bash
#!/bin/bash
# Lấy URL từ tunnel hiện tại
TUNNEL_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-chatbot.log | head -1)

echo "Current tunnel: $TUNNEL_URL"
echo "Access via: https://skastapp.online (after Cloudflare setup)"
```

#### Bước 3: Sử dụng Cloudflare Page Rules
1. Trong Cloudflare Dashboard > Rules > Page Rules
2. Tạo rule: `*skastapp.online/*`
3. Setting: Forwarding URL (301 Redirect) to tunnel URL

---

### Phương pháp 3: VPS/Cloud Server (Production)

Deploy trên VPS như DigitalOcean, AWS, GCP với IP tĩnh.

#### Nginx Reverse Proxy config:
```nginx
server {
    listen 80;
    server_name skastapp.online www.skastapp.online;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name skastapp.online www.skastapp.online;
    
    ssl_certificate /etc/letsencrypt/live/skastapp.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skastapp.online/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
    
    location /comfyui/ {
        proxy_pass http://localhost:8189/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
}
```

#### SSL với Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d skastapp.online -d www.skastapp.online
```

---

## Quick Start (Hiện tại trên RunPod)

Vì đang chạy trên RunPod với IP động, sử dụng phương pháp sau:

### 1. Lấy tunnel URL hiện tại:
```bash
cat /workspace/AI-Assistant/public_urls.txt
```

### 2. Trong Cloudflare Dashboard:
1. Add site `skastapp.online`
2. Update nameservers tại nhà đăng ký
3. Tạo CNAME record:
   - Type: CNAME
   - Name: @ (hoặc skastapp.online)
   - Target: `monsters-oct-specially-bugs.trycloudflare.com` (tunnel hiện tại)
   - Proxy: ON (orange cloud)

### 3. Script tự động update tunnel:
```bash
#!/bin/bash
# /workspace/AI-Assistant/scripts/update_domain.sh

# Lấy tunnel URL mới nhất
TUNNEL_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /workspace/AI-Assistant/logs/tunnel-chatbot.log | head -1)

if [ -n "$TUNNEL_URL" ]; then
    echo "✅ Current tunnel: $TUNNEL_URL"
    echo "📝 Update this in Cloudflare DNS as CNAME target for skastapp.online"
    echo "$TUNNEL_URL" > /workspace/AI-Assistant/current_tunnel.txt
else
    echo "❌ No tunnel found"
fi
```

---

## Biến môi trường cần thiết

Thêm vào `.env`:
```env
# Domain Configuration
DOMAIN_NAME=skastapp.online
ALLOWED_HOSTS=skastapp.online,www.skastapp.online,localhost

# Cloudflare (optional - for API access)
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ZONE_ID=your_zone_id
```

---

## Troubleshooting

### DNS chưa propagate
- Kiểm tra: `nslookup skastapp.online`
- Hoặc: `dig skastapp.online`
- Sử dụng [DNSChecker](https://dnschecker.org) để kiểm tra global

### SSL Error
- Trong Cloudflare > SSL/TLS > Overview
- Đặt mode: "Flexible" (nếu backend không có SSL)
- Hoặc "Full" nếu có SSL local

### 525 SSL Handshake Failed
- Kiểm tra backend đang chạy
- Trong Cloudflare SSL mode: chuyển sang "Flexible"

### 522 Connection Timed Out
- Kiểm tra firewall
- Kiểm tra tunnel đang chạy: `cloudflared tunnel list`
