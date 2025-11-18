"""
Base model class for MongoDB operations using Flask context.
Provides Rails-like ActiveRecord pattern without explicit dependency injection.
"""
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum
from backend.database.context import DatabaseContext


class BaseNoSqlModel:
    """
    Base class for MongoDB models that automatically handles database connection
    through Flask context without requiring explicit dependency injection.
    
    Similar to Rails ActiveRecord pattern where models automatically
    have access to the database connection and common CRUD operations.
    """
    
    def __init__(self):
        """Initialize model without requiring database parameter."""
        pass
    
    @property
    def db(self):
        """Get database instance from Flask context automatically."""
        return DatabaseContext.get_mongo_db()
    
    @property 
    def collection(self):
        """
        Get the MongoDB collection for this model.
        Override in subclasses to specify collection name.
        """
        raise NotImplementedError("Subclasses must implement collection property")

    # -------------------------------------------------------------------------
    # Common CRUD operations (Rails-like class methods)
    # -------------------------------------------------------------------------
    
    @classmethod
    def find(cls, doc_id: str) -> Optional[Any]:
        """
        Find a document by its ID and return as model instance.
        Rails-like: JobModel.find(id)
        """
        doc = cls.find_by_id(doc_id)
        if doc:
            # Convert MongoDB doc to model instance
            doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
            return cls._from_doc(doc)
        return None
    
    @classmethod
    def find_by_id(cls, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a raw document by its ID.
        Rails-like: JobModel.find_by_id(id) - returns raw dict
        """
        instance = cls()
        return instance.collection.find_one({"_id": doc_id})

    @classmethod
    def create(cls, model_instance: Any) -> Any:
        """
        Create a new document in MongoDB from a Pydantic model instance.
        Rails-like: JobModel.create(job)
        Sets created_at automatically.
        """
        doc = model_instance.dict()
        
        # Use the model's ID field as MongoDB _id
        id_field = getattr(model_instance, 'job_id', None) or getattr(model_instance, 'id', None)
        if id_field:
            doc["_id"] = id_field
        
        # Set created_at if not already present
        if 'created_at' not in doc:
            doc['created_at'] = datetime.utcnow()
        
        instance = cls()
        instance.collection.insert_one(doc)
        return model_instance

    @classmethod
    def update(cls, doc_id: str, **kwargs) -> bool:
        """
        Update a document by ID using kwargs.
        Rails-like: JobModel.update(id, status=JobStatus.COMPLETE, name="Updated")
        Handles Pydantic enum conversion automatically.
        """
        instance = cls()
        
        # Convert Pydantic enums to their values for MongoDB storage
        processed_data = {}
        for key, value in kwargs.items():
            if isinstance(value, Enum):
                processed_data[key] = value.value
            else:
                processed_data[key] = value
                
        processed_data["updated_at"] = datetime.utcnow()
        
        result = instance.collection.update_one(
            {"_id": doc_id},
            {"$set": processed_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def _from_doc(cls, doc: Dict[str, Any]) -> Any:
        """
        Convert MongoDB document to model instance.
        Override in subclasses to provide proper model instantiation.
        """
        raise NotImplementedError("Subclasses must implement _from_doc method")