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
        # Try different possible token endpoints
        endpoints = [
            f"{RELAY_BASE_URL}/tokens/{chain_id}",
            f"{RELAY_BASE_URL}/v1/tokens/{chain_id}",
            f"{RELAY_BASE_URL}/api/v1/tokens/{chain_id}",
            f"{RELAY_BASE_URL}/currencies/{chain_id}",
            f"{RELAY_BASE_URL}/v1/currencies/{chain_id}",
        ]
        
        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, timeout=10)
                if resp.ok:
                    data = resp.json()
                    logger.debug(f"Token endpoint {endpoint} returned: {data}")
                    tokens = data.get("tokens") or data.get("result") or data.get("currencies") or []
                    if isinstance(tokens, dict):
                        tokens = list(tokens.values())
                    mapping: Dict[str, str] = {}
                    for t in tokens:
                        if isinstance(t, dict):
                            sym = t.get("symbol")
                            addr = t.get("address")
                            if sym and addr:
                                mapping[sym.upper()] = addr
                    if mapping:
                        logger.info(f"Successfully fetched {len(mapping)} tokens from {endpoint}")
                        return mapping
                elif resp.status_code != 404:
                    logger.warning(f"Token endpoint {endpoint} returned {resp.status_code}")
            except Exception as exc:
                logger.debug(f"Error trying endpoint {endpoint}: {exc}")
                continue
                
        logger.warning(f"No working token endpoint found for chain {chain_id}")
        return {}
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
            logger.debug(f"Chains response structure: {type(data)}")
            logger.debug(f"Chains response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            chains = data.get("chains") or data.get("result") or []
            logger.debug(f"Found {len(chains)} chains")
            
            for i, chain in enumerate(chains):
                logger.debug(f"Chain {i} structure: {type(chain)}")
                logger.debug(f"Chain {i} keys: {list(chain.keys()) if isinstance(chain, dict) else 'Not a dict'}")
                
                cid = chain.get("id") or chain.get("chainId")
                if cid is None:
                    continue
                
                # Ensure cid is an integer for the dictionary key
                try:
                    cid_int = int(cid)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid chain ID: {cid}")
                    continue
                    
                chain_name = chain.get("name") or chain.get("displayName")
                if chain_name and isinstance(chain_name, str):
                    CHAIN_IDS[cid_int] = chain_name
                symbol_map: Dict[str, str] = {}
                
                # Add native token (like ETH, MATIC, etc.)
                native_currency = chain.get("currency")
                logger.debug(f"Native currency for chain {cid_int}: {native_currency} (type: {type(native_currency)})")
                
                if native_currency:
                    if isinstance(native_currency, dict):
                        # Handle case where currency is a dict with symbol field
                        currency_symbol = native_currency.get("symbol") or native_currency.get("name")
                        if currency_symbol and isinstance(currency_symbol, str):
                            symbol_map[currency_symbol.upper()] = "0x0000000000000000000000000000000000000000"
                    elif isinstance(native_currency, str):
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
                    mapping[cid_int] = symbol_map
                    logger.info(f"Loaded {len(symbol_map)} tokens for chain {cid_int} ({CHAIN_IDS[cid_int]})")
                    
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
        logger.warning("Failed to load any token mappings from Relay API, using fallback tokens")
        # Fallback to common tokens for major chains
        fallback_tokens = {
            1: {  # Ethereum
                "ETH": "0x0000000000000000000000000000000000000000",
                "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                "USDC": "0xA0b86a33E6441b8C4C8C8C8C8C8C8C8C8C8C8C8C",
                "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            },
            137: {  # Polygon
                "MATIC": "0x0000000000000000000000000000000000000000",
                "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
            },
            56: {  # BSC
                "BNB": "0x0000000000000000000000000000000000000000",
                "USDT": "0x55d398326f99059fF775485246999027B3197955",
                "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
                "WBNB": "0xbb4CdB9CBd36B01bD1cBaEF60aF814C3bFc7c70d",
            },
            42161: {  # Arbitrum
                "ETH": "0x0000000000000000000000000000000000000000",
                "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
                "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            },
            10: {  # Optimism
                "ETH": "0x0000000000000000000000000000000000000000",
                "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
                "USDC": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "WETH": "0x4200000000000000000000000000000000000006",
            },
        }
        _REMOTE_MAP = fallback_tokens
        # Add fallback chain names
        fallback_chain_names = {
            1: "Ethereum",
            137: "Polygon",
            56: "BNB Smart Chain",
            42161: "Arbitrum One",
            10: "Optimism",
        }
        CHAIN_IDS.update(fallback_chain_names)
        _CACHE_TIMESTAMP = time.time()
        logger.info(f"Using fallback token map with {len(fallback_tokens)} chains")


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
