"""
Streaming Chat Module - SSE (Server-Sent Events) support for real-time responses
"""
import json
import logging
from typing import Generator, Optional, Dict, Any, Callable
from flask import Response, stream_with_context
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Represents a Server-Sent Event"""
    event: str = "message"
    data: str = ""
    id: Optional[str] = None
    retry: Optional[int] = None
    
    def format(self) -> str:
        """Format as SSE string"""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event != "message":
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # Data can be multiline
        for line in self.data.split('\n'):
            lines.append(f"data: {line}")
        
        lines.append("")  # Empty line to end event
        return '\n'.join(lines) + '\n'


class StreamingChatHandler:
    """Handles streaming chat responses via SSE"""
    
    @staticmethod
    def create_sse_response(generator: Generator[str, None, None]) -> Response:
        """Create a Flask SSE response from a generator"""
        
        def generate_events():
            try:
                # Send initial event
                yield StreamEvent(event="start", data=json.dumps({"status": "started"})).format()
                
                full_response = ""
                for chunk in generator:
                    if chunk:
                        full_response += chunk
                        yield StreamEvent(
                            event="chunk",
                            data=json.dumps({"content": chunk})
                        ).format()
                
                # Send completion event
                yield StreamEvent(
                    event="done",
                    data=json.dumps({"status": "complete", "full_response": full_response})
                ).format()
                
            except Exception as e:
                logger.error(f"[SSE] Error during streaming: {e}")
                yield StreamEvent(
                    event="error",
                    data=json.dumps({"error": str(e)})
                ).format()
        
        return Response(
            stream_with_context(generate_events()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
            }
        )
    
    @staticmethod
    def create_json_stream_response(
        generator: Generator[str, None, None],
        model: str,
        context: str,
        deep_thinking: bool
    ) -> Response:
        """Create SSE response with metadata"""
        
        def generate_events():
            try:
                # Send metadata first
                yield StreamEvent(
                    event="metadata",
                    data=json.dumps({
                        "model": model,
                        "context": context,
                        "deep_thinking": deep_thinking,
                        "streaming": True
                    })
                ).format()
                
                full_response = ""
                chunk_count = 0
                
                for chunk in generator:
                    if chunk:
                        full_response += chunk
                        chunk_count += 1
                        yield StreamEvent(
                            event="chunk",
                            data=json.dumps({
                                "content": chunk,
                                "chunk_index": chunk_count
                            })
                        ).format()
                
                # Send final event with complete response
                yield StreamEvent(
                    event="complete",
                    data=json.dumps({
                        "response": full_response,
                        "model": model,
                        "context": context,
                        "deep_thinking": deep_thinking,
                        "total_chunks": chunk_count
                    })
                ).format()
                
            except GeneratorExit:
                logger.info("[SSE] Client disconnected")
            except Exception as e:
                logger.error(f"[SSE] Streaming error: {e}")
                yield StreamEvent(
                    event="error",
                    data=json.dumps({"error": str(e), "model": model})
                ).format()
        
        return Response(
            stream_with_context(generate_events()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
            }
        )


def stream_chat_response(
    chat_generator: Generator[str, None, None],
    on_chunk: Optional[Callable[[str], None]] = None,
    on_complete: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None
) -> Generator[str, None, None]:
    """
    Wrapper for chat generators that allows hooking into events
    
    Args:
        chat_generator: The generator yielding chat chunks
        on_chunk: Callback for each chunk
        on_complete: Callback when streaming completes
        on_error: Callback on error
    """
    full_response = ""
    
    try:
        for chunk in chat_generator:
            if chunk:
                full_response += chunk
                if on_chunk:
                    on_chunk(chunk)
                yield chunk
        
        if on_complete:
            on_complete(full_response)
            
    except Exception as e:
        if on_error:
            on_error(e)
        raise


class NonStreamingToStreaming:
    """Convert non-streaming response to streaming format"""
    
    @staticmethod
    def simulate_stream(
        full_response: str,
        chunk_size: int = 10,
        delay_ms: int = 0
    ) -> Generator[str, None, None]:
        """
        Simulate streaming by yielding chunks of a complete response
        Useful for models that don't support native streaming
        """
        import time
        
        words = full_response.split(' ')
        buffer = []
        
        for word in words:
            buffer.append(word)
            if len(buffer) >= chunk_size:
                yield ' '.join(buffer) + ' '
                buffer = []
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000)
        
        if buffer:
            yield ' '.join(buffer)


# Convenience function for routes
def create_streaming_response(
    generator: Generator[str, None, None],
    model: str = "unknown",
    context: str = "casual",
    deep_thinking: bool = False
) -> Response:
    """Create a streaming SSE response for chat"""
    return StreamingChatHandler.create_json_stream_response(
        generator, model, context, deep_thinking
    )
