"""
Base models for database tables
Provides common functionality for all models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from typing import Dict, Any

# Create base class
Base = declarative_base()


class TimestampMixin:
    """
    Mixin for automatic timestamp tracking
    Adds created_at and updated_at columns to any model
    """
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp when record was created"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class BaseModel(Base, TimestampMixin):
    """
    Base model for all database tables
    
    Features:
    - Auto-incrementing ID
    - Automatic timestamps (created_at, updated_at)
    - to_dict() method for serialization
    - __repr__() for debugging
    """
    
    __abstract__ = True  # This tells SQLAlchemy not to create a table for this class
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name"""
        return cls.__name__.lower()
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        return result
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        class_name = self.__class__.__name__
        return f"<{class_name}(id={self.id})>"
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model attributes from dictionary
        
        Args:
            data: Dictionary with attribute names and values
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
