"""
Optimized ChatBot Agent with Performance Enhancements
- Redis caching for responses
- MongoDB for conversation history
- Streaming support
- Database query optimization
"""

# Add this to app.py after the ChatbotAgent class definition

# ============================================================================
# OPTIMIZED CHAT METHOD WITH CACHING
# ============================================================================

def chat_with_cache_and_db(
    chatbot_instance,
    message: str,
    model: str,
    context: str,
    deep_thinking: bool = False,
    history: list = None,
    memories: list = None,
    session_id: str = None
) -> str:
    """
    Enhanced chat method with caching and database logging
    
    Args:
        chatbot_instance: ChatbotAgent instance
        message: User message
        model: Model name
        context: Context mode
        deep_thinking: Deep thinking mode
        history: Conversation history
        memories: Memory context
        session_id: Session ID for database logging
    
    Returns:
        AI response
    """
    # Try to get from cache (if not using custom history/memories)
    if cache and cache.enabled and history is None and memories is None:
        cached_response = cache.get_ai_response(model, message, context)
        if cached_response:
            logger.info(f"🎯 Cache HIT for {model}")
            return cached_response
    
    # Generate response
    start_time = time.time()
    response = chatbot_instance.chat(message, model, context, deep_thinking, history, memories)
    duration = time.time() - start_time
    
    # Cache response (if not using custom history/memories)
    if cache and cache.enabled and history is None and memories is None:
        cache.cache_ai_response(model, message, context, response, ttl=3600)
        logger.info(f"💾 Cached response for {model}")
    
    # Log to database
    if db and db.enabled and session_id:
        try:
            # Update session activity
            db.update_session_activity(session_id)
            
            # Log analytics
            db.log_event(
                event_type='message',
                session_id=session_id,
                data={
                    'model': model,
                    'context': context,
                    'deep_thinking': deep_thinking,
                    'duration': duration,
                    'message_length': len(message),
                    'response_length': len(response)
                }
            )
        except Exception as e:
            logger.error(f"Database logging error: {e}")
    
    return response


# ============================================================================
# STREAMING CHAT ENDPOINT
# ============================================================================

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Streaming chat endpoint with Server-Sent Events
    
    Request body:
        - message: User message
        - model: Model name (gemini, openai, deepseek)
        - context: Context mode
        - deep_thinking: Boolean
    
    Returns:
        SSE stream with tokens
    """
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model', 'gemini')
        context = data.get('context', 'casual')
        deep_thinking = data.get('deep_thinking', False)
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Build system prompt
        system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
        if deep_thinking:
            system_prompt += "\n\nIMPORTANT: Think deeply and analyze comprehensively."
        
        # Build conversation context
        conversation = f"{system_prompt}\n\n"
        for hist in chatbot.conversation_history[-5:]:
            conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
        conversation += f"User: {message}\nAssistant:"
        
        # Create streaming generator based on model
        if model == 'grok':
            grok_model = genai.GenerativeModel('grok-3')
            generator = streaming.stream_gemini_response(grok_model, conversation)
        
        elif model == 'openai':
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            generator = streaming.stream_openai_response(client, messages)
        
        elif model == 'deepseek':
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            generator = streaming.stream_deepseek_response(client, messages)
        
        else:
            return jsonify({'error': 'Model not supported for streaming'}), 400
        
        # Return SSE response
        return streaming.create_sse_response(
            generator,
            model=model,
            context=context
        )
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CACHE STATS ENDPOINT
# ============================================================================

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    if cache and cache.enabled:
        stats = cache.get_stats()
        return jsonify(stats)
    else:
        return jsonify({'enabled': False, 'message': 'Cache not available'})


@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """Clear all cache"""
    if cache and cache.enabled:
        cache.clear_all()
        return jsonify({'success': True, 'message': 'Cache cleared'})
    else:
        return jsonify({'error': 'Cache not available'}), 400


# ============================================================================
# DATABASE STATS ENDPOINT
# ============================================================================

@app.route('/api/db/stats', methods=['GET'])
def db_stats():
    """Get database statistics"""
    if db and db.enabled:
        stats = db.get_stats()
        return jsonify(stats)
    else:
        return jsonify({'enabled': False, 'message': 'Database not available'})


@app.route('/api/db/conversations', methods=['GET'])
def db_conversations():
    """Get user's conversations from database"""
    if not db or not db.enabled:
        return jsonify({'error': 'Database not available'}), 400
    
    try:
        session_id = session.get('session_id')
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        
        conversations = db.get_conversations(session_id, limit, skip)
        return jsonify({'conversations': conversations})
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PERFORMANCE MONITORING ENDPOINT
# ============================================================================

@app.route('/api/performance/stats', methods=['GET'])
def performance_stats():
    """Get overall performance statistics"""
    stats = {
        'cache': cache.get_stats() if cache and cache.enabled else {'enabled': False},
        'database': db.get_stats() if db and db.enabled else {'enabled': False},
        'features': {
            'performance_optimization': PERFORMANCE_ENABLED,
            'local_models': LOCALMODELS_AVAILABLE,
            'streaming': PERFORMANCE_ENABLED
        }
    }
    
    return jsonify(stats)


# ============================================================================
# USAGE NOTES
# ============================================================================

"""
INTEGRATION STEPS:

1. Add this file's content to app.py

2. Update the /chat endpoint to use caching:

@app.route('/chat', methods=['POST'])
def chat():
    # ... existing code ...
    
    session_id = session.get('session_id')
    chatbot = get_chatbot(session_id)
    
    # USE OPTIMIZED METHOD WITH CACHING
    response = chat_with_cache_and_db(
        chatbot,
        message,
        model,
        context,
        deep_thinking,
        history,
        memories,
        session_id
    )
    
    # ... rest of code ...


3. Frontend changes for streaming:

// Option 1: Use fetch API for regular requests (current)
const response = await fetch('/chat', { ... });

// Option 2: Use EventSource for streaming
const eventSource = new EventSource('/api/chat/stream');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'token') {
        appendToken(data.content);
    } else if (data.type === 'complete') {
        eventSource.close();
    }
};


4. Monitor performance:

GET /api/performance/stats  -> See cache hit rate, DB stats
GET /api/cache/stats        -> Detailed cache statistics
GET /api/db/stats           -> Database statistics
POST /api/cache/clear       -> Clear all cache
"""
