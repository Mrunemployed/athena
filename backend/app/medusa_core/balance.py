import os
import logging
import requests
import time
from typing import Dict

from .token_map import resolve_token_address
from .relay import RELAY_BASE_URL

logger = logging.getLogger(__name__)

# Fallback RPC URLs from environment variables
FALLBACK_RPC_URLS = {
    1: os.getenv("ETHEREUM_RPC_URL"),
    137: os.getenv("POLYGON_RPC_URL"),
    56: os.getenv("BSC_RPC_URL"),
    42161: os.getenv("ARBITRUM_RPC_URL"),
    10: os.getenv("OPTIMISM_RPC_URL"),
    11155111: os.getenv("SEPOLIA_RPC_URL"),
}

# Cache for dynamic RPC URLs from Relay API
_RPC_CACHE: Dict[int, str] = {}
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL = 3600  # 1 hour cache

def _fetch_rpc_urls_from_relay() -> Dict[int, str]:
    """Fetch RPC URLs dynamically from Relay API"""
    try:
        resp = requests.get(f"{RELAY_BASE_URL}/chains", timeout=10)
        if resp.ok and resp.headers.get("Content-Type", "").startswith("application/json"):
            data = resp.json()
            chains = data.get("chains") or []
            rpc_map: Dict[int, str] = {}
            
            for chain in chains:
                chain_id = chain.get("id")
                http_rpc_url = chain.get("httpRpcUrl")
                
                if chain_id is not None and http_rpc_url:
                    rpc_map[int(chain_id)] = http_rpc_url
                    logger.debug(f"Cached RPC URL for chain {chain_id}: {http_rpc_url}")
            
            return rpc_map
        else:
            logger.error("Unexpected response from Relay API: %s", resp.text)
    except Exception as exc:
        logger.error("Failed to fetch RPC URLs from Relay API: %s", exc)
    
    return {}

def _get_rpc_url(chain_id: int) -> str | None:
    """Get RPC URL for a chain, with caching and fallback"""
    global _RPC_CACHE, _CACHE_TIMESTAMP
    
    # Check if cache is expired or empty
    now = time.time()
    if now - _CACHE_TIMESTAMP > _CACHE_TTL or not _RPC_CACHE:
        logger.info("Refreshing RPC URL cache from Relay API")
        _RPC_CACHE = _fetch_rpc_urls_from_relay()
        _CACHE_TIMESTAMP = now
    
    # Try dynamic RPC URL first
    if chain_id in _RPC_CACHE:
        return _RPC_CACHE[chain_id]
    
    # Fallback to environment variables
    fallback_url = FALLBACK_RPC_URLS.get(chain_id)
    if fallback_url:
        logger.warning(f"Using fallback RPC URL for chain {chain_id}")
        return fallback_url
    
    logger.error(f"No RPC URL available for chain {chain_id}")
    return None

def _rpc_call(chain_id: int, method: str, params: list) -> str | None:
    url = _get_rpc_url(chain_id)
    if not url:
        logger.warning("No RPC URL configured for chain %s", chain_id)
        return None
    try:
        resp = requests.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=10,
        )
        resp.raise_for_status()
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            logger.error("Non-JSON RPC response for chain %s: %s", chain_id, resp.text)
            return None
        data = resp.json()
        return data.get("result")
    except Exception as exc:
        logger.error("RPC call failed for chain %s: %s", chain_id, exc)
        return None


def get_token_balance(chain_id: int, token: str, address: str) -> int | None:
    logger.debug(f"get_token_balance called with chain_id={chain_id} (type={type(chain_id)})")
    if isinstance(chain_id, str):
        try:
            chain_id_int = int(chain_id)
            logger.warning(f"Auto-converted chain_id from string '{chain_id}' to {chain_id_int}")
            chain_id = chain_id_int
        except Exception:
            logger.error(f"Invalid chain_id: {chain_id}")
            return None
    token_addr = resolve_token_address(chain_id, token)
    native_tokens = {
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000001010",
    }
    if token_addr.lower() in native_tokens:
        result = _rpc_call(chain_id, "eth_getBalance", [address, "latest"])
    else:
        data = "0x70a08231" + address[2:].rjust(64, "0")
        params = [{"to": token_addr, "data": data}, "latest"]
        result = _rpc_call(chain_id, "eth_call", params)
    if result is None:
        return None
    try:
        return int(result, 16)
    except Exception:
        return None


def get_allowance(chain_id: int, token: str, owner: str, spender: str) -> int | None:
    logger.debug(f"get_allowance called with chain_id={chain_id} (type={type(chain_id)})")
    if isinstance(chain_id, str):
        try:
            chain_id_int = int(chain_id)
            logger.warning(f"Auto-converted chain_id from string '{chain_id}' to {chain_id_int}")
            chain_id = chain_id_int
        except Exception:
            logger.error(f"Invalid chain_id: {chain_id}")
            return None
    token_addr = resolve_token_address(chain_id, token)
    native_tokens = {
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000001010",
    }
    if token_addr.lower() in native_tokens:
        return 2**256 - 1
    data = (
        "0xdd62ed3e"
        + owner[2:].rjust(64, "0")
        + spender[2:].rjust(64, "0")
    )
    params = [{"to": token_addr, "data": data}, "latest"]
    result = _rpc_call(chain_id, "eth_call", params)
    if result is None:
        return None
    try:
        return int(result, 16)
    except Exception:
        return None

def get_transaction_confirmations(chain_id: int, tx_hash: str) -> int | None:
    """Return confirmation count for a transaction."""
    receipt = _rpc_call(chain_id, "eth_getTransactionReceipt", [tx_hash])
    if not receipt or not isinstance(receipt, dict) or receipt.get("blockNumber") is None:
        return 0
    block_hex = receipt["blockNumber"]
    try:
        receipt_block = int(block_hex, 16)
    except Exception:
        return None
    current_hex = _rpc_call(chain_id, "eth_blockNumber", [])
    if current_hex is None:
        return None
    try:
        current_block = int(current_hex, 16)
    except Exception:
        return None
    return max(current_block - receipt_block + 1, 0)
