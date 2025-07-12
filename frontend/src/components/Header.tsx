import { useAppKit, useAppKitState, useDisconnect } from '@reown/appkit/react'
import { networks } from '../config'
import { useWallet } from '../hooks/useWallet'
import './Header.css'

export function Header() {
  const { open } = useAppKit()
  const { selectedNetworkId } = useAppKitState()
  const { disconnect } = useDisconnect()
  const { isConnected, address, namespace } = useWallet()

  const handleConnect = (chainType: 'eip155' | 'solana') => {
    open({ view: 'Connect', namespace: chainType })
  }

  const handleDisconnect = async () => {
    try {
      await disconnect()
    } catch (error) {
      console.error('Failed to disconnect:', error)
    }
  }

  const handleNetworkSwitch = () => {
    // For now, we'll use the open method to switch networks
    // This will open the network selection modal
    open({ view: 'Networks' })
  }

  const getNetworkName = (chainId: string) => {
    const network = networks.find(n => n.id === chainId)
    return network?.name || chainId
  }

  const getChainTypeName = (namespace: string) => {
    return namespace === 'eip155' ? 'EVM' : 'Solana'
  }

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <img src="/reown.svg" alt="Athena" className="logo-img" />
          <h1>Athena</h1>
        </div>

        <div className="header-controls">
          {/* Network Selector */}
          <div className="network-selector">
            <label htmlFor="network-select">Network:</label>
            <select
              id="network-select"
              value={selectedNetworkId || ''}
              onChange={(e) => {
                const selectedNetwork = networks.find(n => n.id === e.target.value)
                if (selectedNetwork) {
                  handleNetworkSwitch()
                }
              }}
              className="network-select"
            >
              {networks.map((network) => (
                <option key={network.id} value={network.id}>
                  {network.name}
                </option>
              ))}
            </select>
          </div>

          {/* Wallet Connection */}
          <div className="wallet-section">
            {!isConnected ? (
              <div className="connect-buttons">
                <button
                  onClick={() => handleConnect('eip155')}
                  className="connect-btn evm-btn"
                >
                  Connect EVM
                </button>
                <button
                  onClick={() => handleConnect('solana')}
                  className="connect-btn solana-btn"
                >
                  Connect Solana
                </button>
              </div>
            ) : (
              <div className="wallet-info">
                <div className="wallet-details">
                  <span className="chain-type">
                    {namespace && getChainTypeName(namespace)}
                  </span>
                  <span className="address">
                    {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Unknown'}
                  </span>
                  <span className="network">
                    {selectedNetworkId && getNetworkName(selectedNetworkId)}
                  </span>
                </div>
                <button onClick={handleDisconnect} className="disconnect-btn">
                  Disconnect
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
} 