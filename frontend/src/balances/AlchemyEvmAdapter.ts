import axios from 'axios';
import { BalanceAdapter, TokenBalance } from './types';

const ALCHEMY_API_KEYS: Record<string, string> = {
  '1': 'ECNFancOj9oOMYrqcfg58m5wS0qFWXdh', // Ethereum Mainnet (replace with your key)
  '137': 'ECNFancOj9oOMYrqcfg58m5wS0qFWXdh', // Polygon (replace with your key)
  // Add more chain IDs and keys as needed
};

const CHAIN_NAMES: Record<string, string> = {
  '1': 'Ethereum',
  '137': 'Polygon',
  // Add more as needed
};

const ALCHEMY_BASE_URLS: Record<string, string> = {
  '1': 'https://eth-mainnet.g.alchemy.com/v2/',
  '137': 'https://polygon-mainnet.g.alchemy.com/v2/',
  // Add more as needed
};

// Simple in-memory cache
const cache: Record<string, { data: TokenBalance[]; ts: number }> = {};

export class AlchemyEvmAdapter implements BalanceAdapter {
  async getBalances(wallet: string, chain: { id: string; namespace: string }): Promise<TokenBalance[]> {
    const { id: chainId } = chain;
    const cacheKey = `${wallet}:${chainId}`;
    const now = Date.now();
    if (cache[cacheKey] && now - cache[cacheKey].ts < 10000) {
      return cache[cacheKey].data;
    }
    const apiKey = ALCHEMY_API_KEYS[chainId];
    const baseUrl = ALCHEMY_BASE_URLS[chainId];
    if (!apiKey || !baseUrl) return [];
    try {
      // Native balance
      const nativeRes = await axios.post(`${baseUrl}${apiKey}`, {
        jsonrpc: '2.0',
        id: 1,
        method: 'eth_getBalance',
        params: [wallet, 'latest'],
      });
      const nativeBalance = BigInt(nativeRes.data.result);
      // ERC-20 balances
      const tokenRes = await axios.post(`${baseUrl}${apiKey}`, {
        jsonrpc: '2.0',
        id: 2,
        method: 'alchemy_getTokenBalances',
        params: [wallet],
      });
      const tokens: TokenBalance[] = [];
      // Native asset
      tokens.push({
        chainId,
        chainName: CHAIN_NAMES[chainId] || chainId,
        namespace: 'eip155',
        address: 'native',
        symbol: chainId === '1' ? 'ETH' : chainId === '137' ? 'MATIC' : 'NATIVE',
        name: chainId === '1' ? 'Ethereum' : chainId === '137' ? 'Polygon' : 'Native',
        decimals: 18,
        amount: nativeBalance,
        isNative: true,
      });
      // ERC-20 tokens
      for (const t of tokenRes.data.result.tokenBalances) {
        if (t.tokenBalance === null) continue;
        tokens.push({
          chainId,
          chainName: CHAIN_NAMES[chainId] || chainId,
          namespace: 'eip155',
          address: t.contractAddress,
          symbol: t.symbol || t.contractAddress.slice(0, 6),
          name: t.name || t.contractAddress,
          decimals: t.decimals || 18,
          amount: BigInt(t.tokenBalance),
          isNative: false,
        });
      }
      cache[cacheKey] = { data: tokens, ts: now };
      return tokens;
    } catch (e) {
      return [];
    }
  }
} 