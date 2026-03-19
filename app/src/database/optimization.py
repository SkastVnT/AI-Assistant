"""
Database Optimization Module
MongoDB indexes, query optimization, and connection pooling
"""

import logging
from typing import Dict, List, Any, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)


# ============================================================================
# INDEX DEFINITIONS
# ============================================================================

MONGODB_INDEXES = {
    "conversations": [
        {
            "keys": [("user_id", ASCENDING), ("created_at", DESCENDING)],
            "name": "idx_user_created",
            "background": True
        },
        {
            "keys": [("session_id", ASCENDING)],
            "name": "idx_session",
            "unique": True,
            "background": True
        },
        {
            "keys": [("updated_at", DESCENDING)],
            "name": "idx_updated",
            "background": True
        },
        {
            "keys": [("is_deleted", ASCENDING), ("user_id", ASCENDING)],
            "name": "idx_deleted_user",
            "background": True
        }
    ],
    "messages": [
        {
            "keys": [("conversation_id", ASCENDING), ("created_at", ASCENDING)],
            "name": "idx_conv_created",
            "background": True
        },
        {
            "keys": [("role", ASCENDING), ("conversation_id", ASCENDING)],
            "name": "idx_role_conv",
            "background": True
        }
    ],
    "memories": [
        {
            "keys": [("user_id", ASCENDING), ("type", ASCENDING)],
            "name": "idx_user_type",
            "background": True
        },
        {
            "keys": [("content", TEXT)],
            "name": "idx_content_text",
            "background": True
        },
        {
            "keys": [("importance", DESCENDING)],
            "name": "idx_importance",
            "background": True
        },
        {
            "keys": [("expires_at", ASCENDING)],
            "name": "idx_expires",
            "expireAfterSeconds": 0,  # TTL index
            "background": True
        }
    ],
    "learning_data": [
        {
            "keys": [("source", ASCENDING), ("quality_score", DESCENDING)],
            "name": "idx_source_quality",
            "background": True
        },
        {
            "keys": [("created_at", DESCENDING)],
            "name": "idx_created",
            "background": True
        },
        {
            "keys": [("question", TEXT), ("answer", TEXT)],
            "name": "idx_qa_text",
            "background": True
        }
    ],
    "api_keys": [
        {
            "keys": [("key_hash", ASCENDING)],
            "name": "idx_key_hash",
            "unique": True,
            "background": True
        },
        {
            "keys": [("expires_at", ASCENDING)],
            "name": "idx_expires",
            "expireAfterSeconds": 0,
            "background": True
        },
        {
            "keys": [("is_active", ASCENDING)],
            "name": "idx_active",
            "background": True
        }
    ],
    "rate_limits": [
        {
            "keys": [("key", ASCENDING)],
            "name": "idx_key",
            "unique": True,
            "background": True
        },
        {
            "keys": [("expires_at", ASCENDING)],
            "name": "idx_expires",
            "expireAfterSeconds": 0,
            "background": True
        }
    ],
    "cache": [
        {
            "keys": [("cache_key", ASCENDING)],
            "name": "idx_cache_key",
            "unique": True,
            "background": True
        },
        {
            "keys": [("expires_at", ASCENDING)],
            "name": "idx_expires",
            "expireAfterSeconds": 0,
            "background": True
        }
    ]
}


class DatabaseOptimizer:
    """
    Database optimization utilities for MongoDB.
    """
    
    def __init__(self, client: MongoClient, db_name: str = "ai_assistant"):
        self.client = client
        self.db: Database = client[db_name]
    
    def create_indexes(self, collections: List[str] = None) -> Dict[str, List[str]]:
        """
        Create indexes for specified collections or all defined collections.
        
        Args:
            collections: List of collection names, or None for all
        
        Returns:
            Dictionary of collection -> created index names
        """
        results = {}
        target_collections = collections or list(MONGODB_INDEXES.keys())
        
        for coll_name in target_collections:
            if coll_name not in MONGODB_INDEXES:
                logger.warning(f"No index definition for collection: {coll_name}")
                continue
            
            collection = self.db[coll_name]
            created = []
            
            for index_def in MONGODB_INDEXES[coll_name]:
                try:
                    keys = index_def.pop("keys")
                    name = index_def.get("name", "unnamed_index")
                    
                    # Create index
                    collection.create_index(keys, **index_def)
                    created.append(name)
                    logger.info(f"Created index {name} on {coll_name}")
                    
                    # Restore keys for future calls
                    index_def["keys"] = keys
                    
                except Exception as e:
                    logger.error(f"Failed to create index on {coll_name}: {e}")
                    index_def["keys"] = keys  # Restore keys
            
            results[coll_name] = created
        
        return results
    
    def analyze_indexes(self, collection_name: str) -> Dict[str, Any]:
        """
        Analyze index usage for a collection.
        
        Args:
            collection_name: Name of collection to analyze
        
        Returns:
            Index statistics
        """
        collection = self.db[collection_name]
        
        # Get existing indexes
        indexes = list(collection.list_indexes())
        
        # Get index stats if available
        try:
            stats = self.db.command("indexStats", collection_name)
        except:
            stats = None
        
        return {
            "collection": collection_name,
            "index_count": len(indexes),
            "indexes": [
                {
                    "name": idx.get("name"),
                    "keys": dict(idx.get("key", {})),
                    "unique": idx.get("unique", False),
                    "sparse": idx.get("sparse", False)
                }
                for idx in indexes
            ],
            "stats": stats
        }
    
    def optimize_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        Optimize a collection (compact, reindex).
        
        Args:
            collection_name: Name of collection
        
        Returns:
            Optimization results
        """
        results = {}
        
        try:
            # Compact collection (requires admin privileges)
            compact_result = self.db.command("compact", collection_name)
            results["compact"] = compact_result
        except Exception as e:
            results["compact_error"] = str(e)
        
        try:
            # Reindex collection
            reindex_result = self.db[collection_name].reindex()
            results["reindex"] = reindex_result
        except Exception as e:
            results["reindex_error"] = str(e)
        
        return results
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Args:
            collection_name: Name of collection
        
        Returns:
            Collection statistics
        """
        try:
            stats = self.db.command("collStats", collection_name)
            return {
                "collection": collection_name,
                "count": stats.get("count", 0),
                "size_bytes": stats.get("size", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "index_count": stats.get("nindexes", 0),
                "total_index_size": stats.get("totalIndexSize", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return {"error": str(e)}


# ============================================================================
# QUERY OPTIMIZATION HELPERS
# ============================================================================

class QueryBuilder:
    """
    Helper for building optimized MongoDB queries.
    """
    
    @staticmethod
    def paginate(query: Dict, page: int = 1, per_page: int = 20, 
                 sort_field: str = "created_at", sort_order: int = DESCENDING) -> Dict:
        """
        Add pagination to a query result.
        
        Args:
            query: Base query dictionary
            page: Page number (1-indexed)
            per_page: Items per page
            sort_field: Field to sort by
            sort_order: ASCENDING or DESCENDING
        
        Returns:
            Query options dictionary
        """
        skip = (page - 1) * per_page
        
        return {
            "filter": query,
            "skip": skip,
            "limit": per_page,
            "sort": [(sort_field, sort_order)]
        }
    
    @staticmethod
    def project(fields: List[str], exclude_id: bool = False) -> Dict:
        """
        Create projection dictionary.
        
        Args:
            fields: Fields to include
            exclude_id: Whether to exclude _id field
        
        Returns:
            Projection dictionary
        """
        projection = {field: 1 for field in fields}
        if exclude_id:
            projection["_id"] = 0
        return projection
    
    @staticmethod
    def text_search(text: str, score_field: str = "score") -> Dict:
        """
        Create text search query.
        
        Args:
            text: Search text
            score_field: Field name for relevance score
        
        Returns:
            Query and projection for text search
        """
        return {
            "query": {"$text": {"$search": text}},
            "projection": {score_field: {"$meta": "textScore"}},
            "sort": [(score_field, {"$meta": "textScore"})]
        }
    
    @staticmethod
    def date_range(field: str, start_date=None, end_date=None) -> Dict:
        """
        Create date range query.
        
        Args:
            field: Date field name
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
        
        Returns:
            Query dictionary
        """
        query = {}
        
        if start_date and end_date:
            query[field] = {"$gte": start_date, "$lt": end_date}
        elif start_date:
            query[field] = {"$gte": start_date}
        elif end_date:
            query[field] = {"$lt": end_date}
        
        return query


# ============================================================================
# CONNECTION POOL MANAGER
# ============================================================================

class MongoDBConnectionManager:
    """
    MongoDB connection manager with pooling.
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    def connect(self, uri: str, 
                max_pool_size: int = 50,
                min_pool_size: int = 10,
                max_idle_time_ms: int = 30000,
                wait_queue_timeout_ms: int = 5000,
                server_selection_timeout_ms: int = 5000) -> MongoClient:
        """
        Create or get MongoDB connection with pooling.
        
        Args:
            uri: MongoDB connection URI
            max_pool_size: Maximum connections in pool
            min_pool_size: Minimum connections to maintain
            max_idle_time_ms: Max time connection can be idle
            wait_queue_timeout_ms: Timeout for waiting for connection
            server_selection_timeout_ms: Timeout for server selection
        
        Returns:
            MongoClient instance
        """
        if self._client is None:
            self._client = MongoClient(
                uri,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                maxIdleTimeMS=max_idle_time_ms,
                waitQueueTimeoutMS=wait_queue_timeout_ms,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                retryWrites=True,
                retryReads=True
            )
            logger.info(f"MongoDB connected with pool size {min_pool_size}-{max_pool_size}")
        
        return self._client
    
    def get_client(self) -> Optional[MongoClient]:
        """Get current client instance."""
        return self._client
    
    def close(self):
        """Close connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check connection health.
        
        Returns:
            Health status dictionary
        """
        if not self._client:
            return {"status": "disconnected"}
        
        try:
            # Ping server
            self._client.admin.command("ping")
            
            # Get server info
            info = self._client.server_info()
            
            return {
                "status": "connected",
                "version": info.get("version"),
                "uptime": info.get("uptime")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Singleton instance
mongodb_manager = MongoDBConnectionManager()
