"""
Health check endpoints for database and service monitoring.

Add these routes to your Flask/FastAPI application:

For Flask:
    from database.utils.health import register_health_routes
    register_health_routes(app)

For FastAPI:
    from database.utils.health import health_router
    app.include_router(health_router)
"""

import logging
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, jsonify
from fastapi import APIRouter, status

from database.utils.engine import DatabaseEngine
from database.utils.performance import check_database_health, get_pool_stats
from database.utils.cache import get_cache

logger = logging.getLogger(__name__)


# ============================================================
# FLASK BLUEPRINT
# ============================================================

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/', methods=['GET'])
def health_check():
    """
    Basic health check endpoint
    
    Returns HTTP 200 if service is running
    """
    return jsonify({
        'status': 'healthy',
        'service': 'ai-assistant',
        'timestamp': datetime.now().isoformat()
    })


@health_bp.route('/database', methods=['GET'])
def database_health():
    """
    Database health check endpoint
    
    Returns:
        200: Database is healthy
        503: Database is unhealthy
    """
    try:
        engine = DatabaseEngine.get_engine()
        health = check_database_health(engine)
        
        if health['status'] == 'healthy':
            return jsonify(health), 200
        else:
            return jsonify(health), 503
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@health_bp.route('/cache', methods=['GET'])
def cache_health():
    """
    Redis cache health check endpoint
    
    Returns:
        200: Cache is healthy
        503: Cache is unhealthy or unavailable
    """
    try:
        cache = get_cache()
        
        if cache is None:
            return jsonify({
                'status': 'disabled',
                'message': 'Cache not initialized',
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Test cache connection
        cache.client.ping()
        
        # Get cache info
        info = cache.client.info('stats')
        
        return jsonify({
            'status': 'healthy',
            'redis': {
                'total_connections_received': info.get('total_connections_received'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@health_bp.route('/detailed', methods=['GET'])
def detailed_health():
    """
    Comprehensive health check with all subsystems
    
    Returns detailed status of database, cache, and connection pools
    """
    result = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check database
    try:
        engine = DatabaseEngine.get_engine()
        db_health = check_database_health(engine)
        result['components']['database'] = db_health
        
        if db_health['status'] != 'healthy':
            result['status'] = 'degraded'
    
    except Exception as e:
        result['components']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        result['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache = get_cache()
        if cache:
            cache.client.ping()
            result['components']['cache'] = {
                'status': 'healthy',
                'enabled': True
            }
        else:
            result['components']['cache'] = {
                'status': 'disabled',
                'enabled': False
            }
    
    except Exception as e:
        result['components']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        result['status'] = 'degraded'
    
    # Determine HTTP status code
    if result['status'] == 'healthy':
        status_code = 200
    elif result['status'] == 'degraded':
        status_code = 200  # Still operational
    else:
        status_code = 503
    
    return jsonify(result), status_code


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Kubernetes readiness probe endpoint
    
    Returns 200 if service is ready to accept traffic
    """
    try:
        engine = DatabaseEngine.get_engine()
        
        # Quick database ping
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return jsonify({
            'ready': True,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            'ready': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    Kubernetes liveness probe endpoint
    
    Returns 200 if service process is alive
    """
    return jsonify({
        'alive': True,
        'timestamp': datetime.now().isoformat()
    }), 200


def register_health_routes(app):
    """
    Register health check routes with Flask app
    
    Args:
        app: Flask application instance
    
    Usage:
        from database.utils.health import register_health_routes
        register_health_routes(app)
    """
    app.register_blueprint(health_bp)
    logger.info("✅ Health check routes registered")


# ============================================================
# FASTAPI ROUTER
# ============================================================

health_router = APIRouter(prefix='/health', tags=['health'])


@health_router.get('/')
async def health_check_fastapi():
    """Basic health check"""
    return {
        'status': 'healthy',
        'service': 'ai-assistant',
        'timestamp': datetime.now().isoformat()
    }


@health_router.get('/database')
async def database_health_fastapi():
    """Database health check"""
    try:
        engine = DatabaseEngine.get_engine()
        health = check_database_health(engine)
        
        if health['status'] == 'healthy':
            return health
        else:
            return health
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@health_router.get('/cache')
async def cache_health_fastapi():
    """Cache health check"""
    try:
        cache = get_cache()
        
        if cache is None:
            return {
                'status': 'disabled',
                'message': 'Cache not initialized',
                'timestamp': datetime.now().isoformat()
            }
        
        cache.client.ping()
        info = cache.client.info('stats')
        
        return {
            'status': 'healthy',
            'redis': {
                'total_connections_received': info.get('total_connections_received'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            },
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@health_router.get('/ready')
async def readiness_check_fastapi():
    """Readiness probe"""
    try:
        engine = DatabaseEngine.get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return {
            'ready': True,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            'ready': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@health_router.get('/live')
async def liveness_check_fastapi():
    """Liveness probe"""
    return {
        'alive': True,
        'timestamp': datetime.now().isoformat()
    }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def calculate_hit_rate(hits: int, misses: int) -> float:
    """Calculate cache hit rate percentage"""
    total = hits + misses
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    'health_bp',
    'health_router',
    'register_health_routes',
    'health_check',
    'database_health',
    'cache_health',
    'detailed_health',
    'readiness_check',
    'liveness_check'
]
