"""
Streaming Response Handler - Real-time AI Responses
Implements Server-Sent Events (SSE) for token-by-token streaming
"""

from flask import Response, stream_with_context
import json
import logging
from typing import Generator, Dict, Any
import time

logger = logging.getLogger(__name__)


class StreamingHandler:
    """
    Handle streaming responses for AI models
    
    Features:
    - Token-by-token streaming
    - Progress updates
    - Error handling
    - Connection management
    """
    
    @staticmethod
    def create_sse_response(
        generator: Generator,
        model: str = None,
        context: str = None
    ) -> Response:
        """
        Create Server-Sent Events (SSE) response
        
        Args:
            generator: Generator yielding tokens
            model: Model name
            context: Context mode
        
        Returns:
            Flask Response with streaming data
        """
        def generate():
            try:
                # Send initial metadata
                metadata = {
                    'type': 'start',
                    'model': model,
                    'context': context,
                    'timestamp': time.time()
                }
                yield f"data: {json.dumps(metadata)}\n\n"
                
                # Stream tokens
                for token in generator:
                    if token:
                        data = {
                            'type': 'token',
                            'content': token
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                
                # Send completion signal
                complete = {
                    'type': 'complete',
                    'timestamp': time.time()
                }
                yield f"data: {json.dumps(complete)}\n\n"
                
            except GeneratorExit:
                logger.info("Client disconnected from stream")
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error = {
                    'type': 'error',
                    'error': str(e)
                }
                yield f"data: {json.dumps(error)}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
    
    @staticmethod
    def stream_gemini_response(model, prompt: str) -> Generator[str, None, None]:
        """
        Stream Gemini response token by token
        
        Args:
            model: Gemini model instance
            prompt: User prompt
        
        Yields:
            Response tokens
        """
        try:
            response = model.generate_content(
                prompt,
                stream=True  # Enable streaming
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise
    
    @staticmethod
    def stream_openai_response(client, messages: list, model: str = "gpt-4") -> Generator[str, None, None]:
        """
        Stream OpenAI response token by token
        
        Args:
            client: OpenAI client instance
            messages: Conversation messages
            model: Model name
        
        Yields:
            Response tokens
        """
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True  # Enable streaming
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    @staticmethod
    def stream_deepseek_response(client, messages: list) -> Generator[str, None, None]:
        """
        Stream DeepSeek response token by token
        
        Args:
            client: DeepSeek client instance (OpenAI compatible)
            messages: Conversation messages
        
        Yields:
            Response tokens
        """
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True  # Enable streaming
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"DeepSeek streaming error: {e}")
            raise
    
    @staticmethod
    def stream_progress(
        task_name: str,
        total_steps: int
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream progress updates for long-running tasks
        
        Args:
            task_name: Name of the task
            total_steps: Total number of steps
        
        Yields:
            Progress updates
        """
        for step in range(total_steps):
            progress = {
                'type': 'progress',
                'task': task_name,
                'step': step + 1,
                'total': total_steps,
                'percentage': round(((step + 1) / total_steps) * 100, 2)
            }
            yield progress
            time.sleep(0.1)  # Small delay for visualization


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
# Example 1: Streaming chat response

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    data = request.json
    message = data['message']
    model = data['model']
    
    if model == 'gemini':
        generator = StreamingHandler.stream_gemini_response(
            gemini_model, 
            message
        )
    elif model == 'openai':
        generator = StreamingHandler.stream_openai_response(
            openai_client,
            [{'role': 'user', 'content': message}]
        )
    
    return StreamingHandler.create_sse_response(
        generator,
        model=model,
        context='casual'
    )


# Example 2: Frontend consumption

const eventSource = new EventSource('/api/chat/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'start':
            console.log('Stream started:', data.model);
            break;
            
        case 'token':
            // Append token to message
            appendToken(data.content);
            break;
            
        case 'complete':
            console.log('Stream complete');
            eventSource.close();
            break;
            
        case 'error':
            console.error('Stream error:', data.error);
            eventSource.close();
            break;
    }
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
"""
