import logging
import time
from typing import Dict

import requests

from .relay import RELAY_BASE_URL


logger = logging.getLogger(__name__)

# Remote token map fetched from Relay
_REMOTE_MAP: Dict[int, Dict[str, str]] = {}
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL = 3600  # 1 hour

CHAIN_IDS : Dict[int, str] = {}

def _fetch_tokens_for_chain(chain_id: int) -> Dict[str, str]:
    """Fetch tokens for a single chain via Relay."""
    try:
        resp = requests.get(f"{RELAY_BASE_URL}/tokens/{chain_id}", timeout=10)
        if resp.ok:
            data = resp.json()
            tokens = data.get("tokens") or data.get("result") or []
            if isinstance(tokens, dict):
                tokens = list(tokens.values())
            mapping: Dict[str, str] = {}
            for t in tokens:
                if isinstance(t, dict):
                    sym = t.get("symbol")
                    addr = t.get("address")
                    if sym and addr:
                        mapping[sym.upper()] = addr
            return mapping
    except Exception as exc:
        logger.exception("Error fetching tokens for chain %s: %s", chain_id, exc)
    return {}


def load_token_map() -> None:
    """Load token mapping from Relay into the in-memory cache."""
    global _REMOTE_MAP, _CACHE_TIMESTAMP, CHAIN_IDS
    mapping: Dict[int, Dict[str, str]] = {}
    
    try:
        # Fetch chains from Relay API
        resp = requests.get(f"{RELAY_BASE_URL}/chains", timeout=10)
        if resp.ok:
            data = resp.json()
            chains = data.get("chains") or data.get("result") or []
            
            for chain in chains:
                cid = chain.get("id") or chain.get("chainId")
                if cid is None:
                    continue
                    
                CHAIN_IDS[cid] = chain.get("name") or chain.get("displayName")
                symbol_map: Dict[str, str] = {}
                
                # Add native token (like ETH, MATIC, etc.)
                native_currency = chain.get("currency")
                if native_currency:
                    symbol_map[native_currency.upper()] = "0x0000000000000000000000000000000000000000"
                
                # Add ERC20 tokens
                tokens = (
                    chain.get("erc20Currencies")
                    or chain.get("featuredTokens")
                    or []
                )
                
                if isinstance(tokens, dict):
                    tokens = list(tokens.values())
                    
                for t in tokens:
                    if not isinstance(t, dict):
                        continue
                    sym = t.get("symbol")
                    addr = t.get("address")
                    if sym and addr:
                        symbol_map[sym.upper()] = addr
                
                if symbol_map:
                    mapping[cid] = symbol_map
                    logger.info(f"Loaded {len(symbol_map)} tokens for chain {cid} ({CHAIN_IDS[cid]})")
                    
    except Exception as exc:
        logger.exception("Error loading token map via /chains: %s", exc)
        # If chains endpoint fails, try individual chain endpoints
        known_chains = [1, 137, 56, 42161, 10, 11155111]  # Common chains
        for cid in known_chains:
            tokens = _fetch_tokens_for_chain(cid)
            if tokens:
                mapping[cid] = tokens
                logger.info(f"Loaded {len(tokens)} tokens for chain {cid} via individual endpoint")

    if mapping:
        _REMOTE_MAP = mapping
        _CACHE_TIMESTAMP = time.time()
        logger.info(f"Token map loaded with {len(mapping)} chains")
    else:
        logger.warning("Failed to load any token mappings from Relay API")


def resolve_token_address(chain_id: int, token: str) -> str:
    """Return the address for a token symbol if available."""
    # If it's already an address, return as is
    if token.lower().startswith("0x") and len(token) == 42:
        return token

    # Refresh cache if needed
    now = time.time()
    if now - _CACHE_TIMESTAMP > _CACHE_TTL or chain_id not in _REMOTE_MAP:
        load_token_map()

    symbol = token.upper()
    addr = _REMOTE_MAP.get(chain_id, {}).get(symbol)
    
    if addr:
        logger.debug(f"Resolved {token} to {addr} on chain {chain_id}")
        return addr
    
    # If not found, return the original token (let Relay handle it)
    logger.warning(f"Token {token} not found in mapping for chain {chain_id}")
    return token


def resolve_key(dict_in: dict, value: str) -> str:
    """Find the key for a given value in a dictionary."""
    for key, val in dict_in.items():
        if val == value:
            return key
    return value  # Return the original value if not found


def resolve_token_symbol(chain_id: int, token_addr: str) -> str:
    """Return the symbol for a token address if available."""
    # Refresh cache if needed
    now = time.time()
    if now - _CACHE_TIMESTAMP > _CACHE_TTL or chain_id not in _REMOTE_MAP:
        load_token_map()
        
    tokens_in_chain = _REMOTE_MAP.get(chain_id, {})
    symbol = resolve_key(tokens_in_chain, token_addr)
    return symbol
