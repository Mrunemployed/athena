import { BalanceAdapter, TokenBalance } from './types';

export class CovalentFallbackAdapter implements BalanceAdapter {
  async getBalances(wallet: string, chain: { id: string; namespace: string }): Promise<TokenBalance[]> {
    // TODO: Implement Covalent fallback logic
    return [];
  }
} 