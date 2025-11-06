"""
Monitoring and Metrics Module for RAG Services
Tracks performance, errors, and system health
"""
import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates application metrics
    Thread-safe implementation
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.lock = Lock()
        
        # Counters
        self.counters = defaultdict(int)
        
        # Timers (store recent measurements)
        self.timers = defaultdict(lambda: deque(maxlen=history_size))
        
        # Gauges (current values)
        self.gauges = {}
        
        # Error tracking
        self.errors = defaultdict(list)
        
        # Start time for uptime calculation
        self.start_time = time.time()
    
    def increment(self, metric: str, value: int = 1):
        """Increment a counter"""
        with self.lock:
            self.counters[metric] += value
    
    def record_time(self, metric: str, duration: float):
        """Record a timing measurement"""
        with self.lock:
            self.timers[metric].append(duration)
    
    def set_gauge(self, metric: str, value: float):
        """Set a gauge value"""
        with self.lock:
            self.gauges[metric] = value
    
    def record_error(self, error_type: str, error_message: str):
        """Record an error"""
        with self.lock:
            self.errors[error_type].append({
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            })
            # Keep only recent errors (last 100 per type)
            if len(self.errors[error_type]) > 100:
                self.errors[error_type] = self.errors[error_type][-100:]
    
    def get_counter(self, metric: str) -> int:
        """Get counter value"""
        with self.lock:
            return self.counters.get(metric, 0)
    
    def get_timer_stats(self, metric: str) -> Dict[str, float]:
        """Get statistics for a timer"""
        with self.lock:
            measurements = list(self.timers.get(metric, []))
        
        if not measurements:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }
        
        sorted_measurements = sorted(measurements)
        count = len(sorted_measurements)
        
        return {
            'count': count,
            'min': round(min(sorted_measurements), 3),
            'max': round(max(sorted_measurements), 3),
            'avg': round(sum(sorted_measurements) / count, 3),
            'p50': round(sorted_measurements[int(count * 0.5)], 3),
            'p95': round(sorted_measurements[int(count * 0.95)], 3),
            'p99': round(sorted_measurements[int(count * 0.99)], 3)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self.lock:
            return {
                'counters': dict(self.counters),
                'timers': {
                    metric: self.get_timer_stats(metric)
                    for metric in self.timers.keys()
                },
                'gauges': dict(self.gauges),
                'errors': {
                    error_type: len(errors)
                    for error_type, errors in self.errors.items()
                },
                'uptime_seconds': int(time.time() - self.start_time)
            }
    
    def get_recent_errors(self, error_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent errors"""
        with self.lock:
            if error_type:
                return self.errors.get(error_type, [])[-limit:]
            else:
                # Get errors from all types
                all_errors = []
                for err_type, err_list in self.errors.items():
                    for err in err_list[-limit:]:
                        all_errors.append({
                            'type': err_type,
                            **err
                        })
                # Sort by timestamp
                all_errors.sort(key=lambda x: x['timestamp'], reverse=True)
                return all_errors[:limit]
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.counters.clear()
            self.timers.clear()
            self.gauges.clear()
            self.errors.clear()
            self.start_time = time.time()
        logger.info("All metrics reset")


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


class SystemMonitor:
    """Monitor system resources (CPU, memory, disk)"""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """Get memory usage information"""
        mem = psutil.virtual_memory()
        return {
            'total_mb': round(mem.total / (1024 ** 2), 2),
            'available_mb': round(mem.available / (1024 ** 2), 2),
            'used_mb': round(mem.used / (1024 ** 2), 2),
            'percent': mem.percent
        }
    
    @staticmethod
    def get_disk_usage(path: str = "/") -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage(path)
            return {
                'total_gb': round(disk.total / (1024 ** 3), 2),
                'used_gb': round(disk.used / (1024 ** 3), 2),
                'free_gb': round(disk.free / (1024 ** 3), 2),
                'percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {}
    
    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """Get current process information"""
        try:
            process = psutil.Process()
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_mb': round(process.memory_info().rss / (1024 ** 2), 2),
                'threads': process.num_threads(),
                'status': process.status()
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {}
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Any]:
        """Get all system statistics"""
        return {
            'cpu_percent': cls.get_cpu_usage(),
            'memory': cls.get_memory_usage(),
            'disk': cls.get_disk_usage(),
            'process': cls.get_process_info(),
            'timestamp': datetime.now().isoformat()
        }


def track_time(metric_name: str):
    """
    Decorator to track execution time
    
    Usage:
        @track_time('search_query')
        def search(query):
            return results
    """
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = get_metrics_collector()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record successful execution
                metrics.record_time(metric_name, duration)
                metrics.increment(f'{metric_name}.success')
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record failed execution
                metrics.record_time(f'{metric_name}.error', duration)
                metrics.increment(f'{metric_name}.error')
                metrics.record_error(metric_name, str(e))
                
                raise
        
        return wrapper
    return decorator


def get_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status
    Returns system health, metrics, and service status
    """
    metrics = get_metrics_collector()
    system = SystemMonitor()
    
    # Get metrics
    all_metrics = metrics.get_all_metrics()
    system_stats = system.get_all_stats()
    
    # Calculate health score (0-100)
    health_score = 100
    health_issues = []
    
    # Check CPU usage
    if system_stats['cpu_percent'] > 90:
        health_score -= 20
        health_issues.append("High CPU usage")
    
    # Check memory usage
    if system_stats['memory']['percent'] > 90:
        health_score -= 20
        health_issues.append("High memory usage")
    
    # Check disk usage
    if system_stats['disk'].get('percent', 0) > 90:
        health_score -= 10
        health_issues.append("Low disk space")
    
    # Check error rate
    total_requests = all_metrics['counters'].get('requests', 0)
    total_errors = sum(all_metrics['errors'].values())
    if total_requests > 0:
        error_rate = (total_errors / total_requests) * 100
        if error_rate > 5:
            health_score -= 30
            health_issues.append(f"High error rate: {error_rate:.1f}%")
    
    # Determine overall status
    if health_score >= 80:
        status = "healthy"
    elif health_score >= 50:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return {
        'status': status,
        'health_score': max(0, health_score),
        'issues': health_issues,
        'uptime_seconds': all_metrics['uptime_seconds'],
        'uptime_human': str(timedelta(seconds=all_metrics['uptime_seconds'])),
        'metrics': all_metrics,
        'system': system_stats,
        'timestamp': datetime.now().isoformat()
    }


# Convenience functions
def increment_counter(metric: str, value: int = 1):
    """Increment a counter (convenience function)"""
    get_metrics_collector().increment(metric, value)


def record_timing(metric: str, duration: float):
    """Record a timing (convenience function)"""
    get_metrics_collector().record_time(metric, duration)


def record_error(error_type: str, message: str):
    """Record an error (convenience function)"""
    get_metrics_collector().record_error(error_type, message)
