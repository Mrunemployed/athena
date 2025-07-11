import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from app.db.db import db, scheduler
from app.medusa_core.token_map import _REMOTE_MAP, load_token_map

def log_event(event: Dict[str, Any]) -> None:
    if db is None:
        return
    db.events.insert_one({
        **event,
        "timestamp": datetime.utcnow()
    })

logger = logging.getLogger(__name__)

metrics_cache: Dict[str, Any] = {}


def compute_tvl(token_map: Dict[int, Dict[str, str]]) -> float:
    """Compute total value locked based on active DCA jobs."""
    if db is None:
        return 0.0
    tracked = {s for m in token_map.values() for s in m.keys()}
    total = 0.0
    for job in db.dca_jobs.find({"status": {"$in": ["active", "paused"]}}):
        basket = db.baskets.find_one({"_id": job.get("basket_id")})
        if not basket:
            continue
        budget = float(job.get("budget_per_tick", 0))
        for coin in basket.get("coins", []):
            if coin.get("symbol") not in tracked:
                continue
            weight = float(coin.get("weight", 0)) / 100.0
            total += budget * weight
    return total


def compute_metrics() -> None:
    """Calculate DCA metrics and store in-memory."""
    if db is None:
        return

    now = datetime.utcnow()
    start = now - timedelta(hours=24)

    running = db.dca_jobs.count_documents({"status": "active"})

    events_cursor = db.events.find(
        {"type": "dca_tick", "timestamp": {"$gte": start}}
    )
    events = list(events_cursor)
    total = len(events)
    success = sum(1 for e in events if e.get("success"))
    success_rate = (success / total) * 100 if total else 0.0
    total_latency = sum(float(e.get("latency", 0)) for e in events)
    avg_latency = (total_latency / total) if total else 0.0

    per_job: Dict[str, Dict[str, Any]] = {}
    for e in events:
        jid = str(e.get("job_id"))
        stat = per_job.setdefault(jid, {"total": 0, "success": 0, "failure": 0, "avg_latency": 0.0})
        stat["total"] += 1
        stat["avg_latency"] += float(e.get("latency", 0))
        if e.get("success"):
            stat["success"] += 1
        else:
            stat["failure"] += 1

    for stat in per_job.values():
        if stat["total"]:
            stat["avg_latency"] /= stat["total"]

    # Ensure token map is loaded
    if not _REMOTE_MAP:
        load_token_map()
    tvl = compute_tvl(_REMOTE_MAP)
    metrics_cache.update({
        "timestamp": now.isoformat(),
        "running_jobs": running,
        "success_rate_24h": success_rate,
        "avg_latency_24h": avg_latency,
        "per_job": per_job,
        "tvl": tvl,
    })
    logger.debug("Metrics updated")


def start_metrics_collection() -> None:
    """Begin periodic metrics computation."""
    compute_metrics()
    if scheduler:
        scheduler.add_job(
            compute_metrics,
            "interval",
            seconds=30,
            id="metrics_collection",
            replace_existing=True,
        )
