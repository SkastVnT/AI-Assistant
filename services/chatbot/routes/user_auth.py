"""
User Authentication Routes
Login, logout, register endpoints
"""
import sys
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, session, render_template, redirect
import logging

CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import logger
from core.feature_flags import features
from core.user_auth import (
    authenticate_user, create_user, init_admin_users,
    get_user_quota, check_image_quota, check_video_access,
    create_payment_request, IMAGE_GEN_LIMIT,
)

user_auth_bp = Blueprint('user_auth', __name__)

# Flag to track if admin users have been seeded
_admin_seeded = False


def _get_db():
    """Get MongoDB database instance."""
    try:
        from core.extensions import get_db
        return get_db()
    except Exception:
        try:
            from config.mongodb_config import mongodb_client
            return mongodb_client.db
        except Exception:
            return None


def _ensure_admin_seeded():
    """Seed admin users once."""
    global _admin_seeded
    if not _admin_seeded:
        db = _get_db()
        if db is not None:
            init_admin_users(db)
            _admin_seeded = True


@user_auth_bp.route('/login')
def login_page():
    """Render login page. If already authenticated, redirect to home."""
    _ensure_admin_seeded()
    if session.get('authenticated'):
        return redirect('/')
    return render_template('login.html')


@user_auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and create session."""
    _ensure_admin_seeded()
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin'}), 400

    db = _get_db()
    user = authenticate_user(db, username, password)

    if user:
        session.clear()
        session['authenticated'] = True
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['user_role'] = user['role']
        session['display_name'] = user['display_name']
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True

        logger.info(f"[Auth] Login success: {username} (role={user['role']})")
        redirect_url = '/admin' if user['role'] == 'admin' else '/'
        response = jsonify({'success': True, 'redirect': redirect_url, 'user': user})
        response.set_cookie('display_name', user['display_name'], max_age=86400 * 30, httponly=False, samesite='Lax')
        return response
    else:
        logger.warning(f"[Auth] Login failed: {username}")
        return jsonify({'success': False, 'message': 'Sai tên đăng nhập hoặc mật khẩu'}), 401


@user_auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"[Auth] Logout: {username}")
    response = redirect('/login')
    response.delete_cookie('display_name')
    return response


@user_auth_bp.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user info."""
    if not session.get('authenticated'):
        return jsonify({'authenticated': False}), 401
    return jsonify({
        'authenticated': True,
        'user': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role'),
            'display_name': session.get('display_name'),
        }
    })


@user_auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    display_name = data.get('display_name', '').strip()
    email = data.get('email', '').strip() or None

    if not username or not password:
        return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin'}), 400
    if len(username) < 3:
        return jsonify({'success': False, 'message': 'Tên đăng nhập phải có ít nhất 3 ký tự'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Mật khẩu phải có ít nhất 6 ký tự'}), 400
    # Only allow alphanumeric + underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'success': False, 'message': 'Tên đăng nhập chỉ được dùng chữ, số và dấu _'}), 400

    db = _get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Lỗi kết nối database'}), 500

    user = create_user(db, username, password, role='user',
                       display_name=display_name or username, email=email)
    if user is None:
        return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại'}), 409

    logger.info(f"[Auth] New user registered: {username}")
    return jsonify({'success': True, 'message': 'Tạo tài khoản thành công! Vui lòng đăng nhập.'})


@user_auth_bp.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """Change password for the currently logged-in user."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401

    data = request.json or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not current_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin'}), 400
    if len(new_pw) < 6:
        return jsonify({'success': False, 'message': 'Mật khẩu mới phải có ít nhất 6 ký tự'}), 400

    db = _get_db()
    username = session.get('username')
    user = authenticate_user(db, username, current_pw)
    if not user:
        return jsonify({'success': False, 'message': 'Mật khẩu hiện tại không đúng'}), 401

    from core.user_auth import change_password as do_change
    ok = do_change(db, username, new_pw)
    if ok:
        logger.info(f"[Auth] Password changed: {username}")
        return jsonify({'success': True, 'message': 'Đổi mật khẩu thành công'})
    return jsonify({'success': False, 'message': 'Đổi mật khẩu thất bại'}), 500


# ─── Public feature flags ─────────────────────────────────────────────────────

@user_auth_bp.route('/api/features', methods=['GET'])
def get_features():
    """Return public feature flag states for frontend UI decisions."""
    features.reload()   # pick up any file changes
    return jsonify({
        'quota':   features.quota_enabled,
        'video':   features.video_enabled,
        'video_requires_payment': features.video_requires_payment,
        'payment': features.payment_enabled,
        'qr':      features.qr_enabled,
        'registration': features.allow_registration,
    })


# ─── Quota & Payment ─────────────────────────────────────────────────────────

@user_auth_bp.route('/api/auth/quota', methods=['GET'])
def get_quota():
    """Get current user's quota status."""
    if not session.get('authenticated'):
        return jsonify({'authenticated': False}), 401
    db = _get_db()
    username = session.get('username', '')
    quota = get_user_quota(db, username)
    quota['image_quota_limit'] = quota.get('image_quota_limit') or IMAGE_GEN_LIMIT
    return jsonify({'success': True, 'quota': quota})


@user_auth_bp.route('/api/auth/request-video-unlock', methods=['POST'])
def request_video_unlock():
    """Submit a video unlock payment request."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
    username = session.get('username', '')
    db = _get_db()
    if db is None:
        return jsonify({'success': False, 'message': 'Lỗi DB'}), 500
    # Check if already unlocked
    allowed, _ = check_video_access(db, username)
    if allowed:
        return jsonify({'success': True, 'message': 'Video đã được mở khóa cho tài khoản của bạn.'})
    data = request.json or {}
    req = create_payment_request(db, username, note=data.get('note', ''))
    logger.info(f"[Auth] Video unlock requested: {username}")
    return jsonify({
        'success': True,
        'message': 'Yêu cầu đã gửi! Admin sẽ xét duyệt sau khi xác nhận thanh toán.',
        'request_id': req.get('_id', ''),
    })

