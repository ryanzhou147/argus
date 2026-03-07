import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AppProvider } from './context/AppContext.tsx'
import { AgentProvider } from './context/AgentContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProvider>
      <AgentProvider>
        <App />
      </AgentProvider>
    </AppProvider>
  </StrictMode>,
)
