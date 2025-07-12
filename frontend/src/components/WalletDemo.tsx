import { useAppKit } from '@reown/appkit/react'
import { useWallet, useEVMWallet, useSolanaWallet } from '../hooks/useWallet'
import './WalletDemo.css'

export function WalletDemo() {
  const { open } = useAppKit()
  const { isConnected, address, chainId, namespace } = useWallet()
  const evmWallet = useEVMWallet()
  const solanaWallet = useSolanaWallet()

  const handleConnectEVM = () => {
    open({ view: 'Connect', namespace: 'eip155' })
  }

  const handleConnectSolana = () => {
    open({ view: 'Connect', namespace: 'solana' })
  }

  const getChainTypeName = (namespace: string) => {
    return namespace === 'eip155' ? 'EVM' : 'Solana'
  }

  return (
    <div className="wallet-demo">
      <div className="demo-header">
        <h2>Wallet & Multichain Connect Demo</h2>
        <p>Connect with MetaMask, switch to Phantom, switch back—all without reloading the page.</p>
      </div>

      <div className="demo-content">
        <div className="connection-status">
          <h3>Connection Status</h3>
          <div className="status-grid">
            <div className="status-card">
              <h4>Overall Status</h4>
              <p>Connected: <span className={isConnected ? 'connected' : 'disconnected'}>{isConnected ? 'Yes' : 'No'}</span></p>
              {isConnected && (
                <>
                  <p>Chain Type: <span className="chain-type">{namespace && getChainTypeName(namespace)}</span></p>
                  <p>Address: <span className="address">{address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Unknown'}</span></p>
                  <p>Chain ID: <span className="chain-id">{chainId || 'Unknown'}</span></p>
                </>
              )}
            </div>

            <div className="status-card">
              <h4>EVM Wallet</h4>
              <p>Connected: <span className={evmWallet.isConnected ? 'connected' : 'disconnected'}>{evmWallet.isConnected ? 'Yes' : 'No'}</span></p>
              {evmWallet.isConnected && (
                <>
                  <p>Address: <span className="address">{evmWallet.address ? `${evmWallet.address.slice(0, 6)}...${evmWallet.address.slice(-4)}` : 'Unknown'}</span></p>
                  <p>Chain ID: <span className="chain-id">{evmWallet.chainId || 'Unknown'}</span></p>
                </>
              )}
            </div>

            <div className="status-card">
              <h4>Solana Wallet</h4>
              <p>Connected: <span className={solanaWallet.isConnected ? 'connected' : 'disconnected'}>{solanaWallet.isConnected ? 'Yes' : 'No'}</span></p>
              {solanaWallet.isConnected && (
                <>
                  <p>Address: <span className="address">{solanaWallet.address ? `${solanaWallet.address.slice(0, 6)}...${solanaWallet.address.slice(-4)}` : 'Unknown'}</span></p>
                  <p>Chain ID: <span className="chain-id">{solanaWallet.chainId || 'Unknown'}</span></p>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="demo-actions">
          <h3>Try It Out</h3>
          <div className="action-buttons">
            <button onClick={handleConnectEVM} className="demo-btn evm-btn">
              Connect MetaMask (EVM)
            </button>
            <button onClick={handleConnectSolana} className="demo-btn solana-btn">
              Connect Phantom (Solana)
            </button>
          </div>
          
          <div className="demo-instructions">
            <h4>Demo Instructions:</h4>
            <ol>
              <li>Click "Connect MetaMask" to connect your EVM wallet</li>
              <li>Switch to a different network using the network selector in the header</li>
              <li>Click "Connect Phantom" to connect your Solana wallet</li>
              <li>Switch between networks - notice the connection persists</li>
              <li>Refresh the page - your connection should remain active</li>
            </ol>
          </div>
        </div>

        <div className="features-showcase">
          <h3>Sprint 1 Features</h3>
          <div className="features-grid">
            <div className="feature-card">
              <h4>✅ AppKitProvider</h4>
              <p>Wired with both WagmiAdapter (EVM) and SolanaAdapter</p>
            </div>
            <div className="feature-card">
              <h4>✅ Network Selector</h4>
              <p>Header includes a dropdown to switch between all enabled chains</p>
            </div>
            <div className="feature-card">
              <h4>✅ Custom useWallet() Hook</h4>
              <p>Exposes address, chainId, and isConnected for both chains</p>
            </div>
            <div className="feature-card">
              <h4>✅ Session Persistence</h4>
              <p>Refresh keeps the connection alive using cookie storage</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 