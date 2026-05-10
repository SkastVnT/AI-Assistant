"""
Flask Extensions Initialization

Centralized extension management for:
- Database connections (MongoDB)
- Cache (Redis)
- Rate limiting
- Other Flask extensions
"""

import logging
import os
from flask import Flask
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Extension instances (initialized lazily)
_mongodb_client = None
_redis_client = None
_cache_manager = None
_mongodb_db_name = os.getenv('MONGODB_DB_NAME', 'chatbot_db')


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions"""
    init_mongodb(app)
    init_redis(app)
    init_cache(app)
    logger.info("All extensions initialized")


def init_mongodb(app: Flask) -> None:
    """Initialize MongoDB connection"""
    global _mongodb_client, _mongodb_db_name

    if not app.config.get('MONGODB_ENABLED', False):
        logger.info("MongoDB disabled by configuration")
        return

    try:
        from pymongo import MongoClient

        uri = app.config.get('MONGODB_URI')
        x509_enabled = str(app.config.get('MONGODB_X509_ENABLED', False)).lower() == 'true'
        x509_uri = str(app.config.get('MONGODB_X509_URI', '') or '').strip()
        x509_cert_path = str(app.config.get('MONGODB_X509_CERT_PATH', '') or '').strip()
        tls_allow_invalid = str(app.config.get('MONGODB_TLS_ALLOW_INVALID_CERTIFICATES', True)).lower() == 'true'

        if x509_enabled and x509_uri:
            uri = x509_uri

        # Only force TLS for non-SRV URIs (Atlas+srv handles TLS automatically)
        connect_kwargs = dict(serverSelectionTimeoutMS=5000)
        if uri and not uri.startswith('mongodb+srv://'):
            parsed_host = (uri.split('@')[-1].split('/')[0].split(':')[0]
                           if '@' in uri
                           else uri.replace('mongodb://', '').split('/')[0].split(':')[0])
            if parsed_host not in ('localhost', '127.0.0.1', '::1'):
                connect_kwargs['tls'] = True
                connect_kwargs['tlsAllowInvalidCertificates'] = tls_allow_invalid

        if x509_enabled and x509_cert_path:
            cert_path = Path(x509_cert_path)
            if cert_path.exists():
                connect_kwargs['tls'] = True
                connect_kwargs['tlsAllowInvalidCertificates'] = tls_allow_invalid
                connect_kwargs['tlsCertificateKeyFile'] = str(cert_path)
                connect_kwargs['authMechanism'] = 'MONGODB-X509'
                connect_kwargs['authSource'] = '$external'
            else:
                logger.warning(f"MongoDB X.509 cert not found: {cert_path}")

        _mongodb_client = MongoClient(uri, **connect_kwargs)
        _mongodb_client.admin.command('ping')

        app.extensions['mongodb'] = _mongodb_client
        db_name = app.config.get('MONGODB_DB_NAME', _mongodb_db_name)
        logger.info(f"MongoDB connected -> database: {db_name}")
        _mongodb_db_name = db_name

    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")
        _mongodb_client = None
        app.config['MONGODB_ENABLED'] = False


def init_redis(app: Flask) -> None:
    """Initialize Redis connection"""
    global _redis_client

    if not app.config.get('CACHE_ENABLED', False):
        logger.info("Redis cache disabled by configuration")
        return

    try:
        import redis

        url = app.config.get('REDIS_URL')
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()

        app.extensions['redis'] = _redis_client
        logger.info("Redis connected successfully")

    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        app.config['CACHE_ENABLED'] = False


def init_cache(app: Flask) -> None:
    """Initialize cache manager"""
    global _cache_manager

    if not app.config.get('CACHE_ENABLED', False):
        return

    try:
        from .services.cache_service import CacheService
        _cache_manager = CacheService(app)
        app.extensions['cache'] = _cache_manager
        logger.info("Cache manager initialized")
    except ImportError:
        logger.info("Cache service not available")


def get_mongodb():
    """Get MongoDB client instance"""
    return _mongodb_client


def get_db(db_name: str = None):
    """Return the configured MongoDB database, or None if not connected."""
    if _mongodb_client is None:
        return None
    name = db_name or _mongodb_db_name
    return _mongodb_client.get_database(name)


def get_redis():
    """Get Redis client instance"""
    return _redis_client


def get_cache():
    """Get cache manager instance"""
    return _cache_manager
