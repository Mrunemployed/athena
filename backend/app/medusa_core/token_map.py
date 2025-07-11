import logging
import time
from typing import Dict

import requests

from .relay import RELAY_BASE_URL


logger = logging.getLogger(__name__)

TOKEN_MAP = {
    1: {
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'USDC': '0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'LINK': '0x514910771AF9Ca656af840dff83E8264EcF986CA',
        'UNI': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'AAVE': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
        'CRV': '0xD533a949740bb3306d119CC777fa900bA034cd52',
        'MATIC': '0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0',
        'BNB': '0xB8c77482e45F1F44de1745F52C74426C631bdd52',
        'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
        'OP': '0x4200000000000000000000000000000000000042',
        'AVAX': '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7',
        'FTM': '0x4e15361fd6b4bb609fa63c81a2be19d873717870',
        'SETH': '0x5e74c9036fb86bd7ecdcb084a0673efc32ea31cb',
    },
    11155111: {
        'USDT': '0x94c5fE3A5810C7A0545B2c2255bB9A1aA4c1a7a9',
        'WETH': '0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6',
    },
    56: {
        'USDT': '0x55d398326f99059fF775485246999027B3197955',
        'WETH': '0x2170Ed0880ac9A755fd29B2688956BD959F933F',
        'BNB': '0x0000000000000000000000000000000000000000',
    },
    137: {
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
        'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
        'MATIC': '0x0000000000000000000000000000000000001010',
    },
}

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
        resp = requests.get(f"{RELAY_BASE_URL}/chains", timeout=10)
        if resp.ok:
            data = resp.json()
            chains = data.get("chains") or data.get("result") or []
            for chain in chains:
                cid = chain.get("id") or chain.get("chainId")
                if cid is None:
                    continue
                CHAIN_IDS[cid] = chain.get("name")
                tokens = (
                    chain.get("erc20Currencies")
                    or chain.get("featuredTokens")
                    or []
                )
                if isinstance(tokens, dict):
                    tokens = list(tokens.values())
                symbol_map: Dict[str, str] = {}
                for t in tokens:
                    if not isinstance(t, dict):
                        continue
                    sym = t.get("symbol")
                    addr = t.get("address")
                    if sym and addr:
                        symbol_map[sym.upper()] = addr
                if symbol_map:
                    mapping[cid] = symbol_map
    except Exception as exc:
        logger.exception("Error loading token map via /chains: %s", exc)

    if not mapping:
        # Fallback to per-chain endpoint using known chain IDs
        for cid in TOKEN_MAP.keys():
            tokens = _fetch_tokens_for_chain(cid)
            if tokens:
                mapping[cid] = tokens

    if mapping:
        _REMOTE_MAP = mapping
        _CACHE_TIMESTAMP = time.time()


def resolve_token_address(chain_id: int, token: str) -> str:
    """Return the address for a token symbol if available."""
    if token.lower().startswith("0x") and len(token) == 42:
        return token

    now = time.time()
    if now - _CACHE_TIMESTAMP > _CACHE_TTL or chain_id not in _REMOTE_MAP:
        load_token_map()

    symbol = token.upper()
    addr = _REMOTE_MAP.get(chain_id, {}).get(symbol)
    if addr:
        return addr

    mapping = TOKEN_MAP.get(chain_id, {})
    return mapping.get(symbol, token)

def resolve_key(dict_in:dict, value:str)-> str:
    for key,val in dict_in.items():
        if val == value:
            return key


def resolve_token_symbol(chain_id:int, token_addr:str):
    now = time.time()
    if now - _CACHE_TIMESTAMP > _CACHE_TTL or chain_id not in _REMOTE_MAP:
        load_token_map()
    tokens_in_chain = _REMOTE_MAP.get(chain_id, {})
    if not tokens_in_chain:
        mapping = TOKEN_MAP.get(chain_id, {})        
        return resolve_key(mapping, value=token_addr)
    symbol = resolve_key(tokens_in_chain, value=token_addr)
    return symbol
