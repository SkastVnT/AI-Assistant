"""
Base Repository

Provides generic CRUD operations for all database models
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models.base import BaseModel
from database.utils.engine import get_session

logger = logging.getLogger(__name__)

# Generic type for models
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations
    
    Provides:
    - get: Get single entity by ID
    - get_all: Get all entities with pagination
    - get_by_ids: Get multiple entities by IDs
    - create: Create new entity
    - update: Update existing entity
    - delete: Delete entity (soft or hard)
    - exists: Check if entity exists
    - count: Count entities with filters
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self):
                super().__init__(User)
        
        repo = UserRepository()
        user = repo.get(session, user_id)
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with model class
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.model_name = model.__name__
    
    def get(self, session: Session, entity_id: Any) -> Optional[ModelType]:
        """
        Get entity by ID
        
        Args:
            session: Database session
            entity_id: Entity primary key
            
        Returns:
            Entity or None if not found
        """
        try:
            stmt = select(self.model).where(self.model.id == entity_id)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_name} {entity_id}: {e}")
            return None
    
    def get_all(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        desc: bool = False
    ) -> List[ModelType]:
        """
        Get all entities with pagination and filters
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value filters
            order_by: Field name to order by
            desc: Sort in descending order
            
        Returns:
            List of entities
        """
        try:
            stmt = select(self.model)
            
            # Apply filters
            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        conditions.append(getattr(self.model, field) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                stmt = stmt.order_by(order_field.desc() if desc else order_field)
            
            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model_name}: {e}")
            return []
    
    def get_by_ids(
        self,
        session: Session,
        entity_ids: List[Any]
    ) -> List[ModelType]:
        """
        Get multiple entities by IDs
        
        Args:
            session: Database session
            entity_ids: List of entity primary keys
            
        Returns:
            List of entities
        """
        try:
            if not entity_ids:
                return []
            
            stmt = select(self.model).where(self.model.id.in_(entity_ids))
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_name} by IDs: {e}")
            return []
    
    def create(
        self,
        session: Session,
        **kwargs
    ) -> Optional[ModelType]:
        """
        Create new entity
        
        Args:
            session: Database session
            **kwargs: Entity attributes
            
        Returns:
            Created entity or None on error
        """
        try:
            entity = self.model(**kwargs)
            session.add(entity)
            session.flush()  # Get ID without committing
            session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_name}: {e}")
            session.rollback()
            return None
    
    def update(
        self,
        session: Session,
        entity_id: Any,
        **kwargs
    ) -> Optional[ModelType]:
        """
        Update existing entity
        
        Args:
            session: Database session
            entity_id: Entity primary key
            **kwargs: Fields to update
            
        Returns:
            Updated entity or None if not found
        """
        try:
            entity = self.get(session, entity_id)
            if not entity:
                logger.warning(f"{self.model_name} {entity_id} not found for update")
                return None
            
            # Update fields
            for field, value in kwargs.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            session.flush()
            session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model_name} {entity_id}: {e}")
            session.rollback()
            return None
    
    def delete(
        self,
        session: Session,
        entity_id: Any,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete entity (soft or hard delete)
        
        Args:
            session: Database session
            entity_id: Entity primary key
            soft_delete: Use soft delete if model supports it
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            entity = self.get(session, entity_id)
            if not entity:
                logger.warning(f"{self.model_name} {entity_id} not found for delete")
                return False
            
            # Soft delete if supported
            if soft_delete and hasattr(entity, 'is_deleted'):
                entity.is_deleted = True
                session.flush()
            else:
                # Hard delete
                session.delete(entity)
                session.flush()
            
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model_name} {entity_id}: {e}")
            session.rollback()
            return False
    
    def exists(
        self,
        session: Session,
        entity_id: Any
    ) -> bool:
        """
        Check if entity exists
        
        Args:
            session: Database session
            entity_id: Entity primary key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count()).select_from(self.model).where(
                self.model.id == entity_id
            )
            result = session.execute(stmt)
            return result.scalar() > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking {self.model_name} existence: {e}")
            return False
    
    def count(
        self,
        session: Session,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count entities with optional filters
        
        Args:
            session: Database session
            filters: Dictionary of field:value filters
            
        Returns:
            Count of entities
        """
        try:
            stmt = select(func.count()).select_from(self.model)
            
            # Apply filters
            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        conditions.append(getattr(self.model, field) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))
            
            result = session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_name}: {e}")
            return 0
    
    def get_or_create(
        self,
        session: Session,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[ModelType, bool]:
        """
        Get existing entity or create new one
        
        Args:
            session: Database session
            defaults: Default values for creation
            **kwargs: Lookup filters
            
        Returns:
            Tuple of (entity, created) where created is True if new
        """
        try:
            # Try to find existing
            stmt = select(self.model)
            conditions = []
            for field, value in kwargs.items():
                if hasattr(self.model, field):
                    conditions.append(getattr(self.model, field) == value)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            result = session.execute(stmt)
            entity = result.scalar_one_or_none()
            
            if entity:
                return entity, False
            
            # Create new
            create_kwargs = {**kwargs}
            if defaults:
                create_kwargs.update(defaults)
            
            entity = self.create(session, **create_kwargs)
            return entity, True
        except SQLAlchemyError as e:
            logger.error(f"Error in get_or_create for {self.model_name}: {e}")
            session.rollback()
            return None, False
