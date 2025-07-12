// TokenBalance type for both native and contract tokens
export interface TokenBalance {
  chainId: string; // e.g. '1' for Ethereum mainnet, '137' for Polygon
  chainName: string;
  namespace: 'eip155' | 'solana';
  address: string; // contract address or 'native'
  symbol: string;
  name: string;
  logoURI?: string;
  decimals: number;
  amount: bigint; // always raw, not formatted
  usdValue?: number; // optional, for price display
  isNative: boolean;
  blockExplorerUrl?: string;
}

// Adapter interface for all balance providers
export interface BalanceAdapter {
  getBalances(wallet: string, chain: { id: string; namespace: string }): Promise<TokenBalance[]>;
} 