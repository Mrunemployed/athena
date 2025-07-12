import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useWallet } from '../hooks/useWallet';
import { networks } from '../config';
import { AlchemyEvmAdapter } from './AlchemyEvmAdapter';
import { SolanaAdapter } from './SolanaAdapter';
import { TokenBalance } from './types';

const alchemy = new AlchemyEvmAdapter();
const solana = new SolanaAdapter();

// Map network id to namespace
function getNamespaceForNetwork(network: any): 'eip155' | 'solana' | undefined {
  // EVM chains use numeric string ids, Solana uses 'solana', 'solanaDevnet', etc.
  if (typeof network.id === 'string' && /^\d+$/.test(network.id)) return 'eip155';
  if (typeof network.id === 'string' && network.id.toLowerCase().includes('solana')) return 'solana';
  return undefined;
}

function getAdaptersForNamespace(namespace: string) {
  if (namespace === 'eip155') return [alchemy];
  if (namespace === 'solana') return [solana];
  return [];
}

export function useAllTokenBalances() {
  const { address, isConnected, namespace } = useWallet();
  // Find all enabled chains for the current wallet namespace
  const enabledChains = useMemo(() =>
    networks.filter(n => getNamespaceForNetwork(n) === namespace),
    [namespace]
  );

  const queryKey = ['allTokenBalances', address, namespace];

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      if (!isConnected || !address) return [];
      let all: TokenBalance[] = [];
      for (const chain of enabledChains) {
        const ns = getNamespaceForNetwork(chain);
        if (!ns) continue;
        const adapters = getAdaptersForNamespace(ns);
        for (const adapter of adapters) {
          const idStr = String(chain.id);
          if (ns === 'eip155') {
            const balances = await adapter.getBalances(address, { id: idStr, namespace: 'eip155' });
            all = all.concat(balances);
          } else if (ns === 'solana') {
            const balances = await adapter.getBalances(address, { id: idStr, namespace: 'solana' });
            all = all.concat(balances);
          }
        }
      }
      // Deduplicate by chain+address
      const deduped: Record<string, TokenBalance> = {};
      for (const t of all) {
        deduped[`${t.chainId}:${t.address}`] = t;
      }
      const result = Object.values(deduped);
      // Persist in localStorage
      try {
        localStorage.setItem(`balances:${address}:${namespace}`, JSON.stringify({ ts: Date.now(), data: result }));
      } catch {}
      return result;
    },
    enabled: isConnected && !!address,
    staleTime: 30000,
    refetchInterval: 30000,
    initialData: () => {
      if (!isConnected || !address) return [];
      try {
        const cached = localStorage.getItem(`balances:${address}:${namespace}`);
        if (cached) {
          const { ts, data } = JSON.parse(cached);
          if (Date.now() - ts < 30000) return data;
        }
      } catch {}
      return [];
    },
  });

  return {
    balances: query.data as TokenBalance[],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
} 