# Docker Setup Guide - AI-Assistant

Complete guide for setting up AI-Assistant with Docker, PostgreSQL, and Redis.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Service Management](#service-management)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## 🔧 Prerequisites

### Required Software

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
  - Version: 20.10+
  - Docker Compose: 2.0+
- **Git** for version control
- **Python 3.10+** (for local development)

### Hardware Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB free space

**Recommended (with GPU services):**
- CPU: 8+ cores
- RAM: 16GB+
- GPU: NVIDIA RTX 3060+ (12GB VRAM)
- Storage: 50GB+ free space

### Check Installation

```powershell
# Check Docker
docker --version
docker-compose --version

# Check Docker is running
docker ps

# Check Python (for local scripts)
python --version
```

---

## 🚀 Quick Start

### 1. Clone Repository

```powershell
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

### 2. Create Environment File

```powershell
# Copy example environment file
Copy-Item .env.example .env

# Edit .env with your credentials
notepad .env
```

**Required changes in `.env`:**
```env
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here
DATABASE_URL=postgresql://postgres:your_secure_password_here@postgres:5432/ai_assistant
```

### 3. Start Database Services

```powershell
# Start PostgreSQL and Redis only
docker-compose up -d postgres redis pgadmin

# Check services are healthy
docker-compose ps

# View logs
docker-compose logs -f postgres redis
```

### 4. Initialize Database

```powershell
# Wait for PostgreSQL to be ready (check logs)
# Then run setup script

python database/scripts/setup_database.py
```

### 5. Start All Services

```powershell
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 6. Access Services

- **Hub Gateway:** http://localhost:3000
- **ChatBot:** http://localhost:5001
- **pgAdmin:** http://localhost:5050
- **Redis:** localhost:6379
- **PostgreSQL:** localhost:5432

---

## ⚙️ Environment Configuration

### Database Configuration

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_assistant

# Connection string (for local access)
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ai_assistant

# Connection string (for Docker containers)
DATABASE_URL=postgresql://postgres:your_password@postgres:5432/ai_assistant
```

### Redis Configuration

```env
REDIS_PASSWORD=redis123
REDIS_URL=redis://:redis123@localhost:6379/0

# For Docker containers:
REDIS_URL=redis://:redis123@redis:6379/0
```

### pgAdmin Configuration

```env
PGADMIN_EMAIL=admin@aiassistant.local
PGADMIN_PASSWORD=admin123
```

**Access pgAdmin:**
1. Open http://localhost:5050
2. Login with credentials above
3. Server is pre-configured as "AI-Assistant PostgreSQL"

---

## 💾 Database Setup

### Method 1: Automated Setup (Recommended)

```powershell
# Run setup script
python database/scripts/setup_database.py

# This will:
# - Create all tables
# - Create admin user
# - Seed demo data (optional)
```

### Method 2: Manual Setup

```powershell
# Test connection
python database/utils/test_connection.py

# Or use Python
python
>>> from database.utils import init_db
>>> from database.models import Base
>>> engine = init_db()
>>> Base.metadata.create_all(engine)
>>> exit()
```

### Verify Database

```powershell
# Check tables exist
docker exec -it ai-assistant-postgres psql -U postgres -d ai_assistant -c "\dt"

# Count records
docker exec -it ai-assistant-postgres psql -U postgres -d ai_assistant -c "SELECT COUNT(*) FROM users;"
```

### Database Migrations

```powershell
# Analyze existing JSON data
python database/scripts/analyze_existing_data.py

# Run migration (dry-run first)
python database/scripts/migrate_conversations.py --dry-run

# Run actual migration
python database/scripts/migrate_conversations.py

# Validate migration
python database/scripts/validate_migration.py
```

---

## 🛠️ Service Management

### Start Services

```powershell
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis
docker-compose up -d chatbot

# Start with logs
docker-compose up postgres redis
```

### Stop Services

```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop postgres
```

### Restart Services

```powershell
# Restart all
docker-compose restart

# Restart specific
docker-compose restart postgres redis
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f chatbot

# Last 100 lines
docker-compose logs --tail=100 postgres
```

### Check Service Status

```powershell
# View status
docker-compose ps

# View health checks
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check resource usage
docker stats
```

---

## 🐛 Troubleshooting

### PostgreSQL Issues

#### Issue: Connection Refused

```powershell
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs for errors
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check port is not in use
netstat -an | findstr :5432
```

#### Issue: Authentication Failed

```powershell
# Verify password in .env matches docker-compose
# Restart with fresh database:

docker-compose down postgres
docker volume rm ai-assistant_postgres-data
docker-compose up -d postgres
```

#### Issue: Database Does Not Exist

```powershell
# Create database manually
docker exec -it ai-assistant-postgres psql -U postgres -c "CREATE DATABASE ai_assistant;"

# Or recreate container
docker-compose down postgres
docker-compose up -d postgres
```

### Redis Issues

#### Issue: Connection Refused

```powershell
# Check Redis is running
docker-compose ps redis

# Test connection
docker exec -it ai-assistant-redis redis-cli -a redis123 ping
# Should return: PONG

# Restart Redis
docker-compose restart redis
```

#### Issue: Authentication Error

```powershell
# Check password in .env
# Test with correct password:
docker exec -it ai-assistant-redis redis-cli -a YOUR_PASSWORD ping
```

### pgAdmin Issues

#### Issue: Cannot Access pgAdmin

```powershell
# Check pgAdmin is running
docker-compose ps pgadmin

# Check logs
docker-compose logs pgadmin

# Restart pgAdmin
docker-compose restart pgadmin

# Access at: http://localhost:5050
```

#### Issue: Server Not Found in pgAdmin

1. Login to pgAdmin
2. Right-click "Servers" → "Register" → "Server"
3. **General tab:**
   - Name: AI-Assistant PostgreSQL
4. **Connection tab:**
   - Host: `postgres` (Docker service name)
   - Port: `5432`
   - Database: `ai_assistant`
   - Username: `postgres`
   - Password: (from .env)

### Docker Issues

#### Issue: Port Already in Use

```powershell
# Find process using port
netstat -ano | findstr :5432
netstat -ano | findstr :6379
netstat -ano | findstr :5050

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in docker-compose.yml
```

#### Issue: Disk Space Full

```powershell
# Check disk usage
docker system df

# Clean up unused images/containers
docker system prune -a

# Remove specific volumes
docker volume ls
docker volume rm <volume_name>
```

#### Issue: Container Won't Start

```powershell
# Check logs
docker-compose logs <service_name>

# Rebuild container
docker-compose build --no-cache <service_name>
docker-compose up -d <service_name>

# Remove and recreate
docker-compose rm -f <service_name>
docker-compose up -d <service_name>
```

---

## 🔒 Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong passwords (20+ characters)
- [ ] Enable SSL/TLS for PostgreSQL
- [ ] Use environment-specific .env files
- [ ] Restrict pgAdmin access (firewall)
- [ ] Enable PostgreSQL authentication
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity

### Production Environment File

```env
# Production PostgreSQL
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=<very_strong_password_here>
POSTGRES_DB=ai_assistant_prod

DATABASE_URL=postgresql://prod_user:<password>@db.example.com:5432/ai_assistant_prod

# Production Redis
REDIS_PASSWORD=<very_strong_redis_password>
REDIS_URL=redis://:<password>@cache.example.com:6379/0

# Disable pgAdmin in production
# Or restrict to internal network only
```

### Backup Strategy

```powershell
# Backup database
docker exec ai-assistant-postgres pg_dump -U postgres ai_assistant > backup.sql

# Backup with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec ai-assistant-postgres pg_dump -U postgres ai_assistant > "backup_$timestamp.sql"

# Restore database
docker exec -i ai-assistant-postgres psql -U postgres ai_assistant < backup.sql

# Automated backup script (daily)
# See: database/scripts/backup_database.ps1
```

### Monitoring

```powershell
# Check container health
docker-compose ps

# Monitor resource usage
docker stats

# Check PostgreSQL connections
docker exec -it ai-assistant-postgres psql -U postgres -d ai_assistant -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
docker exec -it ai-assistant-redis redis-cli -a redis123 info memory
```

---

## 📚 Additional Resources

- **PostgreSQL Documentation:** https://www.postgresql.org/docs/
- **Redis Documentation:** https://redis.io/documentation
- **Docker Compose Reference:** https://docs.docker.com/compose/
- **pgAdmin Documentation:** https://www.pgadmin.org/docs/

---

## 🆘 Need Help?

1. Check [Troubleshooting](#troubleshooting) section
2. View logs: `docker-compose logs -f`
3. Check GitHub Issues: https://github.com/SkastVnT/AI-Assistant/issues
4. Read documentation in `docs/` folder

---

## 📝 Quick Reference

### Common Commands

```powershell
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f <service>

# Restart service
docker-compose restart <service>

# Check status
docker-compose ps

# Enter container
docker exec -it <container_name> bash

# PostgreSQL CLI
docker exec -it ai-assistant-postgres psql -U postgres -d ai_assistant

# Redis CLI
docker exec -it ai-assistant-redis redis-cli -a redis123

# Cleanup
docker system prune -a
```

---

**Last Updated:** November 2025  
**Version:** 1.0.0
