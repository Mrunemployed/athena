'use client'


import { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { WagmiProvider, cookieToInitialState, type Config } from 'wagmi'
import { createAppKit } from '@reown/appkit/react'
import { config, networks, projectId, wagmiAdapter, solanaWeb3JsAdapter } from '../config'
import { mainnet } from '@reown/appkit/networks'

const queryClient = new QueryClient()

const metadata = {
  name: 'Athena dApp',
  description: 'Multichain DeFi Application',
  url: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173',
  icons: ['https://avatars.githubusercontent.com/u/179229932']
}

// Initialize AppKit outside the component render cycle
if (!projectId) {
  console.error("AppKit Initialization Error: Project ID is missing.")
} else {
  createAppKit({
    adapters: [wagmiAdapter, solanaWeb3JsAdapter],
    projectId: projectId!,
    networks: networks,
    defaultNetwork: mainnet,
    metadata,
    features: { analytics: true },
  })
}

interface AppKitProviderProps {
  children: ReactNode
  cookies?: string | null
}

export default function AppKitProvider({ children, cookies }: AppKitProviderProps) {
  // Calculate initial state for Wagmi SSR hydration
  const initialState = cookieToInitialState(config as Config, cookies)

  return (
    <WagmiProvider config={config as Config} initialState={initialState}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </WagmiProvider>
  )
} 