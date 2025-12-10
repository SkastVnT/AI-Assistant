"""
Redis Integration for LoRA Training WebUI
==========================================

Sử dụng Redis để:
1. Task Queue (Celery) - Queue training jobs
2. Caching - Cache dataset metadata, config recommendations
3. Session Management - WebSocket sessions
4. Progress Tracking - Real-time training progress
5. Result Storage - Training metrics, logs

Created: 2024-12-01
Version: 1.0.0
"""

import os
import json
import redis
from typing import Dict, List, Optional, Any
from datetime import timedelta
import pickle


class RedisManager:
    """Redis connection manager cho LoRA Training"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 db: int = 0,
                 decode_responses: bool = True):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host (default: localhost hoặc REDIS_HOST env)
            port: Redis port (default: 6379 hoặc REDIS_PORT env)
            db: Redis database number
            decode_responses: Auto decode bytes to strings
        """
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db
        
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis.ping()
            print(f"✅ Redis connected: {self.host}:{self.port}")
            
        except redis.ConnectionError as e:
            print(f"⚠️ Redis connection failed: {e}")
            print("Falling back to in-memory mode (no persistence)")
            self.redis = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.redis:
            return False
        try:
            return self.redis.ping()
        except:
            return False


class TrainingTaskQueue:
    """Task queue cho training jobs using Redis"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
        self.queue_key = 'lora:training:queue'
        self.active_key = 'lora:training:active'
        self.completed_key = 'lora:training:completed'
    
    def add_task(self, task_id: str, config: Dict) -> bool:
        """Add training task to queue"""
        if not self.redis:
            return False
        
        task_data = {
            'task_id': task_id,
            'config': config,
            'status': 'queued',
            'created_at': self._timestamp()
        }
        
        # Add to queue (FIFO)
        self.redis.rpush(self.queue_key, json.dumps(task_data))
        
        # Store task details
        self.redis.setex(
            f'lora:task:{task_id}',
            timedelta(days=7),  # Keep for 7 days
            json.dumps(task_data)
        )
        
        return True
    
    def get_next_task(self) -> Optional[Dict]:
        """Get next task from queue (FIFO)"""
        if not self.redis:
            return None
        
        # Pop from left (FIFO)
        task_json = self.redis.lpop(self.queue_key)
        
        if not task_json:
            return None
        
        task = json.loads(task_json)
        
        # Move to active
        self.redis.sadd(self.active_key, task['task_id'])
        
        return task
    
    def complete_task(self, task_id: str, result: Dict):
        """Mark task as completed"""
        if not self.redis:
            return
        
        # Remove from active
        self.redis.srem(self.active_key, task_id)
        
        # Add to completed
        self.redis.sadd(self.completed_key, task_id)
        
        # Store result
        result_data = {
            'task_id': task_id,
            'result': result,
            'completed_at': self._timestamp()
        }
        
        self.redis.setex(
            f'lora:result:{task_id}',
            timedelta(days=30),  # Keep results for 30 days
            json.dumps(result_data)
        )
    
    def get_queue_status(self) -> Dict:
        """Get queue statistics"""
        if not self.redis:
            return {'queued': 0, 'active': 0, 'completed': 0}
        
        return {
            'queued': self.redis.llen(self.queue_key),
            'active': self.redis.scard(self.active_key),
            'completed': self.redis.scard(self.completed_key)
        }
    
    def _timestamp(self) -> float:
        """Current timestamp"""
        import time
        return time.time()


class TrainingCache:
    """Cache cho dataset metadata và AI recommendations"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
        self.ttl_short = timedelta(minutes=30)  # For temporary data
        self.ttl_long = timedelta(days=7)  # For metadata
    
    def cache_dataset_metadata(self, dataset_path: str, metadata: Dict):
        """Cache dataset metadata"""
        if not self.redis:
            return
        
        key = f'lora:metadata:{self._hash_path(dataset_path)}'
        self.redis.setex(key, self.ttl_long, json.dumps(metadata))
    
    def get_dataset_metadata(self, dataset_path: str) -> Optional[Dict]:
        """Get cached dataset metadata"""
        if not self.redis:
            return None
        
        key = f'lora:metadata:{self._hash_path(dataset_path)}'
        data = self.redis.get(key)
        
        return json.loads(data) if data else None
    
    def cache_ai_recommendation(self, dataset_path: str, goal: str, config: Dict):
        """Cache AI config recommendation"""
        if not self.redis:
            return
        
        key = f'lora:ai_config:{self._hash_path(dataset_path)}:{goal}'
        self.redis.setex(key, self.ttl_short, json.dumps(config))
    
    def get_ai_recommendation(self, dataset_path: str, goal: str) -> Optional[Dict]:
        """Get cached AI recommendation"""
        if not self.redis:
            return None
        
        key = f'lora:ai_config:{self._hash_path(dataset_path)}:{goal}'
        data = self.redis.get(key)
        
        return json.loads(data) if data else None
    
    def cache_training_progress(self, task_id: str, progress: Dict):
        """Cache training progress"""
        if not self.redis:
            return
        
        key = f'lora:progress:{task_id}'
        self.redis.setex(key, self.ttl_short, json.dumps(progress))
        
        # Also publish to channel for real-time updates
        self.redis.publish(f'lora:progress_update', json.dumps({
            'task_id': task_id,
            'progress': progress
        }))
    
    def get_training_progress(self, task_id: str) -> Optional[Dict]:
        """Get training progress"""
        if not self.redis:
            return None
        
        key = f'lora:progress:{task_id}'
        data = self.redis.get(key)
        
        return json.loads(data) if data else None
    
    def _hash_path(self, path: str) -> str:
        """Hash path for cache key"""
        import hashlib
        return hashlib.md5(path.encode()).hexdigest()


class SessionManager:
    """WebSocket session management"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
        self.session_ttl = timedelta(hours=1)
    
    def create_session(self, session_id: str, user_data: Dict):
        """Create user session"""
        if not self.redis:
            return
        
        key = f'lora:session:{session_id}'
        self.redis.setex(key, self.session_ttl, json.dumps(user_data))
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        if not self.redis:
            return None
        
        key = f'lora:session:{session_id}'
        data = self.redis.get(key)
        
        return json.loads(data) if data else None
    
    def update_session(self, session_id: str, user_data: Dict):
        """Update session"""
        self.create_session(session_id, user_data)  # Refresh TTL
    
    def delete_session(self, session_id: str):
        """Delete session"""
        if not self.redis:
            return
        
        key = f'lora:session:{session_id}'
        self.redis.delete(key)


class MetricsLogger:
    """Log training metrics to Redis for analytics"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
    
    def log_epoch(self, task_id: str, epoch: int, metrics: Dict):
        """Log epoch metrics"""
        if not self.redis:
            return
        
        # Store in sorted set (by epoch number)
        key = f'lora:metrics:{task_id}'
        
        self.redis.zadd(key, {
            json.dumps({
                'epoch': epoch,
                'metrics': metrics,
                'timestamp': self._timestamp()
            }): epoch
        })
        
        # Set expiry
        self.redis.expire(key, timedelta(days=30))
    
    def get_metrics(self, task_id: str) -> List[Dict]:
        """Get all metrics for a task"""
        if not self.redis:
            return []
        
        key = f'lora:metrics:{task_id}'
        
        # Get all from sorted set
        metrics_json = self.redis.zrange(key, 0, -1)
        
        return [json.loads(m) for m in metrics_json]
    
    def _timestamp(self) -> float:
        import time
        return time.time()


# Global instances
redis_manager = RedisManager()
task_queue = TrainingTaskQueue(redis_manager)
cache = TrainingCache(redis_manager)
session_manager = SessionManager(redis_manager)
metrics_logger = MetricsLogger(redis_manager)


# Helper functions
def is_redis_available() -> bool:
    """Check if Redis is available"""
    return redis_manager.is_available()

def queue_training(task_id: str, config: Dict) -> bool:
    """Queue a training task"""
    return task_queue.add_task(task_id, config)

def get_cached_metadata(dataset_path: str) -> Optional[Dict]:
    """Get cached dataset metadata"""
    return cache.get_dataset_metadata(dataset_path)

def cache_metadata(dataset_path: str, metadata: Dict):
    """Cache dataset metadata"""
    cache.cache_dataset_metadata(dataset_path, metadata)
