import os
import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_db(url: str | None = None):
    """Return a MongoDB database connection or None on failure."""
    mongo_url = url or os.getenv("MONGO_URL", "mongodb://localhost:27017")
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        # logger.info("MongoDB connected")
        return client.medusa
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)
    return None


def insert_one_safe(collection: Collection | None, document: Dict[str, Any]):
    """Insert a document if the collection is available."""
    if collection is None:
        return None
    try:
        return collection.insert_one(document)
    except Exception as exc:
        logger.error("Insert failed: %s", exc)
    return None


def update_one_safe(collection: Collection | None, query: Dict[str, Any], update: Dict[str, Any]):
    """Update a document if the collection is available."""
    if collection is None:
        return None
    try:
        return collection.update_one(query, update)
    except Exception as exc:
        logger.error("Update failed: %s", exc)
    return None
