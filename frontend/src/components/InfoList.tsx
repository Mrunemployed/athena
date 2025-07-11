import { useEffect } from 'react'
import {
    useAppKitState,
    useAppKitTheme,
    useAppKitEvents,
    useAppKitAccount,
    useWalletInfo
     } from '@reown/appkit/react'

export const InfoList = () => {
    const kitTheme = useAppKitTheme();
    const state = useAppKitState();
    const {address, caipAddress, isConnected, status, embeddedWalletInfo } = useAppKitAccount();
    const eip155AccountState = useAppKitAccount({ namespace: 'eip155' })
    const solanaAccountState = useAppKitAccount({ namespace: 'solana' })
    const events = useAppKitEvents()
    const { walletInfo } = useWalletInfo()

    useEffect(() => {
        console.log("Events: ", events);
    }, [events]);

  return (
    <>
        <div className="card">
            <h2>Wallet Addresses</h2>
            <pre>
                <strong>EVM Address:</strong> {eip155AccountState.address || 'Not connected'}<br />
                <strong>Solana Address:</strong> {solanaAccountState.address || 'Not connected'}<br />
            </pre>
        </div>
        
        <div className="card">
            <h2>Connection Status</h2>
            <pre>
                <strong>Address:</strong> {address || 'Not connected'}<br />
                <strong>CAIP Address:</strong> {caipAddress || 'Not connected'}<br />
                <strong>Connected:</strong> {isConnected ? '✅ Yes' : '❌ No'}<br />
                <strong>Status:</strong> {status}<br />
                <strong>Account Type:</strong> {embeddedWalletInfo?.accountType || 'N/A'}<br />
                {embeddedWalletInfo?.user?.email && (`<strong>Email:</strong> ${embeddedWalletInfo?.user?.email}\n`)}
                {embeddedWalletInfo?.user?.username && (`<strong>Username:</strong> ${embeddedWalletInfo?.user?.username}\n`)}
            </pre>
        </div>

        <div className="card">
            <h2>Theme Settings</h2>
            <pre>
                <strong>Theme Mode:</strong> {kitTheme.themeMode}<br />
            </pre>
        </div>

        <div className="card">
            <h2>App State</h2>
            <pre>
                <strong>Active Chain:</strong> {state.activeChain || 'None'}<br />
                <strong>Loading:</strong> {state.loading ? '🔄 Yes' : '✅ No'}<br />
                <strong>Modal Open:</strong> {state.open ? '🔓 Yes' : '🔒 No'}<br />
                <strong>Selected Network ID:</strong> {state.selectedNetworkId?.toString() || 'None'}<br />
            </pre>
        </div>

        <div className="card">
            <h2>Wallet Information</h2>
            <pre>
                <strong>Wallet Details:</strong><br />
                {JSON.stringify(walletInfo, null, 2)}
            </pre>
        </div>
    </>
  )
}
