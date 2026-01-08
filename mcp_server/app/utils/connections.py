"""
Database Connection Utilities for PanKB MCP Server
"""
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from app.config import Config

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB Client Singleton"""

    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        """Establish MongoDB connection to PanKB data"""
        try:
            uri = Config.get_pankb_mongodb_uri()
            self._client = MongoClient(uri)
            self._db = self._client[Config.MONGODB_DB_NAME]
            # Test connection
            self._client.server_info()
            logger.info(f"Connected to PanKB MongoDB: {Config.MONGODB_DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to PanKB MongoDB: {e}")
            raise

    @property
    def db(self) -> Database:
        """Get database instance"""
        if self._db is None:
            self._connect()
        return self._db

    def get_collection(self, collection_name: str) -> Collection:
        """Get collection by name"""
        return self.db[collection_name]

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Singleton instance
mongo_client = MongoDBClient()
