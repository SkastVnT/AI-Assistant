"""
Database Query Optimizer

Provides utilities for optimizing database queries:
- Eager loading patterns
- Bulk operations
- Query result caching
- Connection pooling
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable, TypeVar
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryOptimizer:
    """
    Utilities for optimizing MongoDB queries.
    """
    
    @staticmethod
    def build_projection(fields: List[str]) -> Dict[str, int]:
        """
        Build MongoDB projection to limit returned fields.
        Reduces network transfer and memory usage.
        
        Args:
            fields: List of field names to include
            
        Returns:
            MongoDB projection dict
        """
        return {field: 1 for field in fields}
    
    @staticmethod
    def build_pagination_pipeline(
        match: Dict[str, Any],
        sort: Dict[str, int],
        page: int = 1,
        per_page: int = 20,
        project: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build optimized aggregation pipeline for pagination.
        Uses $facet for efficient count + data in single query.
        
        Args:
            match: Match stage conditions
            sort: Sort specification
            page: Page number (1-indexed)
            per_page: Items per page
            project: Optional projection
            
        Returns:
            Aggregation pipeline
        """
        skip = (page - 1) * per_page
        
        pipeline = [
            {'$match': match},
            {'$facet': {
                'metadata': [
                    {'$count': 'total'}
                ],
                'data': [
                    {'$sort': sort},
                    {'$skip': skip},
                    {'$limit': per_page}
                ]
            }}
        ]
        
        if project:
            pipeline[1]['$facet']['data'].append({'$project': project})
        
        return pipeline
    
    @staticmethod
    def build_lookup_pipeline(
        from_collection: str,
        local_field: str,
        foreign_field: str,
        as_field: str,
        unwind: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build $lookup stage for joining collections.
        Equivalent to eager loading in ORMs.
        
        Args:
            from_collection: Collection to join
            local_field: Field from input documents
            foreign_field: Field from joined documents
            as_field: Output array field
            unwind: Whether to unwind the array
            
        Returns:
            Pipeline stages
        """
        stages = [{
            '$lookup': {
                'from': from_collection,
                'localField': local_field,
                'foreignField': foreign_field,
                'as': as_field
            }
        }]
        
        if unwind:
            stages.append({
                '$unwind': {
                    'path': f'${as_field}',
                    'preserveNullAndEmptyArrays': True
                }
            })
        
        return stages


class BulkOperations:
    """
    Utilities for bulk database operations.
    """
    
    def __init__(self, collection, batch_size: int = 1000):
        self.collection = collection
        self.batch_size = batch_size
        self._insert_buffer = []
        self._update_buffer = []
    
    def add_insert(self, document: Dict[str, Any]):
        """Add document to insert buffer"""
        self._insert_buffer.append(document)
        if len(self._insert_buffer) >= self.batch_size:
            self.flush_inserts()
    
    def add_update(self, filter_query: Dict, update: Dict):
        """Add update to buffer"""
        self._update_buffer.append((filter_query, update))
        if len(self._update_buffer) >= self.batch_size:
            self.flush_updates()
    
    def flush_inserts(self) -> int:
        """Execute buffered inserts"""
        if not self._insert_buffer:
            return 0
        
        try:
            result = self.collection.insert_many(
                self._insert_buffer,
                ordered=False  # Continue on errors
            )
            count = len(result.inserted_ids)
            logger.debug(f"Bulk inserted {count} documents")
            self._insert_buffer.clear()
            return count
        except Exception as e:
            logger.error(f"Bulk insert error: {e}")
            raise
    
    def flush_updates(self) -> int:
        """Execute buffered updates using bulk_write"""
        if not self._update_buffer:
            return 0
        
        try:
            from pymongo import UpdateOne
            
            operations = [
                UpdateOne(filter_q, {'$set': update})
                for filter_q, update in self._update_buffer
            ]
            
            result = self.collection.bulk_write(operations, ordered=False)
            count = result.modified_count
            logger.debug(f"Bulk updated {count} documents")
            self._update_buffer.clear()
            return count
        except Exception as e:
            logger.error(f"Bulk update error: {e}")
            raise
    
    def flush_all(self) -> Dict[str, int]:
        """Flush all buffers"""
        return {
            'inserted': self.flush_inserts(),
            'updated': self.flush_updates()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.flush_all()
        return False


def cached_query(
    cache_key_prefix: str,
    ttl: int = 3600,
    cache_none: bool = False
):
    """
    Decorator to cache query results.
    
    Args:
        cache_key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        cache_none: Whether to cache None results
        
    Usage:
        @cached_query("user_conversations", ttl=1800)
        def get_user_conversations(user_id):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from database.cache.chatbot_cache import ChatbotCache
                
                # Build cache key from function args
                key_parts = [cache_key_prefix]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                
                # Check cache
                cached = ChatbotCache.get_query_result(cache_key)
                if cached is not None:
                    return cached
                
                # Execute query
                result = func(*args, **kwargs)
                
                # Cache result
                if result is not None or cache_none:
                    ChatbotCache.set_query_result(cache_key, result, ttl)
                
                return result
            except ImportError:
                # No cache available, just execute
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def timed_query(operation_name: str = None):
    """
    Decorator to time and log query execution.
    
    Args:
        operation_name: Name for logging (defaults to function name)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                
                if elapsed > 100:  # Log slow queries (>100ms)
                    logger.warning(
                        f"Slow query: {name} took {elapsed:.2f}ms",
                        extra={'query_name': name, 'duration_ms': elapsed}
                    )
                else:
                    logger.debug(
                        f"Query {name}: {elapsed:.2f}ms",
                        extra={'query_name': name, 'duration_ms': elapsed}
                    )
                
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    f"Query {name} failed after {elapsed:.2f}ms: {e}",
                    extra={'query_name': name, 'duration_ms': elapsed, 'error': str(e)}
                )
                raise
        
        return wrapper
    return decorator


class ConnectionPool:
    """
    MongoDB connection pool manager.
    Provides connection reuse and health monitoring.
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'errors': 0
        }
    
    @classmethod
    def get_client(cls, uri: str = None, **kwargs):
        """
        Get or create MongoDB client with optimized settings.
        
        Args:
            uri: MongoDB connection URI
            **kwargs: Additional MongoClient options
        """
        if cls._client is not None:
            cls._instance._stats['connections_reused'] += 1
            return cls._client
        
        try:
            from pymongo import MongoClient
            
            # Optimized connection settings
            default_options = {
                'maxPoolSize': 50,
                'minPoolSize': 10,
                'maxIdleTimeMS': 30000,
                'waitQueueTimeoutMS': 10000,
                'serverSelectionTimeoutMS': 5000,
                'connectTimeoutMS': 5000,
                'socketTimeoutMS': 30000,
                'retryWrites': True,
                'retryReads': True,
            }
            default_options.update(kwargs)
            
            import os
            uri = uri or os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
            
            cls._client = MongoClient(uri, **default_options)
            cls._instance._stats['connections_created'] += 1
            
            logger.info("MongoDB connection pool initialized", extra={
                'max_pool_size': default_options['maxPoolSize'],
                'min_pool_size': default_options['minPoolSize']
            })
            
            return cls._client
            
        except Exception as e:
            cls._instance._stats['errors'] += 1
            logger.error(f"Failed to create MongoDB client: {e}")
            raise
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = cls._instance._stats.copy() if cls._instance else {}
        
        if cls._client:
            try:
                server_info = cls._client.server_info()
                stats['server_version'] = server_info.get('version')
            except Exception:
                # Ignore if server info is unavailable
                pass
        
        return stats
    
    @classmethod
    def close(cls):
        """Close the connection pool"""
        if cls._client:
            cls._client.close()
            cls._client = None
            logger.info("MongoDB connection pool closed")


# Index management utilities
class IndexManager:
    """
    Utilities for managing database indexes.
    """
    
    # Recommended indexes for chatbot collections
    RECOMMENDED_INDEXES = {
        'conversations': [
            {'keys': [('user_id', 1), ('created_at', -1)], 'name': 'idx_user_created'},
            {'keys': [('user_id', 1), ('is_deleted', 1)], 'name': 'idx_user_deleted'},
            {'keys': [('updated_at', -1)], 'name': 'idx_updated'},
        ],
        'messages': [
            {'keys': [('conversation_id', 1), ('created_at', 1)], 'name': 'idx_conv_created'},
            {'keys': [('conversation_id', 1), ('is_deleted', 1)], 'name': 'idx_conv_deleted'},
        ],
        'memories': [
            {'keys': [('user_id', 1), ('importance', -1)], 'name': 'idx_user_importance'},
            {'keys': [('user_id', 1), ('category', 1)], 'name': 'idx_user_category'},
            {'keys': [('tags', 1)], 'name': 'idx_tags'},
            {'keys': [('content', 'text')], 'name': 'idx_content_text'},
        ]
    }
    
    @classmethod
    def ensure_indexes(cls, db, collections: List[str] = None):
        """
        Ensure recommended indexes exist.
        
        Args:
            db: MongoDB database instance
            collections: List of collections to index (default: all)
        """
        collections = collections or list(cls.RECOMMENDED_INDEXES.keys())
        
        for collection_name in collections:
            if collection_name not in cls.RECOMMENDED_INDEXES:
                continue
            
            collection = db[collection_name]
            existing_indexes = {idx['name'] for idx in collection.list_indexes()}
            
            for index_spec in cls.RECOMMENDED_INDEXES[collection_name]:
                if index_spec['name'] not in existing_indexes:
                    try:
                        collection.create_index(
                            index_spec['keys'],
                            name=index_spec['name'],
                            background=True
                        )
                        logger.info(
                            f"Created index {index_spec['name']} on {collection_name}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to create index {index_spec['name']}: {e}"
                        )
    
    @classmethod
    def analyze_indexes(cls, db, collection_name: str) -> Dict[str, Any]:
        """
        Analyze index usage for a collection.
        
        Args:
            db: MongoDB database instance
            collection_name: Collection to analyze
            
        Returns:
            Index analysis results
        """
        collection = db[collection_name]
        
        result = {
            'collection': collection_name,
            'indexes': [],
            'recommendations': []
        }
        
        for index in collection.list_indexes():
            result['indexes'].append({
                'name': index['name'],
                'keys': dict(index['key']),
                'unique': index.get('unique', False)
            })
        
        # Check for missing recommended indexes
        recommended = cls.RECOMMENDED_INDEXES.get(collection_name, [])
        existing_names = {idx['name'] for idx in result['indexes']}
        
        for rec in recommended:
            if rec['name'] not in existing_names:
                result['recommendations'].append({
                    'action': 'create',
                    'index': rec
                })
        
        return result
