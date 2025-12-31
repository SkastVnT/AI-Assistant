"""
Base Repository

Generic CRUD repository with MongoDB support.
"""

import logging
from typing import Dict, Any, List, Optional, TypeVar, Generic
from datetime import datetime
from abc import ABC, abstractmethod
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Dict[str, Any])


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository with generic CRUD operations.
    
    Provides:
    - CRUD methods (create, read, update, delete)
    - Pagination support
    - Query building
    - Error handling
    """
    
    def __init__(self, db: Database):
        """
        Initialize repository with database connection.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self._collection: Optional[Collection] = None
    
    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Return the collection name for this repository"""
        pass
    
    @property
    def collection(self) -> Collection:
        """Get the MongoDB collection"""
        if self._collection is None:
            self._collection = self.db[self.collection_name]
        return self._collection
    
    # =========================================================================
    # CREATE Operations
    # =========================================================================
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            data: Document data to insert
            
        Returns:
            Inserted document with _id
        """
        try:
            # Add timestamps if not present
            now = datetime.utcnow()
            if 'created_at' not in data:
                data['created_at'] = now
            if 'updated_at' not in data:
                data['updated_at'] = now
            
            result = self.collection.insert_one(data)
            data['_id'] = result.inserted_id
            
            logger.debug(f"Created document in {self.collection_name}: {result.inserted_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise
    
    def create_many(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple documents.
        
        Args:
            documents: List of documents to insert
            
        Returns:
            List of inserted documents with _ids
        """
        try:
            now = datetime.utcnow()
            for doc in documents:
                if 'created_at' not in doc:
                    doc['created_at'] = now
                if 'updated_at' not in doc:
                    doc['updated_at'] = now
            
            result = self.collection.insert_many(documents)
            
            for doc, inserted_id in zip(documents, result.inserted_ids):
                doc['_id'] = inserted_id
            
            logger.debug(f"Created {len(documents)} documents in {self.collection_name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error creating documents in {self.collection_name}: {e}")
            raise
    
    # =========================================================================
    # READ Operations
    # =========================================================================
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID (string or ObjectId)
            
        Returns:
            Document dict or None if not found
        """
        try:
            # Handle both string and ObjectId
            query_id = self._parse_id(doc_id)
            return self.collection.find_one({'_id': query_id})
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id} from {self.collection_name}: {e}")
            return None
    
    def get_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get a single document matching query.
        
        Args:
            query: MongoDB query dict
            
        Returns:
            Document dict or None
        """
        try:
            return self.collection.find_one(query)
        except Exception as e:
            logger.error(f"Error querying {self.collection_name}: {e}")
            return None
    
    def get_many(
        self,
        query: Dict[str, Any] = None,
        sort: List[tuple] = None,
        skip: int = 0,
        limit: int = 100,
        projection: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get multiple documents with pagination.
        
        Args:
            query: MongoDB query dict
            sort: List of (field, direction) tuples
            skip: Number of documents to skip
            limit: Maximum documents to return
            projection: Fields to include/exclude
            
        Returns:
            List of documents
        """
        try:
            query = query or {}
            cursor = self.collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            cursor = cursor.skip(skip).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error querying {self.collection_name}: {e}")
            return []
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count documents matching query.
        
        Args:
            query: MongoDB query dict
            
        Returns:
            Count of matching documents
        """
        try:
            query = query or {}
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting in {self.collection_name}: {e}")
            return 0
    
    def exists(self, query: Dict[str, Any]) -> bool:
        """
        Check if any document matches query.
        
        Args:
            query: MongoDB query dict
            
        Returns:
            True if at least one document matches
        """
        return self.count(query) > 0
    
    # =========================================================================
    # UPDATE Operations
    # =========================================================================
    
    def update(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a document by ID.
        
        Args:
            doc_id: Document ID
            updates: Fields to update
            
        Returns:
            Updated document or None
        """
        try:
            query_id = self._parse_id(doc_id)
            
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow()
            
            result = self.collection.find_one_and_update(
                {'_id': query_id},
                {'$set': updates},
                return_document=True
            )
            
            logger.debug(f"Updated document {doc_id} in {self.collection_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id} in {self.collection_name}: {e}")
            raise
    
    def update_many(self, query: Dict[str, Any], updates: Dict[str, Any]) -> int:
        """
        Update multiple documents.
        
        Args:
            query: MongoDB query dict
            updates: Fields to update
            
        Returns:
            Count of modified documents
        """
        try:
            updates['updated_at'] = datetime.utcnow()
            
            result = self.collection.update_many(query, {'$set': updates})
            
            logger.debug(f"Updated {result.modified_count} documents in {self.collection_name}")
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error updating documents in {self.collection_name}: {e}")
            raise
    
    def upsert(self, query: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update or insert a document.
        
        Args:
            query: Query to find existing document
            data: Data to set
            
        Returns:
            Upserted document
        """
        try:
            now = datetime.utcnow()
            data['updated_at'] = now
            
            result = self.collection.find_one_and_update(
                query,
                {
                    '$set': data,
                    '$setOnInsert': {'created_at': now}
                },
                upsert=True,
                return_document=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error upserting in {self.collection_name}: {e}")
            raise
    
    # =========================================================================
    # DELETE Operations
    # =========================================================================
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            query_id = self._parse_id(doc_id)
            result = self.collection.delete_one({'_id': query_id})
            
            deleted = result.deleted_count > 0
            if deleted:
                logger.debug(f"Deleted document {doc_id} from {self.collection_name}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} from {self.collection_name}: {e}")
            raise
    
    def delete_many(self, query: Dict[str, Any]) -> int:
        """
        Delete multiple documents.
        
        Args:
            query: MongoDB query dict
            
        Returns:
            Count of deleted documents
        """
        try:
            result = self.collection.delete_many(query)
            
            logger.debug(f"Deleted {result.deleted_count} documents from {self.collection_name}")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting documents from {self.collection_name}: {e}")
            raise
    
    def soft_delete(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Soft delete a document (mark as deleted).
        
        Args:
            doc_id: Document ID
            
        Returns:
            Updated document
        """
        return self.update(doc_id, {
            'is_deleted': True,
            'deleted_at': datetime.utcnow()
        })
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _parse_id(self, doc_id: str) -> Any:
        """
        Parse document ID to appropriate type.
        
        Args:
            doc_id: Document ID string
            
        Returns:
            ObjectId or string depending on format
        """
        if isinstance(doc_id, ObjectId):
            return doc_id
        
        # Try to parse as ObjectId
        try:
            if len(doc_id) == 24:
                return ObjectId(doc_id)
        except:
            pass
        
        # Return as string (for UUID-style IDs)
        return doc_id
    
    def paginate(
        self,
        query: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 20,
        sort: List[tuple] = None
    ) -> Dict[str, Any]:
        """
        Get paginated results.
        
        Args:
            query: MongoDB query dict
            page: Page number (1-indexed)
            per_page: Items per page
            sort: Sort order
            
        Returns:
            Dict with items, total, pages, current_page
        """
        query = query or {}
        skip = (page - 1) * per_page
        
        items = self.get_many(query, sort=sort, skip=skip, limit=per_page)
        total = self.count(query)
        pages = (total + per_page - 1) // per_page
        
        return {
            'items': items,
            'total': total,
            'pages': pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': page < pages,
            'has_prev': page > 1
        }
    
    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run an aggregation pipeline.
        
        Args:
            pipeline: MongoDB aggregation pipeline
            
        Returns:
            Aggregation results
        """
        try:
            return list(self.collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error in aggregation on {self.collection_name}: {e}")
            return []
