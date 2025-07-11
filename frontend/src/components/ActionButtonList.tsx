import { useDisconnect, useAppKit, useAppKitNetwork  } from '@reown/appkit/react'
import { networks } from '../config'

export const ActionButtonList = () => {
    const { disconnect } = useDisconnect();
    const { open } = useAppKit();
    const { switchNetwork } = useAppKitNetwork();

    const handleDisconnect = async () => {
      try {
        await disconnect();
      } catch (error) {
        console.error("Failed to disconnect:", error);
      }
    };
    
  return (
    <div className="action-buttons">
        <button onClick={() => open({ view: 'Connect', namespace: 'eip155' })}>
          Connect EVM Wallet
        </button>
        <button className="secondary" onClick={() => open({ view: 'Connect', namespace: 'solana' })}>
          Connect Solana Wallet
        </button>
        <button className="danger" onClick={handleDisconnect}>
          Disconnect
        </button>
        <button onClick={() => switchNetwork(networks[1]) }>
          Switch Network
        </button>
    </div>
  )
}
