import AppKitProvider from './context/AppKitProvider'
import { Header } from './components/Header'
import { WalletDemo } from './components/WalletDemo'
import { ActionButtonList } from './components/ActionButtonList'
import { InfoList } from './components/InfoList'
import "./App.css"

export function App() {
  return (
    <AppKitProvider>
      <div className="app">
        <Header />
        <main className="main-content">
          <WalletDemo />
          <div className="legacy-components">
            <h2>Legacy Components (for reference)</h2>
            <ActionButtonList />
            <InfoList />
          </div>
        </main>
      </div>
    </AppKitProvider>
  )
}

export default App
