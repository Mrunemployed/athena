from datetime import datetime
from fastapi import APIRouter

from app.db.db import db

router = APIRouter()


@router.get("/events")
def get_events(since: float | None = None):
    if db is None:
        return {"events": []}

    query = {"type": "dca_tick"}
    if since:
        query["timestamp"] = {"$gt": datetime.fromtimestamp(since)}

    events = list(db.events.find(query, {"_id": 0}).sort("timestamp", 1))
    return {"events": events}
