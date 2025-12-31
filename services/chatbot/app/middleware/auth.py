"""
Authentication Middleware

Handles session and API key authentication.
"""

import os
from functools import wraps
from flask import session, request, jsonify


def require_session(f):
    """Decorator to require a valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Create anonymous session
            import uuid
            session['user_id'] = f"anonymous_{str(uuid.uuid4())[:8]}"
        return f(*args, **kwargs)
    return decorated_function


def require_api_key(f):
    """Decorator to require a valid API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'API key required'
            }), 401
        
        # Validate API key (simple validation for now)
        valid_key = os.getenv('API_KEY')
        
        if valid_key and api_key != valid_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid API key'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function
