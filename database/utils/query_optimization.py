"""
Database query optimization utilities.

Provides tools and patterns for optimizing database queries:
- Eager loading to prevent N+1 queries
- Bulk operations for batch inserts/updates
- Query result caching
- Query analysis and profiling
"""

import logging
from typing import List, Type, Any, Callable
from functools import wraps
from sqlalchemy.orm import Session, joinedload, selectinload, subqueryload
from sqlalchemy import inspect

logger = logging.getLogger(__name__)


# ============================================================
# EAGER LOADING HELPERS
# ============================================================

def with_relationships(query, model: Type, relationships: List[str], strategy: str = 'joined'):
    """
    Add eager loading for specified relationships
    
    Args:
        query: SQLAlchemy query
        model: Model class
        relationships: List of relationship names to load
        strategy: Loading strategy ('joined', 'selectin', 'subquery')
    
    Returns:
        Query with eager loading applied
    
    Usage:
        query = session.query(Conversation)
        query = with_relationships(query, Conversation, ['messages', 'user'])
    """
    strategy_map = {
        'joined': joinedload,
        'selectin': selectinload,
        'subquery': subqueryload
    }
    
    loader = strategy_map.get(strategy, joinedload)
    
    for rel_name in relationships:
        if hasattr(model, rel_name):
            query = query.options(loader(getattr(model, rel_name)))
        else:
            logger.warning(f"Relationship '{rel_name}' not found on {model.__name__}")
    
    return query


def load_with_messages(session: Session, model: Type, model_id: Any, limit: int = None):
    """
    Load conversation with messages using eager loading
    
    Args:
        session: Database session
        model: Model class (e.g., Conversation)
        model_id: ID of the model instance
        limit: Optional limit for messages
    
    Returns:
        Model instance with messages loaded
    """
    query = session.query(model).filter_by(id=model_id)
    
    # Use selectinload for better performance with large collections
    query = query.options(selectinload(model.messages))
    
    result = query.first()
    
    # If limit is specified, truncate messages
    if result and limit and hasattr(result, 'messages'):
        result.messages = result.messages[:limit]
    
    return result


# ============================================================
# BULK OPERATIONS
# ============================================================

class BulkOperations:
    """Helper class for bulk database operations"""
    
    @staticmethod
    def bulk_insert_dicts(session: Session, model: Type, data: List[dict]) -> int:
        """
        Bulk insert from list of dictionaries
        
        Args:
            session: Database session
            model: Model class
            data: List of dictionaries with model data
        
        Returns:
            Number of rows inserted
        
        Usage:
            messages = [
                {'conversation_id': 1, 'role': 'user', 'content': 'Hello'},
                {'conversation_id': 1, 'role': 'assistant', 'content': 'Hi!'}
            ]
            count = BulkOperations.bulk_insert_dicts(session, Message, messages)
        """
        if not data:
            return 0
        
        try:
            session.bulk_insert_mappings(model, data)
            session.flush()
            logger.info(f"Bulk inserted {len(data)} {model.__name__} records")
            return len(data)
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise
    
    @staticmethod
    def bulk_update_dicts(session: Session, model: Type, data: List[dict]) -> int:
        """
        Bulk update from list of dictionaries (must include 'id' field)
        
        Args:
            session: Database session
            model: Model class
            data: List of dictionaries with model data (must include 'id')
        
        Returns:
            Number of rows updated
        """
        if not data:
            return 0
        
        try:
            session.bulk_update_mappings(model, data)
            session.flush()
            logger.info(f"Bulk updated {len(data)} {model.__name__} records")
            return len(data)
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            raise
    
    @staticmethod
    def bulk_insert_objects(session: Session, objects: List[Any]) -> int:
        """
        Bulk insert model objects
        
        Args:
            session: Database session
            objects: List of model instances
        
        Returns:
            Number of objects inserted
        """
        if not objects:
            return 0
        
        try:
            session.bulk_save_objects(objects)
            session.flush()
            logger.info(f"Bulk inserted {len(objects)} objects")
            return len(objects)
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise


# ============================================================
# QUERY RESULT CACHING
# ============================================================

def cache_query_result(ttl: int = 3600):
    """
    Decorator to cache query results
    
    Args:
        ttl: Time to live in seconds
    
    Usage:
        @cache_query_result(ttl=3600)
        def get_user_count(session, user_id):
            return session.query(Conversation).filter_by(user_id=user_id).count()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get from cache
            try:
                from database.utils.cache import cache_client
                if cache_client:
                    import hashlib
                    import json
                    
                    # Generate cache key from function name and arguments
                    key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                    cache_key = f"query:{hashlib.md5(key_data.encode()).hexdigest()}"
                    
                    # Check cache
                    cached = cache_client.get(cache_key)
                    if cached:
                        logger.debug(f"Cache HIT: {func.__name__}")
                        return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Execute query
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                from database.utils.cache import cache_client
                if cache_client and result is not None:
                    cache_client.set(cache_key, json.dumps(result, default=str), ex=ttl)
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator


# ============================================================
# QUERY ANALYSIS
# ============================================================

def analyze_query(query) -> dict:
    """
    Analyze query for potential performance issues
    
    Args:
        query: SQLAlchemy query object
    
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        'has_eager_loading': False,
        'joins': [],
        'filters': [],
        'warnings': []
    }
    
    try:
        # Get query context
        context = query._compile_context()
        
        # Check for eager loading
        if hasattr(query, '_with_options'):
            analysis['has_eager_loading'] = True
        
        # Analyze query structure
        statement = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        
        # Check for potential N+1 queries
        if 'JOIN' not in statement.upper():
            analysis['warnings'].append("No JOINs found - potential N+1 query issue")
        
        # Check for missing WHERE clause
        if 'WHERE' not in statement.upper():
            analysis['warnings'].append("No WHERE clause - may return all records")
        
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        analysis['error'] = str(e)
    
    return analysis


def log_query_plan(session: Session, query) -> str:
    """
    Get and log PostgreSQL query execution plan
    
    Args:
        session: Database session
        query: SQLAlchemy query
    
    Returns:
        Query plan as string
    """
    try:
        # Get query SQL
        sql = str(query.statement.compile(
            dialect=session.bind.dialect,
            compile_kwargs={"literal_binds": True}
        ))
        
        # Get EXPLAIN plan
        result = session.execute(f"EXPLAIN ANALYZE {sql}")
        plan = '\n'.join([row[0] for row in result])
        
        logger.info(f"Query Plan:\n{plan}")
        return plan
    
    except Exception as e:
        logger.error(f"Failed to get query plan: {e}")
        return ""


# ============================================================
# OPTIMIZED QUERY PATTERNS
# ============================================================

class OptimizedQueries:
    """Collection of optimized query patterns"""
    
    @staticmethod
    def get_with_related(session: Session, model: Type, model_id: Any, 
                        relationships: List[str]) -> Any:
        """
        Get model with all relationships loaded in single query
        
        Args:
            session: Database session
            model: Model class
            model_id: ID of the model
            relationships: List of relationship names
        
        Returns:
            Model instance with relationships loaded
        """
        query = session.query(model).filter_by(id=model_id)
        query = with_relationships(query, model, relationships, strategy='selectin')
        return query.first()
    
    @staticmethod
    def paginate_with_related(session: Session, model: Type, 
                             relationships: List[str],
                             filters: dict = None,
                             page: int = 1, 
                             per_page: int = 20) -> dict:
        """
        Paginate query with eager loading
        
        Args:
            session: Database session
            model: Model class
            relationships: List of relationship names to load
            filters: Dictionary of filters
            page: Page number (1-indexed)
            per_page: Items per page
        
        Returns:
            Dictionary with items, total, page info
        """
        query = session.query(model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(model, key):
                    query = query.filter(getattr(model, key) == value)
        
        # Add eager loading
        query = with_relationships(query, model, relationships, strategy='selectin')
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }


# ============================================================
# BATCH PROCESSING
# ============================================================

def process_in_batches(session: Session, query, batch_size: int = 1000,
                      callback: Callable = None) -> int:
    """
    Process large result sets in batches to avoid memory issues
    
    Args:
        session: Database session
        query: SQLAlchemy query
        batch_size: Number of records per batch
        callback: Function to call for each batch
    
    Returns:
        Total number of records processed
    
    Usage:
        def process_batch(batch):
            for item in batch:
                # Process item
                pass
        
        query = session.query(Message)
        process_in_batches(session, query, batch_size=1000, callback=process_batch)
    """
    total = 0
    offset = 0
    
    while True:
        batch = query.offset(offset).limit(batch_size).all()
        
        if not batch:
            break
        
        if callback:
            callback(batch)
        
        total += len(batch)
        offset += batch_size
        
        # Clear session to avoid memory buildup
        session.expire_all()
        
        logger.debug(f"Processed batch: {offset} records")
    
    logger.info(f"Total processed: {total} records")
    return total


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    'with_relationships',
    'load_with_messages',
    'BulkOperations',
    'cache_query_result',
    'analyze_query',
    'log_query_plan',
    'OptimizedQueries',
    'process_in_batches'
]
