"""
Admin Panel Routes
Dashboard, user management, session browser, image gallery, memory, logs
"""
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, session, render_template, redirect
import logging

CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import logger
from core.user_auth import (
    list_users, create_user, toggle_user_active, change_password,
    list_payment_requests, approve_payment_request, reject_payment_request,
    reset_image_quota, set_image_quota_limit, IMAGE_GEN_LIMIT,
)
from app.middleware.auth import require_admin

admin_bp = Blueprint('admin', __name__)


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


# ── Admin Page ──────────────────────────────────────────────────────────────

@admin_bp.route('/admin')
@require_admin
def admin_page():
    """Render admin dashboard."""
    return render_template('admin.html')


# ── Stats ───────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/stats')
@require_admin
def get_stats():
    """Get dashboard statistics."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        stats = {
            'users': db.users.count_documents({}),
            'conversations': db.conversations.count_documents({}),
            'messages': db.messages.count_documents({}),
            'images': _count_images(db),
            'memories': db.chatbot_memory.count_documents({}),
        }

        # Recent conversations
        recent = list(db.conversations.find(
            {}, {'title': 1, 'user_id': 1, 'model': 1, 'created_at': 1, 'updated_at': 1}
        ).sort('updated_at', -1).limit(10))
        for c in recent:
            c['_id'] = str(c['_id'])

        stats['recent_conversations'] = recent
        return jsonify(stats)
    except Exception as e:
        logger.error(f"[Admin] Stats error: {e}")
        return jsonify({'error': str(e)}), 500


def _count_images(db):
    """Count images across messages and uploaded_files."""
    try:
        # Count from messages with images
        pipeline = [
            {'$match': {'images': {'$exists': True, '$ne': []}}},
            {'$project': {'count': {'$size': '$images'}}},
            {'$group': {'_id': None, 'total': {'$sum': '$count'}}}
        ]
        result = list(db.messages.aggregate(pipeline))
        msg_count = result[0]['total'] if result else 0

        # Count from uploaded_files
        file_count = db.uploaded_files.count_documents({
            'mime_type': {'$regex': '^image/', '$options': 'i'}
        }) if 'uploaded_files' in db.list_collection_names() else 0

        return msg_count + file_count
    except Exception:
        return 0


# ── Users ───────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/users', methods=['GET'])
@require_admin
def get_users():
    """List all users."""
    db = _get_db()
    users = list_users(db)
    return jsonify({'users': users})


@admin_bp.route('/api/admin/users', methods=['POST'])
@require_admin
def create_new_user():
    """Create a new user."""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')
    display_name = data.get('display_name', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username và password là bắt buộc'}), 400
    if len(username) < 3:
        return jsonify({'success': False, 'message': 'Username phải >= 3 ký tự'}), 400
    if len(password) < 4:
        return jsonify({'success': False, 'message': 'Password phải >= 4 ký tự'}), 400

    db = _get_db()
    result = create_user(db, username, password, role, display_name or username)
    if result:
        logger.info(f"[Admin] Created user: {username} (role={role})")
        return jsonify({'success': True, 'user': result})
    else:
        return jsonify({'success': False, 'message': 'Username đã tồn tại'}), 409


@admin_bp.route('/api/admin/users/<username>/toggle', methods=['POST'])
@require_admin
def toggle_user(username):
    """Enable or disable a user."""
    data = request.json or {}
    active = data.get('active', True)
    db = _get_db()
    success = toggle_user_active(db, username, active)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Không thể thay đổi trạng thái admin'}), 400


@admin_bp.route('/api/admin/users/<username>/password', methods=['POST'])
@require_admin
def reset_password(username):
    """Reset a user's password."""
    data = request.json or {}
    new_password = data.get('password', '')
    if len(new_password) < 4:
        return jsonify({'success': False, 'message': 'Password phải >= 4 ký tự'}), 400
    db = _get_db()
    success = change_password(db, username, new_password)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'User không tồn tại'}), 404


# ── Sessions (Conversations) ───────────────────────────────────────────────

@admin_bp.route('/api/admin/sessions', methods=['GET'])
@require_admin
def get_sessions():
    """List all conversations with pagination and filters."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '').strip()
        user_id = request.args.get('user_id', '').strip()
        model = request.args.get('model', '').strip()

        query = {}
        if user_id:
            query['user_id'] = user_id
        if model:
            query['model'] = {'$regex': model, '$options': 'i'}
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'user_id': {'$regex': search, '$options': 'i'}},
            ]

        total = db.conversations.count_documents(query)
        conversations = list(db.conversations.find(query)
                             .sort('updated_at', -1)
                             .skip((page - 1) * per_page)
                             .limit(per_page))

        for c in conversations:
            c['_id'] = str(c['_id'])

        return jsonify({'conversations': conversations, 'total': total, 'page': page})
    except Exception as e:
        logger.error(f"[Admin] Sessions error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/sessions/<conversation_id>', methods=['GET'])
@require_admin
def get_session_detail(conversation_id):
    """Get a conversation with all its messages."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        from bson import ObjectId

        # Try both string ID and ObjectId
        conv = db.conversations.find_one({'_id': conversation_id})
        if not conv:
            try:
                conv = db.conversations.find_one({'_id': ObjectId(conversation_id)})
            except Exception:
                pass
        if not conv:
            return jsonify({'error': 'Session not found'}), 404

        conv['_id'] = str(conv['_id'])

        # Get messages
        conv_id_str = str(conv['_id'])
        messages = list(db.messages.find({
            '$or': [
                {'conversation_id': conv_id_str},
                {'conversation_id': conversation_id},
            ]
        }).sort('created_at', 1))

        for m in messages:
            m['_id'] = str(m['_id'])
            m['conversation_id'] = str(m.get('conversation_id', ''))

        conv['messages'] = messages
        return jsonify(conv)
    except Exception as e:
        logger.error(f"[Admin] Session detail error: {e}")
        return jsonify({'error': str(e)}), 500


# ── Images ──────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/images', methods=['GET'])
@require_admin
def get_images():
    """Get all images from messages and uploaded_files."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 24))
        user_id = request.args.get('user_id', '').strip()
        search = request.args.get('search', '').strip()

        images = []

        # Extract images from messages
        msg_query = {'images': {'$exists': True, '$ne': []}}
        if user_id:
            # Need to find conversation IDs for this user first
            conv_ids = [str(c['_id']) for c in db.conversations.find({'user_id': user_id}, {'_id': 1})]
            msg_query['conversation_id'] = {'$in': conv_ids}

        msg_cursor = db.messages.find(msg_query).sort('created_at', -1)
        for msg in msg_cursor:
            conv_id = str(msg.get('conversation_id', ''))
            # Look up user_id from conversation
            msg_user = 'unknown'
            try:
                from bson import ObjectId
                conv = db.conversations.find_one({'$or': [{'_id': conv_id}, {'_id': ObjectId(conv_id)}]}, {'user_id': 1})
                if conv:
                    msg_user = conv.get('user_id', 'unknown')
            except Exception:
                pass

            for img in msg.get('images', []):
                img_entry = {
                    'url': img.get('url', ''),
                    'cloud_url': img.get('cloud_url', ''),
                    'caption': img.get('caption', ''),
                    'name': img.get('caption', '') or f"Image from {msg.get('role', 'unknown')}",
                    'user_id': msg_user,
                    'created_at': msg.get('created_at'),
                    'source': 'message',
                    'conversation_id': conv_id,
                }
                if search and search.lower() not in (img_entry.get('caption', '') + img_entry.get('name', '')).lower():
                    continue
                images.append(img_entry)

        # Also get from uploaded_files collection
        file_query = {'mime_type': {'$regex': '^image/', '$options': 'i'}}
        if user_id:
            file_query['user_id'] = user_id
        if search:
            file_query['name'] = {'$regex': search, '$options': 'i'}

        try:
            for f in db.uploaded_files.find(file_query).sort('created_at', -1):
                images.append({
                    'url': f.get('path', ''),
                    'cloud_url': f.get('cloud_url', ''),
                    'caption': f.get('name', ''),
                    'name': f.get('name', 'Uploaded Image'),
                    'user_id': f.get('user_id', 'unknown'),
                    'created_at': f.get('created_at'),
                    'source': 'upload',
                })
        except Exception:
            pass

        total = len(images)
        start = (page - 1) * per_page
        paged = images[start:start + per_page]

        return jsonify({'images': paged, 'total': total, 'page': page})
    except Exception as e:
        logger.error(f"[Admin] Images error: {e}")
        return jsonify({'error': str(e)}), 500


# ── Memory ──────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/memory', methods=['GET'])
@require_admin
def get_memory():
    """Get all AI memory/learning data."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        user_id = request.args.get('user_id', '').strip()
        search = request.args.get('search', '').strip()

        query = {}
        if user_id:
            query['user_id'] = user_id
        if search:
            query['$or'] = [
                {'content': {'$regex': search, '$options': 'i'}},
                {'question': {'$regex': search, '$options': 'i'}},
                {'tags': {'$regex': search, '$options': 'i'}},
            ]

        total = db.chatbot_memory.count_documents(query)
        memories = list(db.chatbot_memory.find(query)
                        .sort('created_at', -1)
                        .skip((page - 1) * per_page)
                        .limit(per_page))

        for m in memories:
            m['_id'] = str(m['_id'])

        return jsonify({'memories': memories, 'total': total, 'page': page})
    except Exception as e:
        logger.error(f"[Admin] Memory error: {e}")
        return jsonify({'error': str(e)}), 500


# ── Logs ────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/logs', methods=['GET'])
@require_admin
def get_logs():
    """Get interaction logs (chat_logs collection)."""
    db = _get_db()
    if db is None:
        return jsonify({'error': 'Database not available'}), 503

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        user_id = request.args.get('user_id', '').strip()
        event = request.args.get('event', '').strip()
        search = request.args.get('search', '').strip()

        query = {}
        if user_id:
            query['$or'] = [{'session_id': user_id}, {'user_id': user_id}]
        if event:
            query['event'] = event
        if search:
            search_conditions = [
                {'message': {'$regex': search, '$options': 'i'}},
                {'response': {'$regex': search, '$options': 'i'}},
            ]
            if '$or' in query:
                query['$and'] = [{'$or': query.pop('$or')}, {'$or': search_conditions}]
            else:
                query['$or'] = search_conditions

        # Try chat_logs collection
        col_name = 'chat_logs'
        if col_name not in db.list_collection_names():
            return jsonify({'logs': [], 'total': 0, 'page': page})

        total = db[col_name].count_documents(query)
        logs = list(db[col_name].find(query)
                    .sort('timestamp', -1)
                    .skip((page - 1) * per_page)
                    .limit(per_page))

        for l in logs:
            l['_id'] = str(l['_id'])

        return jsonify({'logs': logs, 'total': total, 'page': page})
    except Exception as e:
        logger.error(f"[Admin] Logs error: {e}")
        return jsonify({'error': str(e)}), 500


# Payment Requests

@admin_bp.route('/api/admin/payments', methods=['GET'])
@require_admin
def get_payment_requests():
    db = _get_db()
    status = request.args.get('status')
    items = list_payment_requests(db, status if status and status != 'all' else None)
    return jsonify({'payments': items, 'total': len(items)})


@admin_bp.route('/api/admin/payments/<req_id>/approve', methods=['POST'])
@require_admin
def approve_payment(req_id):
    db = _get_db()
    ok = approve_payment_request(db, req_id, session.get('username', 'admin'))
    if ok:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Not found or already processed'}), 404


@admin_bp.route('/api/admin/payments/<req_id>/reject', methods=['POST'])
@require_admin
def reject_payment(req_id):
    db = _get_db()
    ok = reject_payment_request(db, req_id, session.get('username', 'admin'))
    if ok:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Not found or already processed'}), 404


@admin_bp.route('/api/admin/users/<username>/quota/reset', methods=['POST'])
@require_admin
def reset_user_quota(username):
    db = _get_db()
    ok = reset_image_quota(db, username)
    return jsonify({'success': ok})


@admin_bp.route('/api/admin/users/<username>/video/unlock', methods=['POST'])
@require_admin
def unlock_video(username):
    db = _get_db()
    result = db['users'].update_one({'username': username}, {'': {'video_unlocked': True}})
    return jsonify({'success': result.modified_count > 0})


@admin_bp.route('/api/admin/users/<username>/video/lock', methods=['POST'])
@require_admin
def lock_video(username):
    db = _get_db()
    result = db['users'].update_one({'username': username}, {'': {'video_unlocked': False}})
    return jsonify({'success': result.modified_count > 0})
