"""
ChatBot Database Integration Example

This file shows how to integrate the database service into ChatBot/app.py
Copy the relevant sections to your app.py file.
"""

# ==============================================================================
# 1. ADD IMPORTS AT TOP OF app.py (after existing imports)
# ==============================================================================

# Add these imports after line 20 (after existing imports)
try:
    from database.services import chatbot_service
    from database.utils.session_context import db_session
    DATABASE_ENABLED = True
    logger.info("✅ Database service loaded successfully")
except Exception as e:
    DATABASE_ENABLED = False
    logger.warning(f"⚠️ Database service not available: {e}")
    logger.warning("⚠️ Running in file-based mode")


# ==============================================================================
# 2. USER SESSION MANAGEMENT (add helper function)
# ==============================================================================

def get_or_create_user():
    """
    Get or create user from session
    
    Returns:
        int: User ID
    """
    if not DATABASE_ENABLED:
        return None
    
    # Check if user_id already in session
    user_id = session.get('user_id')
    
    if not user_id:
        # Generate unique username from session_id or create anonymous user
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Create or get user
        username = f"user_{session_id[:8]}"
        user = chatbot_service.get_or_create_user(
            username=username,
            full_name="Anonymous User"
        )
        user_id = user['id']
        session['user_id'] = user_id
        logger.info(f"Created user {user_id} for session {session_id}")
    
    return user_id


# ==============================================================================
# 3. CONVERSATION MANAGEMENT (add helper functions)
# ==============================================================================

def get_or_create_conversation(user_id, conversation_id=None):
    """
    Get existing conversation or create new one
    
    Args:
        user_id: User ID
        conversation_id: Optional existing conversation ID
        
    Returns:
        dict: Conversation data
    """
    if not DATABASE_ENABLED:
        return None
    
    if conversation_id:
        # Get existing conversation
        conv = chatbot_service.get_conversation(
            conversation_id,
            include_messages=True,
            message_limit=50  # Load last 50 messages for context
        )
        return conv
    else:
        # Create new conversation
        conv = chatbot_service.create_conversation(
            user_id=user_id,
            title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            tags=["chatbot"]
        )
        return conv


# ==============================================================================
# 4. UPDATE /chat ENDPOINT (replace existing chat() function)
# ==============================================================================

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with database persistence"""
    try:
        logger.info(f"[CHAT] Received request - Content-Type: {request.content_type}")
        
        # Get user
        user_id = get_or_create_user() if DATABASE_ENABLED else None
        
        # Parse request (same as before)
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form
            message = data.get('message', '')
            model = data.get('model', 'gemini')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', 'false').lower() == 'true'
            conversation_id = data.get('conversation_id')  # NEW: get conversation ID
            
            # Parse JSON fields
            try:
                tools = json.loads(data.get('tools', '[]')) if data.get('tools') else []
            except:
                tools = []
            
            try:
                history_str = data.get('history', 'null')
                history = json.loads(history_str) if history_str and history_str != 'null' else None
            except:
                history = None
                
            try:
                memory_ids = json.loads(data.get('memory_ids', '[]')) if data.get('memory_ids') else []
            except:
                memory_ids = []
            
            # Handle uploaded files
            files = request.files.getlist('files')
            # NEW: Track files in database
            if files and DATABASE_ENABLED and conversation_id:
                for file in files:
                    if file.filename:
                        # Save file (existing logic)
                        filename = file.filename
                        # ... your existing file save logic ...
                        
                        # Track in database
                        chatbot_service.track_uploaded_file(
                            user_id=user_id,
                            conversation_id=int(conversation_id),
                            filename=filename,
                            file_path=str(saved_path),  # your file path
                            file_type=file.content_type,
                            file_size=len(file.read())
                        )
        else:
            # JSON request
            data = request.json
            message = data.get('message', '')
            model = data.get('model', 'gemini')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', False)
            tools = data.get('tools', [])
            history = data.get('history', None)
            memory_ids = data.get('memory_ids', [])
            conversation_id = data.get('conversation_id')  # NEW
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
        # NEW: Get or create conversation
        if DATABASE_ENABLED and user_id:
            if conversation_id:
                conversation_id = int(conversation_id)
            
            # Get/create conversation
            conv = get_or_create_conversation(user_id, conversation_id)
            if not conv:
                # Create new if not found
                conv = chatbot_service.create_conversation(user_id=user_id)
            
            conversation_id = conv['id']
            
            # Save user message to database
            chatbot_service.save_message(
                conversation_id=conversation_id,
                role='user',
                content=message,
                metadata={'model': model, 'context': context}
            )
        
        # Get chatbot instance (existing logic)
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Handle tools (existing logic - no changes needed)
        tool_results = []
        if tools and len(tools) > 0:
            logger.info(f"[TOOLS] Active tools: {tools}")
            
            if 'google-search' in tools:
                logger.info(f"[TOOLS] Running Google Search for: {message}")
                search_result = google_search_tool(message)
                tool_results.append(f"## 🔍 Google Search Results\n\n{search_result}")
            
            if 'github' in tools:
                logger.info(f"[TOOLS] Running GitHub Search for: {message}")
                github_result = github_search_tool(message)
                tool_results.append(f"## 🐙 GitHub Search Results\n\n{github_result}")
        
        # If tools were used, return tool results
        if tool_results:
            combined_results = "\n\n---\n\n".join(tool_results)
            
            # NEW: Save tool results as assistant message
            if DATABASE_ENABLED and conversation_id:
                chatbot_service.save_message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=combined_results,
                    model='tools',
                    metadata={'tools_used': tools}
                )
            
            return jsonify({
                'response': combined_results,
                'model': 'tools',
                'context': context,
                'deep_thinking': False,
                'tools': tools,
                'conversation_id': conversation_id,  # NEW: return conversation ID
                'timestamp': datetime.now().isoformat()
            })
        
        # NEW: Load memories from database instead of files
        memories = []
        if memory_ids and DATABASE_ENABLED:
            # Load from database
            for mem_id in memory_ids:
                # Fetch memory by ID
                # Note: You may need to add get_memory_by_id to chatbot_service
                pass
        elif memory_ids:
            # OLD: Load from files (fallback)
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            memories.append(memory)
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # Generate response (existing logic)
        if history:
            original_history = chatbot.conversation_history.copy()
            response = chatbot.chat(message, model, context, deep_thinking, history, memories)
            chatbot.conversation_history = original_history
        else:
            response = chatbot.chat(message, model, context, deep_thinking, None, memories)
        
        # NEW: Save assistant response to database
        if DATABASE_ENABLED and conversation_id:
            chatbot_service.save_message(
                conversation_id=conversation_id,
                role='assistant',
                content=response,
                model=model,
                metadata={'context': context, 'deep_thinking': deep_thinking}
            )
        
        return jsonify({
            'response': response,
            'model': model,
            'context': context,
            'deep_thinking': deep_thinking,
            'tools': tools,
            'conversation_id': conversation_id,  # NEW: return conversation ID
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"[CHAT] Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ==============================================================================
# 5. ADD NEW ENDPOINTS FOR CONVERSATION MANAGEMENT
# ==============================================================================

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """List user's conversations"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database not enabled'}), 503
    
    try:
        user_id = get_or_create_user()
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 50))
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        
        conversations = chatbot_service.list_user_conversations(
            user_id=user_id,
            skip=skip,
            limit=limit,
            include_archived=include_archived
        )
        
        return jsonify({
            'conversations': conversations,
            'total': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation with messages"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database not enabled'}), 503
    
    try:
        conversation = chatbot_service.get_conversation(
            conversation_id,
            include_messages=True
        )
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify(conversation)
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete conversation"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database not enabled'}), 503
    
    try:
        success = chatbot_service.delete_conversation(conversation_id)
        
        if not success:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({'success': True, 'message': 'Conversation deleted'})
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<int:conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id):
    """Archive conversation"""
    if not DATABASE_ENABLED:
        return jsonify({'error': 'Database not enabled'}), 503
    
    try:
        success = chatbot_service.archive_conversation(conversation_id)
        
        if not success:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({'success': True, 'message': 'Conversation archived'})
        
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        return jsonify({'error': str(e)}), 500


# ==============================================================================
# 6. UPDATE MEMORY ENDPOINTS
# ==============================================================================

@app.route('/api/save-memory', methods=['POST'])
def save_memory():
    """Save memory to database"""
    if not DATABASE_ENABLED:
        # Fallback to file-based (existing logic)
        return save_memory_to_file()
    
    try:
        data = request.json
        user_id = get_or_create_user()
        
        memory = chatbot_service.save_memory(
            user_id=user_id,
            question=data.get('title', ''),
            answer=data.get('content', ''),
            conversation_id=data.get('conversation_id'),
            importance=int(data.get('importance', 5)),
            tags=data.get('tags', [])
        )
        
        return jsonify({
            'success': True,
            'memory_id': memory['id'],
            'message': 'Memory saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/memories', methods=['GET'])
def get_memories():
    """Get user memories"""
    if not DATABASE_ENABLED:
        # Fallback to file-based
        return get_memories_from_files()
    
    try:
        user_id = get_or_create_user()
        query = request.args.get('query')
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 50))
        
        if query:
            # Search memories
            memories = chatbot_service.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
        else:
            # List all memories
            memories = chatbot_service.get_user_memories(
                user_id=user_id,
                skip=skip,
                limit=limit
            )
        
        return jsonify({
            'memories': memories,
            'total': len(memories)
        })
        
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return jsonify({'error': str(e)}), 500


# ==============================================================================
# 7. BACKWARD COMPATIBILITY HELPERS (for file-based fallback)
# ==============================================================================

def save_memory_to_file():
    """Fallback: Save memory to file (existing implementation)"""
    # Your existing file-based save logic
    pass


def get_memories_from_files():
    """Fallback: Get memories from files (existing implementation)"""
    # Your existing file-based load logic
    pass


# ==============================================================================
# INTEGRATION NOTES:
# ==============================================================================
# 
# 1. DATABASE_ENABLED flag allows graceful fallback to file-based mode
# 2. All database operations are wrapped in try-except for error handling
# 3. User ID is automatically managed via Flask session
# 4. Conversations are created automatically on first message
# 5. Messages are saved with proper sequence numbers
# 6. Files are tracked in database with metadata
# 7. Memories are stored with full-text search support
# 8. New API endpoints for conversation management
# 9. Backward compatible - existing file-based logic still works
# 10. conversation_id is returned in responses for frontend tracking
