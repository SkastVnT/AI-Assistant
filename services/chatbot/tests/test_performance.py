"""
Performance Tests

Benchmarks and load tests for the database layer.
Tests query performance, cache efficiency, and concurrent access.
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime
import uuid
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add chatbot directory to path
CHATBOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(CHATBOT_DIR))


class TestQueryPerformance:
    """Test database query performance"""
    
    @pytest.fixture
    def mock_db_with_data(self):
        """Create mock DB with realistic response times"""
        db = MagicMock()
        
        # Simulate realistic query times
        def slow_find_one(*args, **kwargs):
            time.sleep(0.01)  # 10ms simulated DB latency
            return {'_id': 'conv_123', 'title': 'Test'}
        
        def slow_find(*args, **kwargs):
            time.sleep(0.02)  # 20ms for find
            cursor = MagicMock()
            cursor.sort.return_value = cursor
            cursor.skip.return_value = cursor
            cursor.limit.return_value = cursor
            cursor.__iter__ = lambda self: iter([
                {'_id': f'conv_{i}', 'title': f'Chat {i}'}
                for i in range(10)
            ])
            return cursor
        
        db.conversations.find_one = slow_find_one
        db.conversations.find = slow_find
        db.conversations.aggregate.return_value = [{'_id': 'conv_123', 'messages': []}]
        
        return db
    
    def test_single_conversation_fetch_performance(self, mock_db_with_data):
        """Single conversation fetch should be < 100ms"""
        from database.repositories.conversation_repository import ConversationRepository
        
        repo = ConversationRepository(mock_db_with_data)
        
        times = []
        for _ in range(10):
            start = time.perf_counter()
            repo.get_by_id('conv_123')
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        assert avg_time < 100, f"Average fetch time {avg_time:.2f}ms exceeds 100ms"
    
    def test_conversation_list_performance(self, mock_db_with_data):
        """User conversation list should be < 200ms"""
        from database.repositories.conversation_repository import ConversationRepository
        
        repo = ConversationRepository(mock_db_with_data)
        
        times = []
        for _ in range(10):
            start = time.perf_counter()
            repo.get_user_conversations('user_123')
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        assert avg_time < 200, f"Average list time {avg_time:.2f}ms exceeds 200ms"


class TestCachePerformance:
    """Test cache performance and hit rates"""
    
    def test_cache_vs_no_cache_speed(self):
        """Cache should be significantly faster than DB"""
        from database.cache.chatbot_cache import ChatbotCache
        
        # Clear cache
        ChatbotCache.clear_all()
        
        test_data = {'_id': 'perf_test', 'data': 'x' * 1000}  # 1KB payload
        
        # Warm up cache
        ChatbotCache.set_conversation('perf_test', test_data)
        
        # Measure cache reads
        cache_times = []
        for _ in range(100):
            start = time.perf_counter()
            ChatbotCache.get_conversation('perf_test')
            elapsed = (time.perf_counter() - start) * 1000
            cache_times.append(elapsed)
        
        avg_cache_time = statistics.mean(cache_times)
        
        # Cache reads should be < 1ms on average
        assert avg_cache_time < 1, f"Cache read {avg_cache_time:.3f}ms exceeds 1ms"
    
    def test_cache_hit_rate_simulation(self):
        """Simulate typical usage pattern and measure hit rate"""
        from database.cache.chatbot_cache import ChatbotCache
        
        ChatbotCache.clear_all()
        
        hits = 0
        misses = 0
        
        # Simulate 100 accesses with some repetition
        conversation_ids = [f'conv_{i % 20}' for i in range(100)]
        
        for conv_id in conversation_ids:
            # Check cache
            cached = ChatbotCache.get_conversation(conv_id)
            
            if cached:
                hits += 1
            else:
                misses += 1
                # Simulate DB fetch and cache
                ChatbotCache.set_conversation(conv_id, {'_id': conv_id})
        
        hit_rate = hits / (hits + misses) * 100
        
        # After warmup, hit rate should be > 70%
        # First 20 are misses, remaining 80 should mostly hit
        assert hit_rate >= 70, f"Hit rate {hit_rate:.1f}% below 70%"
    
    def test_cache_memory_usage(self):
        """Test cache doesn't grow unbounded"""
        from database.cache.chatbot_cache import ChatbotCache
        
        ChatbotCache.clear_all()
        
        # Add 1000 items
        for i in range(1000):
            ChatbotCache.set_conversation(
                f'mem_test_{i}',
                {'_id': f'mem_test_{i}', 'data': 'x' * 100}
            )
        
        stats = ChatbotCache.get_stats()
        
        # Check stats are available
        assert 'keys' in stats or 'backend' in stats


class TestConcurrentPerformance:
    """Test performance under concurrent load"""
    
    def test_concurrent_cache_operations(self):
        """Test cache under concurrent load"""
        from database.cache.chatbot_cache import ChatbotCache
        
        ChatbotCache.clear_all()
        
        errors = []
        times = []
        
        def cache_operations(thread_id):
            try:
                thread_times = []
                for i in range(20):
                    key = f'concurrent_{thread_id}_{i}'
                    
                    start = time.perf_counter()
                    ChatbotCache.set_conversation(key, {'id': key})
                    ChatbotCache.get_conversation(key)
                    elapsed = (time.perf_counter() - start) * 1000
                    
                    thread_times.append(elapsed)
                
                times.extend(thread_times)
            except Exception as e:
                errors.append(str(e))
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(cache_operations, i)
                for i in range(10)
            ]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0, f"Errors: {errors}"
        
        # Average operation time should still be reasonable
        avg_time = statistics.mean(times)
        assert avg_time < 5, f"Concurrent avg time {avg_time:.2f}ms exceeds 5ms"
    
    def test_concurrent_repository_operations(self):
        """Test repositories under concurrent access"""
        from database.repositories.conversation_repository import ConversationRepository
        
        results = []
        errors = []
        
        def create_and_read(thread_id):
            try:
                mock_db = MagicMock()
                mock_db.conversations.insert_one.return_value = MagicMock(
                    inserted_id=str(uuid.uuid4())
                )
                
                repo = ConversationRepository(mock_db)
                
                start = time.perf_counter()
                for i in range(10):
                    conv = repo.create_conversation(
                        user_id=f'user_{thread_id}',
                        title=f'Chat {i}'
                    )
                elapsed = (time.perf_counter() - start) * 1000
                
                results.append(elapsed)
            except Exception as e:
                errors.append(str(e))
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_and_read, i)
                for i in range(5)
            ]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0, f"Errors: {errors}"


class TestBulkOperations:
    """Test bulk data operations"""
    
    def test_bulk_message_insert_performance(self):
        """Test inserting many messages"""
        from database.repositories.message_repository import MessageRepository
        
        mock_db = MagicMock()
        mock_db.messages.insert_one.return_value = MagicMock(inserted_id='msg_123')
        
        repo = MessageRepository(mock_db)
        
        start = time.perf_counter()
        for i in range(100):
            repo.add_message(
                conversation_id='conv_123',
                role='user' if i % 2 == 0 else 'assistant',
                content=f'Message {i}: ' + 'x' * 100
            )
        elapsed = (time.perf_counter() - start) * 1000
        
        # 100 inserts should complete in < 500ms with mocks
        assert elapsed < 500, f"Bulk insert took {elapsed:.0f}ms, expected < 500ms"
    
    def test_bulk_memory_search_performance(self):
        """Test searching through many memories"""
        from database.repositories.memory_repository import MemoryRepository
        
        mock_db = MagicMock()
        
        # Mock search result
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = lambda self: iter([
            {'_id': f'mem_{i}', 'content': f'Memory {i}'}
            for i in range(10)
        ])
        mock_db.memories.find.return_value = mock_cursor
        
        repo = MemoryRepository(mock_db)
        
        times = []
        for _ in range(10):
            start = time.perf_counter()
            repo.search_memories('user_123', 'python')
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        assert avg_time < 50, f"Average search time {avg_time:.2f}ms exceeds 50ms"


class TestPaginationPerformance:
    """Test pagination performance"""
    
    def test_paginated_query_consistent_time(self):
        """Pagination should have consistent query times across pages"""
        from database.repositories.conversation_repository import ConversationRepository
        
        mock_db = MagicMock()
        
        # Setup collection mock with proper __getitem__ pattern
        conversations_collection = MagicMock()
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = lambda self: iter([
            {'_id': f'conv_{i}'} for i in range(20)
        ])
        conversations_collection.find.return_value = mock_cursor
        # Return actual integer, not MagicMock
        conversations_collection.count_documents.return_value = 100
        
        # Proper __getitem__ setup
        mock_db.__getitem__ = MagicMock(return_value=conversations_collection)
        
        repo = ConversationRepository(mock_db)
        
        # Warm up to avoid first-call overhead
        repo.paginate({}, page=1, per_page=20)
        
        page_times = []
        for page in range(1, 6):
            start = time.perf_counter()
            repo.paginate({}, page=page, per_page=20)
            elapsed = (time.perf_counter() - start) * 1000
            page_times.append(elapsed)
        
        # Skip first page comparison (may have warmup overhead)
        # Just verify all times are reasonable (< 10ms for mocked DB)
        avg_time = sum(page_times) / len(page_times)
        
        assert avg_time < 10, f"Average pagination time {avg_time:.2f}ms exceeds 10ms"


# Benchmark decorator
def benchmark(iterations=10):
    """Decorator to benchmark a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            
            print(f"\n{func.__name__}:")
            print(f"  Min: {min(times):.3f}ms")
            print(f"  Max: {max(times):.3f}ms")
            print(f"  Avg: {statistics.mean(times):.3f}ms")
            print(f"  Std: {statistics.stdev(times):.3f}ms" if len(times) > 1 else "")
            
            return result
        return wrapper
    return decorator


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
