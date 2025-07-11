from fastapi import APIRouter, HTTPException
import os
import asyncio
from datetime import datetime
import requests
from typing import Dict, Any
from app.utils.error_handling import handle_agent_error

from app.db.db import mongo_connected, redis_connected, scheduler

RELAY_BASE_URL = os.getenv("RELAY_BASE_URL", "https://api.relay.link")

router = APIRouter()

RPC_URL = os.getenv("SEPOLIA_RPC_URL")


async def check_wallet_connector_health() -> Dict[str, Any]:
    project_id = os.getenv("NEXT_PUBLIC_PROJECT_ID")
    status = "ok" if project_id else "error"
    return {"project_id": bool(project_id), "status": status}


async def check_swap_router_health() -> Dict[str, Any]:
    try:
        res = requests.get(f"{RELAY_BASE_URL}/health", timeout=5)
        res.raise_for_status()
        return {"status": "ok"}
    except Exception as exc:
        await handle_agent_error("Health", exc)
        return {"status": "error", "error": str(exc)}


async def check_dca_executor_health() -> Dict[str, Any]:
    scheduler_running = False
    job_count = 0
    if scheduler:
        scheduler_running = scheduler.running
        job_count = len(scheduler.get_jobs())

    result = {
        "mongo_connected": mongo_connected,
        "scheduler_running": scheduler_running,
        "job_count": job_count,
    }
    result["status"] = "ok" if mongo_connected and scheduler_running else "error"
    return result


async def check_analytics_logger_health() -> Dict[str, Any]:
    result = {
        "mongo_connected": mongo_connected,
        "redis_connected": redis_connected,
    }
    result["status"] = "ok" if mongo_connected else "error"
    return result


async def check_agent_health() -> Dict[str, Any]:
    wallet_connector = await check_wallet_connector_health()
    swap_router = await check_swap_router_health()
    dca_executor = await check_dca_executor_health()
    analytics_logger = await check_analytics_logger_health()

    checks = {
        "wallet_connector": wallet_connector,
        "swap_router": swap_router,
        "dca_executor": dca_executor,
        "analytics_logger": analytics_logger,
    }

    overall = "ok" if all(c.get("status") == "ok" for c in checks.values()) else "error"

    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        **checks,
    }

@router.get("/health/zksync")
def health_zksync():
    if not RPC_URL:
        raise HTTPException(status_code=500, detail="SEPOLIA_RPC_URL not configured")
    try:
        res = requests.post(
            RPC_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
            timeout=5,
        )
        if res.status_code == 429:
            raise HTTPException(status_code=503, detail="rpc rate limited")
        res.raise_for_status()
        data = res.json()
        return {"status": "ok", "result": data.get("result")}
    except HTTPException:
        raise
    except Exception as exc:
        asyncio.run(handle_agent_error("Health", exc))
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/health")
async def health_root():
    return await check_agent_health()
