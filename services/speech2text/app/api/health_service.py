"""
Health Monitor Service - System Health and Performance Monitoring
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import time
import logging
import psutil
import requests
import redis
import psycopg2
from typing import Dict, List
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Monitor Service", version="1.0.0")

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://s2t_user:s2t_password@postgres:5432/s2t_db')

# Redis connection
redis_client = None
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")

class ServiceHealth(BaseModel):
    name: str
    status: str
    response_time: float
    last_check: float

class SystemHealth(BaseModel):
    overall_status: str
    timestamp: float
    system_metrics: Dict
    services: List[ServiceHealth]

def get_system_metrics():
    """Get system performance metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        "uptime": time.time() - psutil.boot_time()
    }

def check_service_health(service_name: str, url: str) -> ServiceHealth:
    """Check health of individual service"""
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            status = "healthy"
        else:
            status = "unhealthy"
            
    except requests.exceptions.Timeout:
        status = "timeout"
        response_time = 10.0
    except requests.exceptions.ConnectionError:
        status = "unreachable"
        response_time = time.time() - start_time
    except Exception as e:
        status = "error"
        response_time = time.time() - start_time
        logger.error(f"Error checking {service_name}: {e}")
    
    return ServiceHealth(
        name=service_name,
        status=status,
        response_time=response_time,
        last_check=time.time()
    )

def check_database():
    """Check PostgreSQL database health"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "unhealthy"

def check_redis():
    """Check Redis health"""
    if not redis_client:
        return "unavailable"
    
    try:
        redis_client.ping()
        return "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return "unhealthy"

@app.get("/health", response_model=SystemHealth)
async def full_health_check():
    """Comprehensive system health check"""
    
    # Check all services
    services = [
        ("api", "http://api:8000/health"),
        ("t5-service", "http://t5-service:8001/health"),
        ("phowhisper-service", "http://phowhisper-service:8002/health"),
        ("whisper-service", "http://whisper-service:8003/health"),
        ("gemini-proxy", "http://gemini-proxy:8004/health")
    ]
    
    service_health = []
    healthy_services = 0
    
    for service_name, url in services:
        health = check_service_health(service_name, url)
        service_health.append(health)
        if health.status == "healthy":
            healthy_services += 1
    
    # Add database and Redis checks
    db_status = check_database()
    redis_status = check_redis()
    
    service_health.extend([
        ServiceHealth(
            name="postgres",
            status=db_status,
            response_time=0.0,
            last_check=time.time()
        ),
        ServiceHealth(
            name="redis",
            status=redis_status,
            response_time=0.0,
            last_check=time.time()
        )
    ])
    
    if db_status == "healthy":
        healthy_services += 1
    if redis_status == "healthy":
        healthy_services += 1
    
    # Determine overall status
    total_services = len(service_health)
    if healthy_services == total_services:
        overall_status = "healthy"
    elif healthy_services >= total_services * 0.7:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    # Get system metrics
    system_metrics = get_system_metrics()
    
    return SystemHealth(
        overall_status=overall_status,
        timestamp=time.time(),
        system_metrics=system_metrics,
        services=service_health
    )

@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""
    return {
        "timestamp": time.time(),
        "metrics": get_system_metrics()
    }

@app.get("/services")
async def get_service_status():
    """Get status of all services"""
    services = [
        ("api", "http://api:8000/health"),
        ("t5-service", "http://t5-service:8001/health"),
        ("phowhisper-service", "http://phowhisper-service:8002/health"), 
        ("whisper-service", "http://whisper-service:8003/health"),
        ("gemini-proxy", "http://gemini-proxy:8004/health")
    ]
    
    results = {}
    for service_name, url in services:
        health = check_service_health(service_name, url)
        results[service_name] = health.dict()
    
    # Add infrastructure services
    results["postgres"] = {"status": check_database()}
    results["redis"] = {"status": check_redis()}
    
    return results

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Health Monitor Service",
        "version": "1.0.0",
        "description": "System health and performance monitoring",
        "endpoints": ["/health", "/metrics", "/services"]
    }

if __name__ == "__main__":
    uvicorn.run("health_service:app", host="0.0.0.0", port=8080, reload=False)