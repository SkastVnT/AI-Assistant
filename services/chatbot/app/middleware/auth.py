"""
Authentication Middleware

Handles session, login, admin, and API key authentication.
"""

import os
from functools import wraps
from flask import session, request, jsonify, redirect, url_for


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


def require_login(f):
    """Decorator to require authenticated user. Redirects to /login if not logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            # API requests get 401, browser requests get redirect
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'message': 'Login required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'message': 'Login required'}), 401
            return redirect('/login')
        if session.get('user_role') != 'admin':
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Forbidden', 'message': 'Admin access required'}), 403
            return redirect('/')
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
