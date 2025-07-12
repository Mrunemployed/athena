import os
from aiohttp import ClientSession
from typing import Dict
from pydantic import BaseModel
from dotenv import load_dotenv
from threading import Thread
import asyncio
from pathlib import Path
import sys
from abc import ABC
import json

load_dotenv()

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

PROVIDES = {
    'relay':{
        'active': False,
        'api': os.getenv("RELAY_BASE_URL",None),
        'api_key': None
    }
}

class Endpoints(BaseModel):
    supported_chains:str=''
    quote:str=''
    
class interface(BaseModel):
    active:bool=False
    base_url:str=''
    apikey:str=''
    supported_chains:Dict[int, Dict[str, str]] = {}
    endpoints:Endpoints=None

class ConnectorInterface(ABC):
    def _boot(self):
        raise NotImplementedError("`_boot` method needs to be implemented!")

    def setup(self):
        raise NotImplementedError("`setup` method needs to be implemented!")
    
    def supported_chains(Self):
        raise NotImplementedError("`supported_chains` method needs to be implemented!")


class relay(ConnectorInterface):

    def __init__(self):
        self.interface:interface = None
        
    def _boot(self):
        available_endpoints = Endpoints(
                supported_chains='/chains',
                quote='/quote'
            )
        config = interface(
            active=True,
            base_url= os.getenv("RELAY_BASE_URL",None),
            endpoints=available_endpoints
        )
        return config

    async def _load_supported_chains(self) -> dict:
        try:
                
            chains_url = self.interface.base_url+self.interface.endpoints.supported_chains
            async with ClientSession() as session:
                async with session.get(url=chains_url) as request:
                    response = await request.json()
                    return response
                
        except Exception as err:
            return
            
    async def supported_chains(self):
        supported_chains = {}
        data = await self._load_supported_chains()
        if not data:
            return
        
        chains = data.get("chains") or data.get("result") or []
        for chain in chains:
            cid = chain.get("id") or chain.get("chainId")
            if cid is None:
                continue
            supported_chains[cid] = chain.get("name")
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
                supported_chains[cid] = symbol_map
        return supported_chains

    async def setup(self):
        self.interface = self._boot()
        self.interface.supported_chains = await self.supported_chains()



class Providers:

    def __init__(self):
        self._providers = {'relay': relay()}

    async def get_provider(self,provider:str='relay') -> interface:
        if provider not in self._providers:
            return None
        provider_requested = self._providers.get(provider)
        if provider_requested.interface.supported_chains:
            return provider_requested.interface
        else:
            await self.load_providers()
            return provider_requested.interface
    
    async def load_providers(self):
        for key,connector in self._providers.items():
            await connector.setup()

providers = Providers()

class WalletBalance:
    def __init__(
        self,
    ):
        self._rpc_provider_name = "Alchemy"
        self._supported_providers = None
        self._project_id = ALCHEMY_API_KEY
        self._supported_networks:dict = self.supported_networks()
        self._metadata : dict = self._load_metadata()
    
    def build_uris(self,chain_id:str):
        try:
                
            if not self._supported_networks:
                self._supported_networks = self.supported_networks()
            alchemy_dict:dict = self._supported_networks.get(str(chain_id))
            if not alchemy_dict:
                raise ValueError("network not supported")
            url = alchemy_dict.get('url')
            return f"{url}{self._project_id}"
        except Exception as err:
            return


    def _conf_file(self,dir:str,file:str):
        if getattr(sys,'frozen', False):
            return Path(sys.executable).parent.parent
        load_dotenv()
        _base_path = Path(__file__).resolve().parent.parent
        return _base_path / dir / file

    def supported_networks(self):
        file_path = self._conf_file('config', 'alchemy.json')
        with open(file_path,'r') as alchemy_nets:
            _supported_networks = json.load(alchemy_nets)
            return _supported_networks

    def _load_metadata(self):
        file_path = self._conf_file('config', 'metadata.json')
        with open(file_path,'r') as metadata:
            return json.load(metadata)

    def build_payload(self, wallet_addr:str):
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "alchemy_getTokenBalances",
            "params": [
                wallet_addr,
            ]
        }
        return payload

    async def _convert_to_currency(self,response:dict):
        token_balances = response.get('tokenBalances')
        available_balances = []
        for balanceObj in token_balances:
            contractAddress = balanceObj.get('contractAddress')
            tokenBalance = balanceObj.get("tokenBalance")
            raw_tokenBalance = int(tokenBalance, 16)
            if raw_tokenBalance == 0:
                continue
            else:
                token = self._metadata.get(contractAddress)
                if not token:
                    continue
                decimals = token.get("decimal",18)
                address = token.get("address")
                symbol = token.get("symbol")
                amount = raw_tokenBalance / 10 ** decimals
                amount = float(f"{amount:.8f}")
                balance_map = {
                    "address": address,
                    "symbol": symbol,
                    "amount": amount
                }
                available_balances.append(balance_map)
        return available_balances


    async def call(self, chain_id:int|str, wallet_addr:str, retries=3):
        try:
            req_url = self.build_uris(str(chain_id))
            # print(req_url)
            if not req_url:
                return
            async with ClientSession() as session:
                for _ in range(retries):
                    async with session.post(url=req_url,json=self.build_payload(wallet_addr)) as request:
                        if request.status == 400:
                            return
                        elif request.status > 200:
                            continue
                        response = await request.json()
                        if request.status<=200 and response.get("result"):
                            available_balances = await self._convert_to_currency(response.get("result"))
                            return available_balances
        except Exception as err:
            return
            # print(err)
        
    async def run_in_pool(self, wallet_addr:str):
        network_pool = []
        for k,v in self._supported_providers.supported_chains.items():
            call_future = self.call(chain_id=k, wallet_addr=wallet_addr)
            network_pool.append(call_future)
        coro_pool = await asyncio.gather(*network_pool)
        consolidated = []
        for result in coro_pool:
            consolidated.append(result)
        return consolidated

    async def resolve_balances(
        self,
        wallet_addr:str
    ):
        await providers.load_providers()
        self._supported_providers = await providers.get_provider()
        balances = await self.run_in_pool(wallet_addr)
        refined = []
        for balance in balances:
            if balance:
                refined.extend(balance)
        return refined
    
BalanceProvider = WalletBalance()

if __name__ == '__main__':
    # balanceResolver = WalletBalance()
    pass
    # print(asyncio.run(balanceResolver.resolve_balances("0xD3D8d8FD0a225a48343DFB945eE8eBa50fc47afA")))