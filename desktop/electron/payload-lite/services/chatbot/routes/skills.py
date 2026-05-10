"""
Skills routes: /api/skills — runtime skill management for the chatbot UI and external clients.

Endpoints:
    GET  /api/skills           — list available skills
    GET  /api/skills/<id>      — fetch one skill by id
    POST /api/skills/activate  — set active skill for the current session
    POST /api/skills/deactivate — clear active skill for the current session
    GET  /api/skills/active    — get the currently active skill for the session
"""
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, session
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.skills.registry import get_skill_registry
from core.skills.session import get_session_skill, set_session_skill, clear_session_skill

logger = logging.getLogger(__name__)

skills_bp = Blueprint('skills', __name__)


@skills_bp.route('/api/skills', methods=['GET'])
def list_skills():
    """List available runtime skills for the frontend skill selector.

    Query params:
        include_disabled (bool): include disabled skills (default: false)
        tag (str): filter by tag (optional, repeatable)

    Returns:
        {
            "skills": [ { id, name, description, ... }, ... ],
            "total": int
        }
    """
    registry = get_skill_registry()
    include_disabled = request.args.get('include_disabled', 'false').lower() == 'true'
    filter_tags = request.args.getlist('tag')

    if include_disabled:
        skills = registry.list_all()
    else:
        skills = registry.list_ui_visible()

    if filter_tags:
        skills = [s for s in skills if any(t in s.tags for t in filter_tags)]

    result = []
    for s in skills:
        result.append({
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'default_model': s.default_model,
            'default_thinking_mode': s.default_thinking_mode,
            'default_context': s.default_context,
            'preferred_tools': s.preferred_tools,
            'blocked_tools': s.blocked_tools,
            'tags': s.tags,
            'enabled': s.enabled,
            'ui_visible': s.ui_visible,
        })

    return jsonify({
        'skills': result,
        'total': len(result),
    })


@skills_bp.route('/api/skills/<skill_id>', methods=['GET'])
def get_skill(skill_id):
    """Fetch a single skill by id.

    Returns:
        { "skill": { id, name, description, ... } }
        404 if not found.
    """
    registry = get_skill_registry()
    skill = registry.get(skill_id)
    if skill is None:
        skill = registry.get_by_name(skill_id)
    if skill is None:
        return jsonify({'error': f'Skill not found: {skill_id}'}), 404

    return jsonify({
        'skill': {
            'id': skill.id,
            'name': skill.name,
            'description': skill.description,
            'prompt_fragments': skill.prompt_fragments,
            'default_model': skill.default_model,
            'default_thinking_mode': skill.default_thinking_mode,
            'default_context': skill.default_context,
            'preferred_tools': skill.preferred_tools,
            'blocked_tools': skill.blocked_tools,
            'trigger_keywords': skill.trigger_keywords,
            'tags': skill.tags,
            'enabled': skill.enabled,
            'ui_visible': skill.ui_visible,
            'builtin': skill.builtin,
            'priority': skill.priority,
        }
    })


@skills_bp.route('/api/skills/activate', methods=['POST'])
def activate_skill():
    """Set the active skill for the current session.

    Request Body (JSON):
        { "skill_id": "coding-assistant" }

    Returns:
        { "success": true, "skill_id": "...", "skill_name": "..." }
        400 if skill_id missing or invalid.
    """
    data = request.get_json(silent=True) or {}
    skill_id = data.get('skill_id', '').strip()

    if not skill_id:
        return jsonify({'success': False, 'error': 'skill_id is required'}), 400

    registry = get_skill_registry()
    skill = registry.get(skill_id)
    if skill is None:
        skill = registry.get_by_name(skill_id)
    if skill is None:
        return jsonify({'success': False, 'error': f'Skill not found: {skill_id}'}), 404
    if not skill.enabled:
        return jsonify({'success': False, 'error': f'Skill is disabled: {skill.id}'}), 400

    # Ensure session exists
    if 'session_id' not in session:
        import uuid
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']
    set_session_skill(session_id, skill.id)
    logger.info(f"[Skills] Activated skill '{skill.id}' for session {session_id[:8]}...")

    return jsonify({
        'success': True,
        'skill_id': skill.id,
        'skill_name': skill.name,
        'session_id': session_id,
    })


@skills_bp.route('/api/skills/deactivate', methods=['POST'])
def deactivate_skill():
    """Clear the active skill for the current session.

    Returns:
        { "success": true, "had_active": true/false }
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'success': True, 'had_active': False})

    had_active = clear_session_skill(session_id)
    if had_active:
        logger.info(f"[Skills] Deactivated skill for session {session_id[:8]}...")

    return jsonify({
        'success': True,
        'had_active': had_active,
    })


@skills_bp.route('/api/skills/active', methods=['GET'])
def get_active_skill():
    """Get the currently active skill for this session.

    Returns:
        { "skill_id": "coding-assistant", "skill_name": "...", "active": true }
        or { "skill_id": null, "active": false } if none.
    """
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'skill_id': None, 'active': False})

    active_id = get_session_skill(session_id)
    if not active_id:
        return jsonify({'skill_id': None, 'active': False})

    registry = get_skill_registry()
    skill = registry.get(active_id)
    if skill is None:
        # Stale session binding — skill was removed
        clear_session_skill(session_id)
        return jsonify({'skill_id': None, 'active': False})

    return jsonify({
        'skill_id': skill.id,
        'skill_name': skill.name,
        'active': True,
    })
