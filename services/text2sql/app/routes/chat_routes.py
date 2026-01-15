"""
Chat Routes
Chat and SQL generation endpoints
"""

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# State management
YES_WORDS = ["có", "đồng ý", "yes", "ok", "oke", "okay"]
NO_WORDS = ["không", "không cần", "no", "ko", "khong"]
pending_question = None


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint for SQL generation.
    
    Flow:
    1. Find question in dataset -> return SQL immediately
    2. Not found -> ask for confirmation (needs_confirmation=true)
    3. User confirms -> generate SQL with AI (needs_check=true)
    4. User can then /check to approve and save to memory
    """
    global pending_question
    
    from ..controllers.chat_controller import ChatController
    controller = ChatController()
    
    data = request.get_json() or {}
    question = (data.get('question') or data.get('message', '')).strip()
    model = data.get('model', current_app.config.get('DEFAULT_SQL_MODEL', 'grok'))
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    # Check for confirmation responses
    q_lower = question.lower()
    
    # User confirms "yes" to pending question
    if any(w in q_lower for w in YES_WORDS) and pending_question:
        result = controller.generate_sql_with_confirmation(pending_question, model)
        pending_question = None
        return jsonify(result)
    
    # User says "no"
    if any(w in q_lower for w in NO_WORDS) and pending_question:
        pending_question = None
        return jsonify({
            'message': 'Đã hủy. Bạn có thể hỏi câu khác.',
            'cancelled': True
        })
    
    # Try to find in dataset first
    result = controller.find_or_ask_confirmation(question)
    
    if result.get('needs_confirmation'):
        pending_question = question
    
    return jsonify(result)


@chat_bp.route('/check', methods=['POST'])
def check_sql():
    """
    Approve and save SQL to memory.
    Called after user reviews generated SQL.
    """
    from ..controllers.chat_controller import ChatController
    controller = ChatController()
    
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    sql = data.get('sql', '').strip()
    
    if not question or not sql:
        return jsonify({'error': 'Question and SQL are required'}), 400
    
    result = controller.approve_sql(question, sql)
    return jsonify(result)


@chat_bp.route('/refine', methods=['POST'])
def refine_sql():
    """
    Refine an existing SQL query based on feedback.
    """
    from ..controllers.chat_controller import ChatController
    controller = ChatController()
    
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    prev_sql = data.get('sql', '').strip()
    feedback = data.get('feedback', '')
    extra_context = data.get('extra_context', '')
    model = data.get('model', current_app.config.get('REFINE_STRATEGY', 'gemini'))
    
    if not question or not prev_sql:
        return jsonify({'error': 'Question and previous SQL are required'}), 400
    
    result = controller.refine_sql(question, prev_sql, feedback, extra_context, model)
    return jsonify(result)


@chat_bp.route('/evaluate', methods=['GET'])
def evaluate():
    """
    Evaluate model performance using eval dataset.
    """
    from ..controllers.chat_controller import ChatController
    controller = ChatController()
    
    result = controller.evaluate_model()
    return jsonify(result)
