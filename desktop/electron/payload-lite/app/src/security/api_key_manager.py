"""
API Key Manager
Secure API key handling with rotation support
"""

import os
import secrets
import hashlib
import logging
import time
from typing import Optional, Dict, Set
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Secure API key management with support for:
    - Key hashing (never store plain keys)
    - Key rotation
    - Usage tracking
    - Expiration
    """
    
    def __init__(self, key_prefix: str = "ak_"):
        self.key_prefix = key_prefix
        self._keys: Dict[str, dict] = {}  # hash -> metadata
        self._revoked: Set[str] = set()
        self._lock = Lock()
    
    def generate_key(self, name: str, expires_in: int = None) -> str:
        """
        Generate a new API key.
        
        Args:
            name: Key name/description
            expires_in: Expiration in seconds (None = no expiration)
        
        Returns:
            Plain text API key (only returned once!)
        """
        # Generate secure random key
        key = f"{self.key_prefix}{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(key)
        
        with self._lock:
            self._keys[key_hash] = {
                'name': name,
                'created_at': time.time(),
                'expires_at': time.time() + expires_in if expires_in else None,
                'last_used': None,
                'use_count': 0
            }
        
        logger.info(f"API key generated: {name}")
        return key
    
    def validate_key(self, key: str) -> Optional[dict]:
        """
        Validate an API key.
        
        Args:
            key: Plain text API key
        
        Returns:
            Key metadata if valid, None if invalid
        """
        if not key or not key.startswith(self.key_prefix):
            return None
        
        key_hash = self._hash_key(key)
        
        with self._lock:
            # Check if revoked
            if key_hash in self._revoked:
                logger.warning(f"Revoked key used")
                return None
            
            # Check if exists
            if key_hash not in self._keys:
                return None
            
            metadata = self._keys[key_hash]
            
            # Check expiration
            if metadata['expires_at'] and time.time() > metadata['expires_at']:
                logger.warning(f"Expired key used: {metadata['name']}")
                return None
            
            # Update usage
            metadata['last_used'] = time.time()
            metadata['use_count'] += 1
            
            return metadata
    
    def revoke_key(self, key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key: Plain text API key
        
        Returns:
            True if revoked, False if key not found
        """
        key_hash = self._hash_key(key)
        
        with self._lock:
            if key_hash in self._keys:
                self._revoked.add(key_hash)
                name = self._keys[key_hash].get('name', 'unknown')
                del self._keys[key_hash]
                logger.info(f"API key revoked: {name}")
                return True
        
        return False
    
    def rotate_key(self, old_key: str) -> Optional[str]:
        """
        Rotate an API key (revoke old, generate new with same metadata).
        
        Args:
            old_key: Current API key
        
        Returns:
            New API key if successful, None if old key invalid
        """
        metadata = self.validate_key(old_key)
        if not metadata:
            return None
        
        # Generate new key with same name
        new_key = self.generate_key(
            name=metadata['name'],
            expires_in=None  # New key, new expiration
        )
        
        # Revoke old key
        self.revoke_key(old_key)
        
        logger.info(f"API key rotated: {metadata['name']}")
        return new_key
    
    def get_stats(self) -> Dict:
        """Get key statistics."""
        with self._lock:
            return {
                'active_keys': len(self._keys),
                'revoked_keys': len(self._revoked),
                'keys': [
                    {
                        'name': m['name'],
                        'created_at': m['created_at'],
                        'last_used': m['last_used'],
                        'use_count': m['use_count'],
                        'expires_at': m['expires_at']
                    }
                    for m in self._keys.values()
                ]
            }
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()


def api_key_required(manager: APIKeyManager = None, 
                     header_name: str = "X-API-Key"):
    """
    Decorator to require API key authentication.
    
    Args:
        manager: APIKeyManager instance
        header_name: Header name for API key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            # Get API key from header or query param
            api_key = request.headers.get(header_name)
            if not api_key:
                api_key = request.args.get('api_key')
            
            if not api_key:
                return jsonify({
                    'error': 'API key required',
                    'message': f'Provide key in {header_name} header or api_key parameter'
                }), 401
            
            # Validate key
            if manager:
                key_info = manager.validate_key(api_key)
                if not key_info:
                    return jsonify({
                        'error': 'Invalid or expired API key'
                    }), 403
                
                # Add key info to request context
                request.api_key_info = key_info
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Environment-based key validation
def validate_env_api_key(key_name: str) -> bool:
    """
    Validate API key from environment.
    
    Args:
        key_name: Environment variable name
    
    Returns:
        True if key is set and not empty
    """
    key = os.getenv(key_name)
    if not key:
        logger.warning(f"API key not configured: {key_name}")
        return False
    
    if len(key) < 10:
        logger.warning(f"API key too short: {key_name}")
        return False
    
    return True


def mask_api_key(key: str, visible_chars: int = 4) -> str:
    """
    Mask API key for safe logging.
    
    Args:
        key: API key to mask
        visible_chars: Number of visible characters at start/end
    
    Returns:
        Masked key like "ak_xxxx...xxxx"
    """
    if not key or len(key) <= visible_chars * 2:
        return "***"
    
    return f"{key[:visible_chars]}...{key[-visible_chars:]}"
