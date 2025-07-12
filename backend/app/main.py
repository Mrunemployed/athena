import os
import json
import atexit
from datetime import datetime
import time
import logging
import requests
import asyncio
from decimal import Decimal
from bson import ObjectId
from app.log_config.set_logging import LOGGING_CONFIG
from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from app.models import SwapMetric
from dotenv import load_dotenv
from app.medusa_core.resolve_balance import WalletBalance
from app.medusa_core.relay import (
    get_quote as relay_get_quote,
    execute_route,
    get_route_status,
    approve_token,
)
from app.medusa_core.token_map import resolve_token_address, resolve_token_symbol, CHAIN_IDS, load_token_map
from app.medusa_core.balance import get_token_balance, get_allowance, get_transaction_confirmations
from app.db.db import db, redis_client, scheduler, mongo_connected, redis_connected
from app.utils.error_handling import handle_agent_error
from app.repositories.swap_repository import SwapRepository

import re

def _is_evm_address(address: str) -> bool:
    """Return True if the address looks like an EVM address."""
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", address or ""))


def _is_solana_address(address: str) -> bool:
    """Return True if the address looks like a Solana address."""
    if not isinstance(address, str) or address.startswith("0x"):
        return False
    try:
        import base58
        decoded = base58.b58decode(address)
    except Exception:
        return False
    return len(decoded) == 32


def is_address(address: str) -> bool:
    """Basic non-empty address check."""
    return isinstance(address, str) and len(address) > 0


def is_address_for_chain(address: str, chain_id: int) -> bool:
    """Validate the address format for the given chain."""
    chain_name = CHAIN_IDS.get(chain_id, "").lower()
    if chain_name == "solana":
        return _is_solana_address(address)
    return _is_evm_address(address)


# Load environment variables from .env file
load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.debug("Log level set to %s", LOG_LEVEL)

swap_repo = SwapRepository(db)

app = FastAPI(title="Cross-Chain Swap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import basket, metrics as metrics_router, events as events_router, health as health_router
app.include_router(basket.router)
app.include_router(metrics_router.router)
app.include_router(events_router.router)
app.include_router(health_router.router)



# CHAIN_IDS = {
#     "ethereum": 1,
#     "polygon": 137,
#     "bsc": 56,
#     "arbitrum": 42161,
#     "optimism": 10,
# }

@app.on_event("startup")
def _reload_jobs():
    from app.core.metrics import start_metrics_collection
    from app.db_validator import run_database_validation

    # Run database validation first
    run_database_validation(db)

    # Ensure indexes for swaps collection
    swap_repo.ensure_indexes()

    start_metrics_collection()
    load_token_map()

# Relay API configuration (public endpoints)
RELAY_BASE_URL = os.getenv("RELAY_BASE_URL", "https://api.relay.link")

class SwapRequest(BaseModel):
    user: str
    source_chain: str
    destination_chain: str
    token_in: str
    token_out: str
    amount: str
    receiver: str
    chain_id: int | None = None
    # Address of the wallet that submitted the request. Defaults to ``user``.
    requester: str | None = None
    # Request IDs returned by Relay for each step of the route
    step_request_ids: list[str] | None = None



class SwapTrackRequest(BaseModel):
    swap_id: str | None = None
    endpoint: str
    txHash: str | None = None
    from_wallet: str | None = None
    to_wallet: str | None = None
    token_in: str | None = None
    token_out: str | None = None
    amount: str | float | None = None
    started_at: str | float | None = None


# Scheduler comes from db module

@app.get("/")
def read_root():
    return {"message": "Cross-Chain Swap API"}

@app.post("/swap", summary="Create swap quote")
def create_swap(req: SwapRequest):
    """Proxy to Relay /quote and store the raw quote."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        src_chain = int(req.source_chain)
        dst_chain = int(req.destination_chain)
        chain_id = int(req.chain_id) if req.chain_id is not None else None
    except Exception:
        raise HTTPException(status_code=422, detail="invalid chain ids")
    if not is_address_for_chain(req.user, src_chain) or not is_address_for_chain(req.receiver, dst_chain):
        raise HTTPException(status_code=422, detail="invalid address")
    params = {"originChainId": src_chain, "destinationChainId": dst_chain, "inputToken": resolve_token_address(src_chain, req.token_in), "outputToken": resolve_token_address(dst_chain, req.token_out), "inputAmount": req.amount, "user": req.user, "receiver": req.receiver, "tradeType": "EXACT_INPUT"}
    quote = relay_get_quote(params)
    if not quote:
        raise HTTPException(status_code=502, detail="quote unavailable")
    doc = {
        "user": req.user,
        "src_chain": src_chain,
        "dst_chain": dst_chain,
        "token_in": req.token_in,
        "token_out": req.token_out,
        "amount": req.amount,
        "receiver": req.receiver,
        "quote": quote,
        "status": "new",
    }
    if chain_id is not None:
        doc["chain_id"] = chain_id
    swap_id = swap_repo.create(doc)
    container = quote.get("result") if isinstance(quote.get("result"), dict) else quote
    steps = []
    for step in container.get("steps", []):
        if not isinstance(step, dict):
            continue
        info = {"id": step.get("id")}
        items = step.get("items") or []
        if items and isinstance(items[0], dict):
            data = items[0].get("data") or items[0].get("tx")
            if data:
                info["data"] = data
        endpoint = (step.get("check") or {}).get("endpoint")
        if endpoint:
            info["endpoint"] = endpoint
        steps.append(info)
    return {"status": "success", "ok":True, "steps": quote.get('steps'), "swap_id": swap_id, "fees":quote.get("fees"), "details":quote.get("details")}

@app.get("/balances{walletAddress}")
async def fetch_balances(walletAddress:str):
    wb = WalletBalance()
    return await wb.resolve_balances(walletAddress)

@app.get("/swap/{swap_id}")
def get_swap(swap_id: str):
    """Retrieve a swap by ID"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    doc = swap_repo.get(swap_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Swap not found")

    return {
        "swap_id": str(doc.get("_id")),
        "status": doc.get("status"),
        "quote": doc.get("quote"),
        "execution": doc.get("execution"),
        "created_at": doc.get("created_at"),
        "executed_at": doc.get("executed_at"),
        "updated_at": doc.get("updated_at"),
    }

@app.get("/swap/{swap_id}/status", summary="Get swap status")
def swap_status(swap_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = swap_repo.get(swap_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Swap not found")
    txh = doc.get("tx_hash")
    confirmations = None
    if txh and doc.get("dst_chain") is not None:
        confirmations = get_transaction_confirmations(int(doc["dst_chain"]), txh)
    return {
        "status": doc.get("status"),
        "tx_hash": txh,
        "confirmations": confirmations,
        "chain_id": doc.get("chain_id"),
    }


@app.websocket("/ws/swaps/{swap_id}")
async def swap_ws(websocket: WebSocket, swap_id: str):
    """Stream swap status updates via WebSocket."""
    await websocket.accept()
    if not redis_client:
        await websocket.close()
        return

    channel = f"swap:{swap_id}"
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)
    try:
        while True:
            msg = await asyncio.to_thread(
                pubsub.get_message, ignore_subscribe_messages=True, timeout=1
            )
            if msg and msg.get("type") == "message":
                data = msg.get("data")
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(str(data))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.close()





def poll_swap_status(metric_id: str, endpoint: str) -> None:
    """Poll the provided endpoint for swap completion."""
    if db is None:
        return
    try:
        doc = db.swap_metrics.find_one({"_id": ObjectId(metric_id)})
        if not doc:
            if scheduler:
                scheduler.remove_job(f"swap_track_{metric_id}")
            return

        count = int(doc.get("poll_count", 0)) + 1
        final = False
        status = doc.get("status", "pending")
        tx_hash = doc.get("txHash")
        try:
            resp = requests.get(endpoint, timeout=10)
            if resp.ok:
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                tx_hash = tx_hash or data.get("txHash") or data.get("transactionHash") or data.get("hash")
                status = data.get("status") or data.get("state") or status
                if isinstance(status, str) and status.lower() in {"completed", "success", "failed", "error", "reverted", "cancelled"}:
                    final = True
        except Exception as exc:
            asyncio.run(handle_agent_error("SwapTracker", exc))

        if count >= 12 and not final:
            status = "timeout"
            final = True

        update = {
            "poll_count": count,
            "updated_at": datetime.utcnow(),
            "status": status,
        }
        if tx_hash:
            update["txHash"] = tx_hash
        if final:
            update["completed_at"] = datetime.utcnow()
        db.swap_metrics.update_one({"_id": ObjectId(metric_id)}, {"$set": update})

        if redis_client:
            try:
                swap_id = doc.get("swap_id")
                if swap_id:
                    payload = {"swap_id": swap_id, "status": status}
                    if tx_hash:
                        payload["txHash"] = tx_hash
                    if final:
                        payload["final"] = True
                    redis_client.publish(f"swap:{swap_id}", json.dumps(payload))
            except Exception as pub_exc:
                logger.error("Redis publish failed: %s", pub_exc)

        if final and scheduler:
            scheduler.remove_job(f"swap_track_{metric_id}")
    except Exception as exc:
        logger.exception("Error polling swap status")
        asyncio.run(handle_agent_error("SwapTracker", exc))


@app.post("/swap/track")
def track_swap(req: SwapTrackRequest):
    if db is None:
        return {"status": "error", "message": "Database not available"}

    doc = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    doc.update({
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "poll_count": 0,
        "completed_at": None,
    })
    metric = SwapMetric(**doc)
    result = db.swap_metrics.insert_one(metric.model_dump())
    doc_id = str(result.inserted_id)

    if scheduler:
        try:
            scheduler.add_job(
                poll_swap_status,
                "interval",
                seconds=5,
                id=f"swap_track_{doc_id}",
                args=[doc_id, doc.get("endpoint")],
            )
        except Exception as exc:
            asyncio.run(handle_agent_error("SwapTracker", exc))

    return {"status": "tracking", "id": doc_id}

@app.get("/history")
def history(user: str | None = None):
    if redis_client:
        cache_key = f"history:{user}" if user else "history:all"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(str(cached))

    if db is None:
        return {"swaps": []}

    query = {"user": user} if user else {}
    result = {
        "swaps": list(db.swaps.find(query, {"_id": 0}).sort("_id", -1)),
    }
    if redis_client:
        redis_client.setex(cache_key, 60, json.dumps(jsonable_encoder(result)))
    return result

@app.get("/quote")
def get_quote(
    source_chain: str,
    destination_chain: str,
    token_in: str,
    token_out: str,
    amount: str,
    user_address: str,
    receiver_address: str | None = None
):
    """Get quote from Relay API"""
    try:
        logger.info(
            f"Quote request - src:{source_chain} dst:{destination_chain} token_in:{token_in} token_out:{token_out} amount:{amount}"
        )

        src_chain_id = int(source_chain)
        dst_chain_id = int(destination_chain)

        if not is_address_for_chain(user_address, src_chain_id):
            raise HTTPException(status_code=422, detail="Invalid user_address for source chain")

        if receiver_address is None:
            if CHAIN_IDS.get(dst_chain_id, "").lower() == "solana":
                raise HTTPException(status_code=422, detail="receiver_address required for Solana")
            receiver_address = user_address
        elif not is_address_for_chain(receiver_address, dst_chain_id):
            raise HTTPException(status_code=422, detail="Invalid receiver_address for destination chain")

        # Use chain IDs directly
        if not src_chain_id:
            logger.error(f"Source chain: {src_chain_id} is not available ")
            raise HTTPException(status_code=404,detail="Src chain not supported")
        if not dst_chain_id:
            logger.error(f"Destination chain: {dst_chain_id} is not available ")
            raise HTTPException(status_code=404,detail="Dest chain not supported")
        input_amount = amount
        
        params = {
            "originChainId": int(source_chain),
            "destinationChainId": int(destination_chain),
            "inputToken": resolve_token_address(src_chain_id, token_in),
            "outputToken": resolve_token_address(dst_chain_id, token_out),
            "inputAmount": input_amount,
            "user": user_address,
            "receiver": receiver_address or user_address,
            "tradeType": "EXACT_INPUT",
        }
        
        # Use standardized relay function
        quote_data = relay_get_quote(params)

        result_data = None
        if isinstance(quote_data, dict):
            if "result" in quote_data:
                result_data = quote_data.get("result")
            elif "steps" in quote_data or "details" in quote_data:
                # Latest API returns the quote directly with these fields
                result_data = quote_data
            elif quote_data.get("status") == "error" and isinstance(quote_data.get("message"), dict):
                # Relay sometimes returns status "error" while providing the quote
                result_data = quote_data.get("message")

        if result_data:
            logger.info("Quote retrieved successfully")

            # Extract essential fields for the frontend
            result = result_data
            output_amount = None
            output_token = None
            output_value_usd = None

            if isinstance(result, dict):
                if "outputAmount" in result:
                    output_amount = result.get("outputAmount")
                    output_token = result.get("outputToken")
                    output_value_usd = result.get("outputValueInUsd")
                elif "details" in result:
                    out = result.get("details", {}).get("currencyOut", {})
                    output_amount = out.get("amount")
                    output_token = out.get("currency")
                    output_value_usd = out.get("amountUsd")
                elif "output" in result:
                    out = result.get("output", {})
                    output_amount = out.get("amount")
                    output_token = out.get("token")
                    output_value_usd = out.get("valueInUsd")

            simplified = {"outputAmount": output_amount}
            if output_token is not None:
                simplified["outputToken"] = output_token
            if output_value_usd is not None:
                simplified["outputValueInUsd"] = output_value_usd

            return {
                "status": "success",
                "quote": simplified
            }
        else:
            logger.error(
                "Failed to get quote from Relay - params:%s response:%s",
                {k: params[k] for k in params if k not in {"user", "receiver"}},
                quote_data,
            )
            message = None
            if isinstance(quote_data, dict):
                message = quote_data.get("message") or quote_data.get("error")
            return {
                "status": "error",
                "message": message or quote_data,
                "code": "QUOTE_FAILED",
            }
    except Exception as e:
        logger.exception("Error getting quote")
        asyncio.run(handle_agent_error("CrossChainSwapRouter", e))
        return {
            "status": "error",
            "message": f"Error getting quote: {str(e)}"
        }

@app.get("/chains")
def get_supported_chains():
    """Get supported chains from Relay API."""
    try:
        response = requests.get(
            f"{RELAY_BASE_URL}/chains",
            timeout=10,
        )

        if response.ok:
            data = response.json()
            chains = data.get("chains")
            if chains is None:
                chains = data.get("result", [])

            formatted = [
                {
                    "chainId": c.get("id"),
                    "name": c.get("displayName"),
                    "icon": c.get("iconUrl"),
                    "currency": c.get("currency"),
                }
                for c in chains or []
                if isinstance(c, dict)
            ]

            if not formatted and isinstance(chains, list):
                formatted = chains

            return {"status": "success", "chains": formatted}

        return {
            "status": "error",
            "message": f"Failed to fetch chains: {response.status_code}",
            "details": response.text,
        }

    except Exception as e:
        asyncio.run(handle_agent_error("CrossChainSwapRouter", e))
        return {
            "status": "error",
            "message": f"Error fetching chains: {str(e)}",
        }

@app.get("/tokens/{chain_id}")
def get_tokens_for_chain(chain_id: int):
    """Get tokens for a specific chain from Relay API."""
    try:
        response = requests.get(
            f"{RELAY_BASE_URL}/chains",
            timeout=10,
        )

        if response.ok:
            data = response.json()
            if "chains" not in data and "result" in data and isinstance(data["result"], list) and not any(isinstance(i, dict) and "id" in i for i in data["result"]):
                # Fallback for legacy /tokens response used in tests
                return {"status": "success", "tokens": data["result"]}

            chains = data.get("chains")
            if chains is None:
                chains = data.get("result", [])

            chain = next((c for c in chains if c.get("id") == chain_id or c.get("chainId") == chain_id), None)
            if not chain:
                return {"status": "success", "tokens": []}

            token_list = (
                chain.get("featuredTokens") or chain.get("erc20Currencies") or []
            )

            if isinstance(token_list, dict):
                token_list = list(token_list.values())

            tokens = [
                {
                    "address": t.get("address"),
                    "symbol": t.get("symbol"),
                    "name": t.get("name"),
                    "decimals": t.get("decimals"),
                    "logoURI": t.get("logoURI") or t.get("iconUrl"),
                }
                for t in token_list
                if isinstance(t, dict)
            ]

            return {"status": "success", "tokens": tokens}

        return {
            "status": "error",
            "message": f"Failed to fetch tokens: {response.status_code}",
            "details": response.text,
        }

    except Exception as e:
        asyncio.run(handle_agent_error("CrossChainSwapRouter", e))
        return {
            "status": "error",
            "message": f"Error fetching tokens: {str(e)}",
        }


# Cleanup on shutdown
def cleanup():
    if scheduler:
        scheduler.shutdown()

atexit.register(cleanup)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
