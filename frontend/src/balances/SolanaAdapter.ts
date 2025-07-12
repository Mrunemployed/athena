import { Connection, PublicKey } from '@solana/web3.js';
import { BalanceAdapter, TokenBalance } from './types';

const SOLANA_ENDPOINTS: Record<string, string> = {
  'solana': 'https://api.mainnet-beta.solana.com',
  'solanaDevnet': 'https://api.devnet.solana.com',
  'solanaTestnet': 'https://api.testnet.solana.com',
};

const CHAIN_NAMES: Record<string, string> = {
  'solana': 'Solana',
  'solanaDevnet': 'Solana Devnet',
  'solanaTestnet': 'Solana Testnet',
};

const cache: Record<string, { data: TokenBalance[]; ts: number }> = {};

export class SolanaAdapter implements BalanceAdapter {
  async getBalances(wallet: string, chain: { id: string; namespace: string }): Promise<TokenBalance[]> {
    const { id: chainId } = chain;
    const cacheKey = `${wallet}:${chainId}`;
    const now = Date.now();
    if (cache[cacheKey] && now - cache[cacheKey].ts < 10000) {
      return cache[cacheKey].data;
    }
    const endpoint = SOLANA_ENDPOINTS[chainId];
    if (!endpoint) return [];
    try {
      const connection = new Connection(endpoint);
      const pubkey = new PublicKey(wallet);
      // Native SOL balance
      const solBalance = await connection.getBalance(pubkey);
      const tokens: TokenBalance[] = [{
        chainId,
        chainName: CHAIN_NAMES[chainId] || chainId,
        namespace: 'solana',
        address: 'native',
        symbol: 'SOL',
        name: 'Solana',
        decimals: 9,
        amount: BigInt(solBalance),
        isNative: true,
      }];
      // SPL tokens (basic, no metadata enrichment yet)
      const tokenAccounts = await connection.getParsedTokenAccountsByOwner(pubkey, { programId: new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA') });
      for (const { account, pubkey: tokenPubkey } of tokenAccounts.value) {
        const info = account.data.parsed.info;
        const mint = info.mint;
        const amount = BigInt(info.tokenAmount.amount);
        if (amount === 0n) continue;
        tokens.push({
          chainId,
          chainName: CHAIN_NAMES[chainId] || chainId,
          namespace: 'solana',
          address: mint,
          symbol: mint.slice(0, 6),
          name: mint,
          decimals: info.tokenAmount.decimals,
          amount,
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