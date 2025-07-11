import React, { useState, useEffect } from 'react'
import { useAppKitAccount, useAppKitAccount as useAppKitAccountEVM, useAppKitAccount as useAppKitAccountSolana } from '@reown/appkit/react'

interface Chain {
  id: number
  name: string
}

interface Token {
  symbol: string
  address: string
  decimals: number
  logoURI?: string
}

interface QuoteResponse {
  status: string
  quote: any
  swap_id: string
  steps: any[]
  message?: string
}

interface SwapStatus {
  status: string
  tx_hash?: string
  confirmations?: number
  chain_id?: number
}

interface WalletAddress {
  address: string
  chainId: number
  namespace: string
  chainName: string
}

const SwapInterface: React.FC = () => {
  const { address, isConnected } = useAppKitAccount()
  const evmAccount = useAppKitAccountEVM({ namespace: 'eip155' })
  const solanaAccount = useAppKitAccountSolana({ namespace: 'solana' })
  
  // State for form inputs
  const [sourceChain, setSourceChain] = useState<string>('1') // Ethereum mainnet
  const [destinationChain, setDestinationChain] = useState<string>('137') // Polygon
  const [tokenIn, setTokenIn] = useState<string>('ETH')
  const [tokenOut, setTokenOut] = useState<string>('USDT')
  const [amount, setAmount] = useState<string>('')
  const [receiverAddress, setReceiverAddress] = useState<string>('')
  const [selectedSourceAddress, setSelectedSourceAddress] = useState<string>('')
  
  // State for available options
  const [chains, setChains] = useState<Chain[]>([])
  const [sourceTokens, setSourceTokens] = useState<Token[]>([])
  const [destinationTokens, setDestinationTokens] = useState<Token[]>([])
  
  // State for swap process
  const [quote, setQuote] = useState<any>(null)
  const [swapId, setSwapId] = useState<string>('')
  const [swapStatus, setSwapStatus] = useState<SwapStatus | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isLoadingChains, setIsLoadingChains] = useState<boolean>(true)
  const [isLoadingTokens, setIsLoadingTokens] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://medusaapi.tinyaibots.com'

  // Get all connected wallet addresses
  const getConnectedAddresses = (): WalletAddress[] => {
    const addresses: WalletAddress[] = []
    
    console.log('getConnectedAddresses - evmAccount:', evmAccount)
    console.log('getConnectedAddresses - solanaAccount:', solanaAccount)
    console.log('getConnectedAddresses - general address:', address)
    console.log('getConnectedAddresses - isConnected:', isConnected)
    
    // Add EVM addresses
    if (evmAccount.address) {
      addresses.push({
        address: evmAccount.address,
        chainId: 1, // Default to Ethereum mainnet
        namespace: 'eip155',
        chainName: 'Ethereum'
      })
    }
    
    // Add Solana address - try multiple approaches
    let solanaAddr = null
    
    // Try from solanaAccount hook
    if (solanaAccount.address) {
      solanaAddr = solanaAccount.address
      console.log('Found Solana address from solanaAccount:', solanaAddr)
    }
    
    // Try from general address if it looks like Solana
    if (!solanaAddr && address && address.length > 40) {
      solanaAddr = address
      console.log('Found Solana address from general address:', solanaAddr)
    }
    
    // If we found a Solana address, add it
    if (solanaAddr) {
      addresses.push({
        address: solanaAddr,
        chainId: 792703809, // Solana chain ID from Relay API
        namespace: 'solana',
        chainName: 'Solana'
      })
    }
    
    // Temporary fallback: if no Solana address found but we're connected, add the known address
    if (!solanaAddr && isConnected && address && address.length > 40) {
      console.log('Adding fallback Solana address:', address)
      addresses.push({
        address: address,
        chainId: 792703809, // Solana chain ID from Relay API
        namespace: 'solana',
        chainName: 'Solana'
      })
    }
    
    console.log('getConnectedAddresses - returning addresses:', addresses)
    return addresses
  }

  // Get available addresses for a specific chain
  const getAddressesForChain = (chainId: string): WalletAddress[] => {
    const addresses = getConnectedAddresses()
    const chainIdNum = parseInt(chainId)
    
    console.log('getAddressesForChain called with chainId:', chainId, 'chainIdNum:', chainIdNum)
    console.log('All available addresses:', addresses)
    
    // Filter addresses based on chain type
    // Solana chain ID from Relay API is 792703809
    if (chainIdNum === 792703809) {
      // Solana chain
      const solanaAddresses = addresses.filter(addr => addr.namespace === 'solana')
      console.log('Filtered Solana addresses:', solanaAddresses)
      return solanaAddresses
    } else {
      // EVM chains
      const evmAddresses = addresses.filter(addr => addr.namespace === 'eip155')
      console.log('Filtered EVM addresses:', evmAddresses)
      return evmAddresses
    }
  }

  // Auto-select appropriate address when chain changes
  useEffect(() => {
    const availableAddresses = getAddressesForChain(sourceChain)
    if (availableAddresses.length > 0) {
      setSelectedSourceAddress(availableAddresses[0].address)
    } else {
      setSelectedSourceAddress('')
    }
  }, [sourceChain, evmAccount.address, solanaAccount.address])

  // Load supported chains
  useEffect(() => {
    const loadChains = async () => {
      setIsLoadingChains(true)
      setError('')
      
      // First check if backend is accessible
      try {
        console.log('Checking backend health...')
        const healthResponse = await fetch(`${API_BASE_URL}/`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
        console.log('Health check status:', healthResponse.status)
      } catch (err) {
        console.warn('Health check failed:', err)
      }
      
      const retryLoad = async (attempts = 3) => {
        for (let attempt = 1; attempt <= attempts; attempt++) {
          try {
            console.log(`Loading chains from: ${API_BASE_URL}/chains (attempt ${attempt}/${attempts})`)
            const response = await fetch(`${API_BASE_URL}/chains`, {
              method: 'GET',
              headers: {
                'Content-Type': 'application/json',
              },
            })
            console.log('Chains response status:', response.status)
            
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}: ${response.statusText}`)
            }
            
            const data = await response.json()
            console.log('Chains data:', data)
            
            if (data.chains && Array.isArray(data.chains)) {
              // Ensure all chains have valid id and name properties
              const validChains = data.chains.filter((chain: any) => 
                chain && (chain.id !== undefined || chain.chainId !== undefined) && (chain.name || chain.displayName)
              ).map((chain: any) => ({
                id: chain.id || chain.chainId,
                name: chain.name || chain.displayName || `Chain ${chain.id || chain.chainId}`
              }))
              setChains(validChains)
              console.log(`Successfully loaded ${validChains.length} chains`)
              return // Success, exit retry loop
            } else {
              throw new Error('Invalid chains data structure')
            }
          } catch (err) {
            console.error(`Failed to load chains (attempt ${attempt}/${attempts}):`, err)
            if (attempt === attempts) {
              setError('Failed to load supported chains: ' + (err instanceof Error ? err.message : 'Network error'))
            } else {
              // Wait before retrying
              await new Promise(resolve => setTimeout(resolve, 1000 * attempt))
            }
          }
        }
      }
      
      await retryLoad()
      setIsLoadingChains(false)
    }
    loadChains()
  }, [API_BASE_URL])

  // Load tokens for source chain
  useEffect(() => {
    const loadSourceTokens = async () => {
      if (!sourceChain) return
      setIsLoadingTokens(true)
      try {
        console.log('Loading source tokens from:', `${API_BASE_URL}/tokens/${sourceChain}`)
        const response = await fetch(`${API_BASE_URL}/tokens/${sourceChain}`)
        console.log('Source tokens response status:', response.status)
        const data = await response.json()
        console.log('Source tokens data:', data)
        if (data.tokens && Array.isArray(data.tokens)) {
          // Ensure all tokens have valid properties
          const validTokens = data.tokens.filter((token: any) => 
            token && token.symbol && token.address
          )
          setSourceTokens(validTokens)
        }
      } catch (err) {
        console.error('Failed to load source tokens:', err)
        setError('Failed to load tokens for source chain: ' + (err instanceof Error ? err.message : 'Network error'))
      } finally {
        setIsLoadingTokens(false)
      }
    }
    loadSourceTokens()
  }, [sourceChain, API_BASE_URL])

  // Load tokens for destination chain
  useEffect(() => {
    const loadDestinationTokens = async () => {
      if (!destinationChain) return
      setIsLoadingTokens(true)
      try {
        console.log('Loading destination tokens from:', `${API_BASE_URL}/tokens/${destinationChain}`)
        const response = await fetch(`${API_BASE_URL}/tokens/${destinationChain}`)
        console.log('Destination tokens response status:', response.status)
        const data = await response.json()
        console.log('Destination tokens data:', data)
        if (data.tokens && Array.isArray(data.tokens)) {
          // Ensure all tokens have valid properties
          const validTokens = data.tokens.filter((token: any) => 
            token && token.symbol && token.address
          )
          setDestinationTokens(validTokens)
        }
      } catch (err) {
        console.error('Failed to load destination tokens:', err)
        setError('Failed to load tokens for destination chain: ' + (err instanceof Error ? err.message : 'Network error'))
      } finally {
        setIsLoadingTokens(false)
      }
    }
    loadDestinationTokens()
  }, [destinationChain, API_BASE_URL])

  // Set receiver address to connected wallet if available
  useEffect(() => {
    if (isConnected && address && !receiverAddress) {
      setReceiverAddress(address)
    }
  }, [isConnected, address, receiverAddress])

  // Get quote for the swap
  const getQuote = async () => {
    if (!isConnected || !selectedSourceAddress || !amount || !receiverAddress) {
      setError('Please connect wallet, select source address, and fill all fields')
      return
    }

    setIsLoading(true)
    setError('')
    setQuote(null)

    try {
      const url = new URL(`${API_BASE_URL}/quote`)
      url.searchParams.append('source_chain', sourceChain)
      url.searchParams.append('destination_chain', destinationChain)
      url.searchParams.append('token_in', tokenIn)
      url.searchParams.append('token_out', tokenOut)
      url.searchParams.append('amount', amount)
      url.searchParams.append('user_address', selectedSourceAddress)
      url.searchParams.append('receiver_address', receiverAddress)

      const response = await fetch(url.toString())
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const quoteData: QuoteResponse = await response.json()

      if (quoteData.status === 'success') {
        setQuote(quoteData.quote)
        setSwapId(quoteData.swap_id)
      } else {
        setError('Failed to get quote: ' + (quoteData.message || 'Unknown error'))
      }
    } catch (err) {
      setError('Failed to get quote: ' + (err instanceof Error ? err.message : 'Network error'))
      console.error('Quote error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Execute the swap
  const executeSwap = async () => {
    if (!swapId) {
      setError('No swap quote available')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/swap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user: selectedSourceAddress,
          source_chain: sourceChain,
          destination_chain: destinationChain,
          token_in: tokenIn,
          token_out: tokenOut,
          amount: amount,
          receiver: receiverAddress,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      if (data.status === 'success') {
        setSwapId(data.swap_id)
        // Start polling for status
        pollSwapStatus(data.swap_id)
      } else {
        setError('Failed to execute swap: ' + (data.message || 'Unknown error'))
      }
    } catch (err) {
      setError('Failed to execute swap: ' + (err instanceof Error ? err.message : 'Network error'))
      console.error('Swap execution error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Poll swap status
  const pollSwapStatus = async (id: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/swap/${id}/status`)
        const status: SwapStatus = await response.json()
        setSwapStatus(status)
        
        if (status.status === 'completed' || status.status === 'failed') {
          return // Stop polling
        }
        
        // Continue polling
        setTimeout(poll, 5000)
      } catch (err) {
        console.error('Status polling error:', err)
      }
    }
    
    poll()
  }

  // Format amount for display
  const formatAmount = (amount: string, decimals: number = 6) => {
    const num = parseFloat(amount)
    if (isNaN(num)) return '0'
    return num.toFixed(decimals)
  }

  // Get estimated output from quote
  const getEstimatedOutput = () => {
    if (!quote?.result?.destinationAmount) return '0'
    return formatAmount(quote.result.destinationAmount, 6)
  }

  // Get gas estimate from quote
  const getGasEstimate = () => {
    if (!quote?.result?.gasEstimate) return '0'
    return formatAmount(quote.result.gasEstimate, 6)
  }

  // Get available addresses for current source chain
  const availableSourceAddresses = getAddressesForChain(sourceChain)

  return (
    <div className="swap-interface">
      <div className="swap-header">
        <h2>Cross-Chain Swap</h2>
        <p>Swap tokens across different blockchain networks</p>
      </div>

      {!isConnected && (
        <div className="wallet-notice">
          <p>Please connect your wallet to start swapping</p>
        </div>
      )}

      {isLoadingChains && (
        <div className="loading-notice">
          <p>🔄 Loading supported chains and tokens...</p>
        </div>
      )}

      <div className="swap-form">
        {/* Source Chain and Token */}
        <div className="swap-section">
          <h3>From</h3>
          <div className="chain-token-row">
            <div className="chain-selector">
              <label>Chain</label>
              <select 
                value={sourceChain} 
                onChange={(e) => setSourceChain(e.target.value)}
                disabled={isLoading || isLoadingChains}
              >
                {isLoadingChains ? (
                  <option>Loading chains...</option>
                ) : (
                  chains.map(chain => (
                    <option key={chain.id} value={chain.id}>
                      {chain.name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="token-selector">
              <label>Token</label>
              <select 
                value={tokenIn} 
                onChange={(e) => setTokenIn(e.target.value)}
                disabled={isLoading || isLoadingTokens}
              >
                {isLoadingTokens ? (
                  <option>Loading tokens...</option>
                ) : (
                  sourceTokens.map(token => (
                    <option key={token.symbol} value={token.symbol}>
                      {token.symbol}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="amount-input">
              <label>Amount</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.0"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Source Address Selector */}
          {isConnected && availableSourceAddresses.length > 0 && (
            <div className="address-selector">
              <label>Source Address</label>
              <select 
                value={selectedSourceAddress} 
                onChange={(e) => setSelectedSourceAddress(e.target.value)}
                disabled={isLoading}
              >
                {availableSourceAddresses.map(addr => (
                  <option key={addr.address} value={addr.address}>
                    {addr.chainName}: {addr.address.slice(0, 6)}...{addr.address.slice(-4)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {isConnected && availableSourceAddresses.length === 0 && (
            <div className="address-warning">
              <p>⚠️ No compatible wallet addresses found for this chain. Please connect a wallet that supports {chains.find(c => c.id?.toString() === sourceChain)?.name || 'this chain'}.</p>
            </div>
          )}
        </div>

        {/* Swap Direction Arrow */}
        <div className="swap-direction">
          <div className="arrow">↓</div>
        </div>

        {/* Destination Chain and Token */}
        <div className="swap-section">
          <h3>To</h3>
          <div className="chain-token-row">
            <div className="chain-selector">
              <label>Chain</label>
              <select 
                value={destinationChain} 
                onChange={(e) => setDestinationChain(e.target.value)}
                disabled={isLoading || isLoadingChains}
              >
                {isLoadingChains ? (
                  <option>Loading chains...</option>
                ) : (
                  chains.map(chain => (
                    <option key={chain.id} value={chain.id}>
                      {chain.name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="token-selector">
              <label>Token</label>
              <select 
                value={tokenOut} 
                onChange={(e) => setTokenOut(e.target.value)}
                disabled={isLoading || isLoadingTokens}
              >
                {isLoadingTokens ? (
                  <option>Loading tokens...</option>
                ) : (
                  destinationTokens.map(token => (
                    <option key={token.symbol} value={token.symbol}>
                      {token.symbol}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="amount-display">
              <label>You'll Receive</label>
              <div className="estimated-amount">
                {quote ? getEstimatedOutput() : '0.0'} {tokenOut}
              </div>
            </div>
          </div>
        </div>

        {/* Receiver Address */}
        <div className="receiver-section">
          <label>Receiver Address</label>
          <input
            type="text"
            value={receiverAddress}
            onChange={(e) => setReceiverAddress(e.target.value)}
            placeholder="Enter receiver address"
            disabled={isLoading}
          />
        </div>

        {/* Quote Details */}
        {quote && (
          <div className="quote-details">
            <h3>Quote Details</h3>
            <div className="quote-info">
              <div className="quote-row">
                <span>Estimated Output:</span>
                <span>{getEstimatedOutput()} {tokenOut}</span>
              </div>
              <div className="quote-row">
                <span>Gas Estimate:</span>
                <span>{getGasEstimate()}</span>
              </div>
              <div className="quote-row">
                <span>Route:</span>
                <span>{quote.result?.route?.length || 0} steps</span>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="swap-actions">
          {!quote ? (
            <button 
              onClick={getQuote} 
              disabled={isLoading || !isConnected || !selectedSourceAddress}
              className="primary"
            >
              {isLoading ? 'Getting Quote...' : 'Get Quote'}
            </button>
          ) : (
            <button 
              onClick={executeSwap} 
              disabled={isLoading}
              className="primary"
            >
              {isLoading ? 'Executing Swap...' : 'Execute Swap'}
            </button>
          )}
        </div>

        {/* Swap Status */}
        {swapStatus && (
          <div className="swap-status">
            <h3>Swap Status</h3>
            <div className="status-info">
              <div className="status-row">
                <span>Status:</span>
                <span className={`status-${swapStatus.status}`}>
                  {swapStatus.status}
                </span>
              </div>
              {swapStatus.tx_hash && (
                <div className="status-row">
                  <span>Transaction:</span>
                  <a 
                    href={`https://etherscan.io/tx/${swapStatus.tx_hash}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {swapStatus.tx_hash.slice(0, 10)}...{swapStatus.tx_hash.slice(-8)}
                  </a>
                </div>
              )}
              {swapStatus.confirmations !== undefined && (
                <div className="status-row">
                  <span>Confirmations:</span>
                  <span>{swapStatus.confirmations}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default SwapInterface 