# 🚀 RAG Services - Deployment Guide

> **Complete guide for deploying RAG Services to production**  
> **Version:** 1.0.0  
> **Difficulty:** Intermediate  
> **Duration:** 2-4 hours  
> **Last Updated:** November 6, 2025

---

## 📋 OVERVIEW

This guide covers deployment options cho RAG Services từ development đến production environment.

### Deployment Options

| Option | Complexity | Cost | Scalability | Best For |
|--------|-----------|------|-------------|----------|
| **Local Server** | Low | Free | Low | Development, Testing |
| **VPS (DigitalOcean)** | Medium | $10-50/mo | Medium | Small-Medium apps |
| **Docker** | Medium | Varies | High | Any scale |
| **Kubernetes** | High | Varies | Very High | Enterprise |
| **Serverless** | Low | Pay-per-use | Auto | Variable load |

---

## 🎯 PREREQUISITES

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- OS: Ubuntu 20.04+ / Windows Server 2019+

**Recommended**:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- OS: Ubuntu 22.04 LTS

### Software Requirements

```bash
# Required
Python 3.11+
pip 23.0+
git

# Optional but recommended
Redis 7.0+
Nginx 1.20+
Supervisor 4.2+
```

### API Keys Required

- OpenAI API Key (GPT-4)
- DeepSeek API Key
- Google Gemini API Key
- (Optional) Redis Cloud account

---

## 🖥️ OPTION 1: LOCAL SERVER DEPLOYMENT

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx supervisor redis-server

# Verify installations
python3.11 --version
redis-server --version
nginx -v
```

### Step 2: Clone Repository

```bash
# Create app directory
sudo mkdir -p /var/www/rag-services
sudo chown $USER:$USER /var/www/rag-services

# Clone repo
cd /var/www/rag-services
git clone https://github.com/SkastVnT/AI-Assistant.git .
cd "RAG Services"
```

### Step 3: Setup Virtual Environment

```bash
# Create venv
python3.11 -m venv RAG

# Activate
source RAG/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Step 4: Configuration

```bash
# Copy environment file
cp .env.example .env

# Edit with your keys
nano .env
```

**`.env` configuration**:

```properties
# Production settings
FLASK_ENV=production
FLASK_SECRET_KEY=your-super-secret-key-change-this

# Service
RAG_PORT=5003
WORKERS=4

# API Keys
OPENAI_API_KEY=sk-proj-your-key
DEEPSEEK_API_KEY=sk-your-key
GEMINI_API_KEY_1=your-key

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/rag-services/app.log
```

### Step 5: Setup Gunicorn

Create `/var/www/rag-services/RAG Services/gunicorn_config.py`:

```python
import multiprocessing

# Server socket
bind = "127.0.0.1:5003"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = '/var/log/rag-services/access.log'
errorlog = '/var/log/rag-services/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'rag-services'

# Server mechanics
daemon = False
pidfile = '/var/run/rag-services.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if using HTTPS directly)
# keyfile = '/path/to/private.key'
# certfile = '/path/to/certificate.crt'
```

### Step 6: Setup Supervisor

Create `/etc/supervisor/conf.d/rag-services.conf`:

```ini
[program:rag-services]
directory=/var/www/rag-services/RAG Services
command=/var/www/rag-services/RAG Services/RAG/bin/gunicorn -c gunicorn_config.py app:app
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/rag-services/supervisor-error.log
stdout_logfile=/var/log/rag-services/supervisor-access.log
environment=PATH="/var/www/rag-services/RAG Services/RAG/bin"
```

```bash
# Create log directory
sudo mkdir -p /var/log/rag-services
sudo chown www-data:www-data /var/log/rag-services

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rag-services

# Check status
sudo supervisorctl status rag-services
```

### Step 7: Setup Nginx

Create `/etc/nginx/sites-available/rag-services`:

```nginx
upstream rag_services {
    server 127.0.0.1:5003 fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    client_max_body_size 50M;
    
    # Redirect to HTTPS (uncomment after SSL setup)
    # return 301 https://$server_name$request_uri;
    
    location / {
        proxy_pass http://rag_services;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # WebSocket support (for future use)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static/ {
        alias /var/www/rag-services/RAG Services/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Rate limiting (optional)
    limit_req_zone $binary_remote_addr zone=rag_limit:10m rate=10r/s;
    limit_req zone=rag_limit burst=20 nodelay;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/rag-services /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### Step 8: Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is set up automatically
# Test renewal
sudo certbot renew --dry-run
```

### Step 9: Setup Firewall

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 10: Verify Deployment

```bash
# Check service status
sudo supervisorctl status rag-services

# Check logs
tail -f /var/log/rag-services/app.log

# Test API
curl http://your-domain.com/health

# Test query endpoint
curl -X POST http://your-domain.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}'
```

---

## 🐳 OPTION 2: DOCKER DEPLOYMENT

### Step 1: Create Dockerfile

Create `RAG Services/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p data/documents data/vectordb logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Expose port
EXPOSE 5003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5003/health || exit 1

# Run application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5003", "--timeout", "120", "app:app"]
```

### Step 2: Create docker-compose.yml

Create `RAG Services/docker-compose.yml`:

```yaml
version: '3.8'

services:
  rag-services:
    build: .
    container_name: rag-services
    restart: unless-stopped
    ports:
      - "5003:5003"
    environment:
      - FLASK_ENV=production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    networks:
      - rag-network

  redis:
    image: redis:7-alpine
    container_name: rag-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - rag-network

  nginx:
    image: nginx:alpine
    container_name: rag-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - rag-services
    networks:
      - rag-network

volumes:
  redis-data:

networks:
  rag-network:
    driver: bridge
```

### Step 3: Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f rag-services

# Check status
docker-compose ps

# Stop services
docker-compose down
```

### Step 4: Docker Management Commands

```bash
# Restart service
docker-compose restart rag-services

# Update service
git pull
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f

# Execute command in container
docker-compose exec rag-services python -c "print('Hello')"

# Clean up
docker-compose down -v  # Remove volumes too
docker system prune -a  # Clean all unused containers/images
```

---

## ☁️ OPTION 3: CLOUD DEPLOYMENT

### DigitalOcean App Platform

1. **Create App**:
   - Go to DigitalOcean Dashboard
   - Create → Apps → Create App
   - Connect GitHub repository

2. **Configure**:
   ```yaml
   name: rag-services
   services:
   - name: web
     github:
       repo: SkastVnT/AI-Assistant
       branch: master
       deploy_on_push: true
     source_dir: /RAG Services
     build_command: pip install -r requirements.txt
     run_command: gunicorn -w 4 -b 0.0.0.0:8080 app:app
     envs:
     - key: FLASK_ENV
       value: production
     - key: OPENAI_API_KEY
       value: ${OPENAI_API_KEY}
       type: SECRET
     health_check:
       http_path: /health
     instance_count: 2
     instance_size_slug: basic-xs
   databases:
   - name: redis
     engine: REDIS
     version: "7"
   ```

3. **Deploy**: Click "Create Resources"

### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 rag-services --region us-east-1

# Create environment
eb create rag-services-prod

# Deploy
eb deploy

# Open in browser
eb open

# View logs
eb logs

# SSH into instance
eb ssh
```

### Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create rag-services-app

# Add buildpack
heroku buildpacks:set heroku/python

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set OPENAI_API_KEY=your-key

# Add Redis
heroku addons:create heroku-redis:hobby-dev

# Deploy
git push heroku master

# Open app
heroku open

# View logs
heroku logs --tail
```

---

## 📊 MONITORING & LOGGING

### Setup Monitoring

**Install monitoring tools**:

```bash
# Install Prometheus
# See: https://prometheus.io/docs/prometheus/latest/installation/

# Install Grafana
# See: https://grafana.com/docs/grafana/latest/setup-grafana/installation/
```

**Configure metrics endpoint** in `app.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('rag_requests_total', 'Total requests')
request_duration = Histogram('rag_request_duration_seconds', 'Request duration')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### Logging Best Practices

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

### Log Aggregation with ELK Stack

1. **Elasticsearch**: Store logs
2. **Logstash**: Process logs
3. **Kibana**: Visualize logs

---

## 🔒 SECURITY CHECKLIST

### Pre-deployment Security

- [ ] Change default secrets in `.env`
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall rules
- [ ] Disable debug mode (`FLASK_ENV=production`)
- [ ] Set strong Redis password
- [ ] Implement rate limiting
- [ ] Add API authentication
- [ ] Configure CORS properly
- [ ] Enable request logging
- [ ] Set up monitoring & alerts

### Security Headers

Add to Nginx config:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

---

## 🚨 TROUBLESHOOTING

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
sudo supervisorctl tail -f rag-services stderr

# Check Python errors
source RAG/bin/activate
python app.py

# Check port availability
sudo lsof -i :5003
```

#### 2. High Memory Usage

```bash
# Monitor resources
htop

# Reduce Gunicorn workers
# Edit gunicorn_config.py
workers = 2

# Restart service
sudo supervisorctl restart rag-services
```

#### 3. Slow Response Times

- Check Redis connection
- Monitor LLM API latency
- Optimize vector database queries
- Increase cache TTL
- Add more workers

#### 4. SSL Certificate Issues

```bash
# Renew certificate
sudo certbot renew

# Check certificate
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

---

## 📈 SCALING

### Vertical Scaling

Upgrade server resources:
- More CPU cores
- More RAM
- Faster SSD

### Horizontal Scaling

**Load Balancer Setup**:

```nginx
upstream rag_backend {
    least_conn;
    server 192.168.1.10:5003;
    server 192.168.1.11:5003;
    server 192.168.1.12:5003;
}

server {
    location / {
        proxy_pass http://rag_backend;
    }
}
```

**Redis Cluster**:
- Use Redis Cluster for distributed caching
- Or Redis Sentinel for high availability

---

## ✅ POST-DEPLOYMENT CHECKLIST

- [ ] Service is running
- [ ] Health check returns 200 OK
- [ ] API endpoints respond correctly
- [ ] SSL certificate is valid
- [ ] Logs are being written
- [ ] Monitoring is active
- [ ] Backups are configured
- [ ] Documentation is updated
- [ ] Team is notified
- [ ] DNS records are correct

---

## 📚 RESOURCES

- [Flask Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)

---

<div align="center">

## 🎉 DEPLOYMENT GUIDE COMPLETE

**Your RAG Services is now production-ready!**

---

**📅 Created:** November 6, 2025  
**👤 Author:** SkastVnT  
**🔄 Version:** 1.0.0  
**📍 Location:** `RAG Services/docs/DEPLOYMENT_GUIDE.md`  
**🏷️ Tags:** #deployment #production #docker #nginx

[🏠 Back to Docs](../README.md) | [📖 API Docs](./API_DOCUMENTATION.md)

</div>
