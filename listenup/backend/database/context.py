"""
Database context manager for Flask application.
Provides database instances without explicit dependency passing.
"""
from flask import g


class DatabaseContext:
    """
    Flask context manager for database instances.
    Works in both request context (controllers) and application context (background threads).
    """
    
    @staticmethod
    def get_mongo_db():
        """
        Get MongoDB database instance from Flask context.
        
        Works in both:
        - Request context (controllers) - uses 'g' for request-local storage
        - Application context (background threads) - direct import
        """
        try:
            # Try request context first (controllers)
            if 'mongo_db' not in g:
                from backend.app import mongo
                g.mongo_db = mongo.db
            return g.mongo_db
        except RuntimeError:
            # No request context - use direct import (application context)
            from backend.app import mongo
            return mongo.db
    
    @staticmethod
    def get_mongo():
        """Get the PyMongo instance from Flask app."""
        from backend.app import mongo
        return mongo