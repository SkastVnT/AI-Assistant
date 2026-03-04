"""
Enhanced Error Handler — Centralized error handling with user-friendly messages,
automatic model fallback suggestions, and error analytics.
"""
import logging
import traceback
from datetime import datetime
from functools import wraps
from flask import jsonify, request

logger = logging.getLogger(__name__)

# ============================================================
# ERROR CODES & MESSAGES
# ============================================================

ERROR_MESSAGES = {
    # API Key issues
    'no_api_key': {
        'vi': '❌ API key chưa được cấu hình cho model {model}. Vui lòng kiểm tra file .env',
        'en': '❌ API key not configured for model {model}. Please check your .env file',
    },
    # Rate limiting
    'rate_limited': {
        'vi': '⏳ Đã vượt giới hạn request. Vui lòng đợi {wait}s hoặc chuyển sang model khác.',
        'en': '⏳ Rate limited. Please wait {wait}s or switch to another model.',
    },
    # Network errors
    'connection_error': {
        'vi': '🌐 Không thể kết nối đến {provider}. Kiểm tra mạng hoặc thử model khác.',
        'en': '🌐 Cannot connect to {provider}. Check network or try another model.',
    },
    # Timeout
    'timeout': {
        'vi': '⏱️ Request timeout ({timeout}s). Thử lại với tin nhắn ngắn hơn hoặc model nhanh hơn.',
        'en': '⏱️ Request timeout ({timeout}s). Try a shorter message or faster model.',
    },
    # Model unavailable
    'model_unavailable': {
        'vi': '❌ Model {model} hiện không khả dụng. Gợi ý: {fallbacks}',
        'en': '❌ Model {model} is currently unavailable. Suggestions: {fallbacks}',
    },
    # Balance issues
    'insufficient_balance': {
        'vi': '💰 Hết balance cho {model}. Sử dụng model FREE: Gemini, Step-3.5 Flash, BloomVN',
        'en': '💰 Insufficient balance for {model}. Use FREE models: Gemini, Step-3.5 Flash, BloomVN',
    },
    # Generic
    'unknown': {
        'vi': '❌ Lỗi không xác định: {error}',
        'en': '❌ Unknown error: {error}',
    },
}

# Fallback suggestions per model
MODEL_FALLBACKS = {
    'grok': ['deepseek', 'step-flash', 'gemini'],
    'openai': ['deepseek', 'step-flash', 'gemini'],
    'deepseek': ['step-flash', 'gemini', 'openai'],
    'gemini': ['step-flash', 'grok', 'deepseek'],
    'step-flash': ['gemini', 'deepseek', 'grok'],
    'stepfun': ['step-flash', 'deepseek', 'gemini'],
    'qwen': ['deepseek', 'step-flash', 'gemini'],
    'bloomvn': ['step-flash', 'gemini', 'qwen'],
}

# Error statistics
_error_stats = {
    'total': 0,
    'by_model': {},
    'by_type': {},
    'recent': [],
}


def classify_error(error: Exception) -> str:
    """Classify an error into a known category"""
    error_str = str(error).lower()
    
    if 'rate' in error_str and 'limit' in error_str:
        return 'rate_limited'
    elif 'timeout' in error_str or 'timed out' in error_str:
        return 'timeout'
    elif 'connection' in error_str or 'connect' in error_str:
        return 'connection_error'
    elif 'api key' in error_str or 'authentication' in error_str or 'unauthorized' in error_str:
        return 'no_api_key'
    elif 'balance' in error_str or 'insufficient' in error_str or 'quota' in error_str:
        return 'insufficient_balance'
    elif 'not found' in error_str or 'unavailable' in error_str:
        return 'model_unavailable'
    else:
        return 'unknown'


def get_user_friendly_error(error: Exception, model: str = 'unknown', language: str = 'vi') -> str:
    """Get a user-friendly error message with fallback suggestions"""
    error_type = classify_error(error)
    
    messages = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['unknown'])
    msg_template = messages.get(language, messages.get('vi', '❌ Error: {error}'))
    
    # Get fallback suggestions
    fallbacks = MODEL_FALLBACKS.get(model, ['gemini', 'step-flash', 'deepseek'])
    fallback_str = ', '.join(fallbacks[:3])
    
    # Format the message
    try:
        msg = msg_template.format(
            model=model,
            provider=model,
            error=str(error)[:200],
            wait=30,
            timeout=60,
            fallbacks=fallback_str,
        )
    except (KeyError, IndexError):
        msg = f"❌ Error with {model}: {str(error)[:200]}"
    
    # Track stats
    _track_error(model, error_type, str(error))
    
    return msg


def _track_error(model: str, error_type: str, error_msg: str):
    """Track error statistics"""
    _error_stats['total'] += 1
    
    if model not in _error_stats['by_model']:
        _error_stats['by_model'][model] = 0
    _error_stats['by_model'][model] += 1
    
    if error_type not in _error_stats['by_type']:
        _error_stats['by_type'][error_type] = 0
    _error_stats['by_type'][error_type] += 1
    
    _error_stats['recent'].append({
        'model': model,
        'type': error_type,
        'message': error_msg[:100],
        'timestamp': datetime.now().isoformat(),
    })
    
    # Keep only last 50
    if len(_error_stats['recent']) > 50:
        _error_stats['recent'] = _error_stats['recent'][-50:]


def get_error_stats() -> dict:
    """Get error statistics"""
    return {
        **_error_stats,
        'most_failing_model': max(_error_stats['by_model'].items(), key=lambda x: x[1])[0] if _error_stats['by_model'] else None,
        'most_common_error': max(_error_stats['by_type'].items(), key=lambda x: x[1])[0] if _error_stats['by_type'] else None,
    }


def api_error_handler(f):
    """Decorator for Flask API routes — catches errors and returns user-friendly JSON"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"[API Error] {request.path}: {e}")
            logger.debug(traceback.format_exc())
            
            model = 'unknown'
            language = 'vi'
            
            # Try to extract model and language from request
            try:
                data = request.json or {}
                model = data.get('model', 'unknown')
                language = data.get('language', 'vi')
            except Exception:
                pass
            
            error_msg = get_user_friendly_error(e, model, language)
            
            return jsonify({
                'error': error_msg,
                'error_type': classify_error(e),
                'model': model,
                'fallbacks': MODEL_FALLBACKS.get(model, ['gemini', 'step-flash']),
                'timestamp': datetime.now().isoformat(),
            }), 500
    
    return wrapper
