import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
import redis

logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# MongoDB connection
try:
    _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    _client.admin.command("ping")
    db = _client.medusa
    mongo_connected = True
    logger.info("MongoDB connected")
except Exception as exc:
    logger.error("MongoDB connection failed: %s", exc)
    db = None
    mongo_connected = False

# Redis connection
try:
    redis_client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=5)
    redis_client.ping()
    redis_connected = True
    logger.info("Redis connected")
except Exception as exc:
    logger.error("Redis connection failed: %s", exc)
    redis_client = None
    redis_connected = False

# Scheduler setup
scheduler = None
if mongo_connected:
    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Ensure swap_metrics collection exists and has useful indexes
    try:
        swap_metrics = db.get_collection("swap_metrics")
        swap_metrics.create_index("swap_id")
        swap_metrics.create_index("started_at")
    except Exception as exc:
        logger.error("Failed to initialize swap_metrics collection: %s", exc)
