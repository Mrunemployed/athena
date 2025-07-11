from fastapi import APIRouter, HTTPException

from app.core.metrics import metrics_cache, compute_tvl
from app.medusa_core.token_map import TOKEN_MAP

router = APIRouter()


@router.get("/metrics/summary")
def metrics_summary():
    """Return cached metrics summary."""
    return metrics_cache


@router.get("/metrics/dca/{job_id}")
def metrics_job(job_id: str):
    job_metrics = metrics_cache.get("per_job", {}).get(job_id)
    if job_metrics is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job_metrics


@router.get("/metrics/tvl")
def metrics_tvl():
    """Return total value locked across tracked tokens."""
    total = compute_tvl(TOKEN_MAP)
    return {"tvl": total}
