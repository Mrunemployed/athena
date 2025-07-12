import React from 'react';
import { useAllTokenBalances } from '../balances/useAllTokenBalances';
import './AssetsPanel.css';

export function AssetsPanel() {
  const { balances, isLoading, error } = useAllTokenBalances();

  if (isLoading) {
    return <div className="assets-panel">Loading balances...</div>;
  }
  if (error) {
    return <div className="assets-panel">Error loading balances.</div>;
  }
  if (!balances || balances.length === 0) {
    return <div className="assets-panel">No assets detected on this chain.</div>;
  }

  return (
    <div className="assets-panel">
      {balances.map((token) => (
        <div className="asset-card" key={`${token.chainId}:${token.address}`}>
          <div className="asset-logo">
            {token.logoURI ? (
              <img src={token.logoURI} alt={token.symbol} />
            ) : (
              <div className="asset-logo-fallback">{token.symbol.slice(0, 3)}</div>
            )}
          </div>
          <div className="asset-info">
            <div className="asset-symbol">{token.symbol}</div>
            <div className="asset-chain">{token.chainName}</div>
            <div className="asset-amount">{formatAmount(token.amount, token.decimals)}</div>
            {token.usdValue !== undefined && (
              <div className="asset-usd">${token.usdValue.toFixed(2)}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatAmount(amount: bigint, decimals: number) {
  return (Number(amount) / 10 ** decimals).toLocaleString(undefined, { maximumFractionDigits: 6 });
} 