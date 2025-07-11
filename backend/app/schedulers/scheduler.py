import logging
from typing import Any, Callable, Dict

from app.db.db import db, scheduler

logger = logging.getLogger(__name__)


def register_cron_job(job_doc: Dict[str, Any], callback: Callable[[str], None]) -> str | None:
    """Add a cron job to APS and store the APS id back to MongoDB."""
    if scheduler is None or db is None:
        return None
    try:
        cron_parts = job_doc.get("cron", "").split()
        cron_keys = ["minute", "hour", "day", "month", "day_of_week"]
        cron_kwargs = {k: v for k, v in zip(cron_keys, cron_parts)}
        aps_job = scheduler.add_job(
            callback,
            trigger="cron",
            args=[str(job_doc["_id"])],
            **cron_kwargs,
        )
        db.dca_jobs.update_one(
            {"_id": job_doc["_id"]},
            {"$set": {"aps_id": aps_job.id, "next_run": aps_job.next_run_time, "status": "active"}},
        )
        return aps_job.id
    except Exception as exc:
        logger.error("Failed to register cron job: %s", exc)
    return None


def rehydrate_on_startup(callback: Callable[[str], None]):
    """Re-add all active jobs from MongoDB to APS scheduler on startup."""
    if scheduler is None or db is None:
        return
    for job_doc in db.dca_jobs.find({"status": "active"}):
        register_cron_job(job_doc, callback)


def pause_job(job_id: str) -> bool:
    if scheduler is None:
        return False
    try:
        scheduler.pause_job(job_id)
        return True
    except Exception as exc:
        logger.error("Pause job failed: %s", exc)
    return False


def resume_job(job_id: str) -> bool:
    if scheduler is None:
        return False
    try:
        scheduler.resume_job(job_id)
        return True
    except Exception as exc:
        logger.error("Resume job failed: %s", exc)
    return False


def remove_job(job_id: str) -> bool:
    if scheduler is None:
        return False
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception as exc:
        logger.error("Remove job failed: %s", exc)
    return False

