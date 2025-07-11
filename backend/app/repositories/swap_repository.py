import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

from bson import ObjectId
from pymongo.collection import Collection
from pydantic import BaseModel, Field


class Swap(BaseModel):
    """Schema for swap documents."""

    swap_id: Optional[str] = Field(default=None, alias="_id")
    quote: Dict[str, Any]
    chain_id: Optional[int] = None
    status: str = "new"
    tx_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    step_logs: List[Dict[str, Any]] = []


class SwapRepository:
    """Helper class for CRUD operations on the ``swaps`` collection."""

    def __init__(self, db):
        self.collection: Optional[Collection] = None
        if db is not None:
            self.collection = db.get_collection("swaps")
        self.logger = logging.getLogger(__name__)

    def ensure_indexes(self) -> None:
        """Ensure indexes required for the swaps collection exist."""
        if self.collection is None:
            return
        try:
            self.collection.create_index(
                "signatureRequest.hash", unique=True, sparse=True
            )
        except Exception as exc:
            self.logger.error("Failed to create unique index: %s", exc)

    def create(self, data: Dict[str, Any]) -> Optional[str]:
        """Insert a new swap document and return its ID."""
        if self.collection is None:
            return None
        now = datetime.utcnow()
        doc = {
            **data,
            "created_at": data.get("created_at", now),
            "updated_at": data.get("updated_at", now),
        }
        doc.setdefault("status", "new")
        doc.setdefault("step_logs", [])
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get(self, swap_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a swap document by ID."""
        if self.collection is None:
            return None
        try:
            obj_id = ObjectId(swap_id)
        except Exception:
            return None
        return self.collection.find_one({"_id": obj_id})

    def update(self, swap_id: str, fields: Dict[str, Any]) -> bool:
        """Update fields of a swap document."""
        if self.collection is None:
            return False
        try:
            obj_id = ObjectId(swap_id)
        except Exception:
            return False
        fields.setdefault("updated_at", datetime.utcnow())
        result = self.collection.update_one({"_id": obj_id}, {"$set": fields})
        return result.modified_count > 0

    def add_step_log(self, swap_id: str, log: Dict[str, Any]) -> bool:
        """Append a step log to the swap document."""
        if self.collection is None:
            return False
        try:
            obj_id = ObjectId(swap_id)
        except Exception:
            return False
        result = self.collection.update_one(
            {"_id": obj_id},
            {"$push": {"step_logs": log}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    def delete(self, swap_id: str) -> bool:
        """Delete a swap document."""
        if self.collection is None:
            return False
        try:
            obj_id = ObjectId(swap_id)
        except Exception:
            return False
        result = self.collection.delete_one({"_id": obj_id})
        return result.deleted_count > 0
