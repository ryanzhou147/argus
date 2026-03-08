import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AppProvider } from './context/AppContext.tsx'
import { AgentProvider } from './context/AgentContext.tsx'
import { UserPersonaProvider } from './context/UserPersonaContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProvider>
      <UserPersonaProvider>
        <AgentProvider>
          <App />
        </AgentProvider>
      </UserPersonaProvider>
    </AppProvider>
  </StrictMode>,
)
