import { useAppKitAccount, useAppKitState } from '@reown/appkit/react'

export interface WalletState {
  address: string | undefined
  chainId: string | undefined
  isConnected: boolean
  namespace: 'eip155' | 'solana' | undefined
}

export function useWallet(namespace?: 'eip155' | 'solana'): WalletState {
  const { address, isConnected, caipAddress } = useAppKitAccount({ namespace })
  const { selectedNetworkId } = useAppKitState()

  // Extract chainId from caipAddress or selectedNetworkId
  const chainId = caipAddress ? caipAddress.split(':')[1] : selectedNetworkId

  return {
    address,
    chainId,
    isConnected,
    namespace: namespace || (caipAddress ? (caipAddress.startsWith('eip155:') ? 'eip155' : 'solana') : undefined)
  }
}

// Convenience hooks for specific chains
export function useEVMWallet(): WalletState {
  return useWallet('eip155')
}

export function useSolanaWallet(): WalletState {
  return useWallet('solana')
} 