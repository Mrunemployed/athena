import { createAppKit } from '@reown/appkit/react'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ActionButtonList } from './components/ActionButtonList'
import { InfoList } from './components/InfoList'
import SwapInterface from './components/SwapInterface'
import { projectId, metadata, networks, wagmiAdapter, solanaWeb3JsAdapter } from './config'
import "./App.css"
import { useState } from 'react'

const queryClient = new QueryClient()

// Create modal with single object parameter
createAppKit({
  adapters: [wagmiAdapter, solanaWeb3JsAdapter],
  projectId,
  metadata,
  networks,
  themeMode: 'dark' as const,
  features: {
    analytics: true
  },
  themeVariables: {
    '--w3m-accent': '#6366f1',
  }
})

export function App() {
  const [activeTab, setActiveTab] = useState<'wallet' | 'swap'>('swap')

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo-section">
            <img src="/reown.svg" alt="Reown" className="logo" />
            <h1 className="title">Athena Web3 Dashboard</h1>
          </div>
          <p className="subtitle">Multi-chain wallet connection and cross-chain swaps</p>
        </div>
      </header>

      <main className="main-content">
        <WagmiProvider config={wagmiAdapter.wagmiConfig}>
          <QueryClientProvider client={queryClient}>
            <div className="dashboard">
              {/* Tab Navigation */}
              <div className="tab-navigation">
                <button 
                  className={`tab-button ${activeTab === 'swap' ? 'active' : ''}`}
                  onClick={() => setActiveTab('swap')}
                >
                  Cross-Chain Swap
                </button>
                <button 
                  className={`tab-button ${activeTab === 'wallet' ? 'active' : ''}`}
                  onClick={() => setActiveTab('wallet')}
                >
                  Wallet Info
                </button>
              </div>

              {/* Tab Content */}
              {activeTab === 'swap' && (
                <SwapInterface />
              )}

              {activeTab === 'wallet' && (
                <>
                  <div className="wallet-section">
                    <div className="wallet-header">
                      <h2>Wallet Connection</h2>
                      <p>Connect your wallet to get started</p>
                    </div>
                    <div className="wallet-actions">
                      <appkit-button />
                      <ActionButtonList />
                    </div>
                  </div>

                  <div className="info-section">
                    <InfoList />
                  </div>

                  <div className="advice-section">
                    <div className="advice-card">
                      <h3>Getting Started</h3>
                      <p>
                        This projectId only works on localhost. <br/>
                        Visit <a href="https://cloud.reown.com" target="_blank" className="link-button" rel="noopener noreferrer">Reown Cloud</a> to get your own project ID.
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </QueryClientProvider>
        </WagmiProvider>
      </main>
    </div>
  )
}

export default App
