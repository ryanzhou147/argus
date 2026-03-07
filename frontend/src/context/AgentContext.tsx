import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { postAgentQuery } from '../api/client'
import type { AgentResponse, HighlightRelationship } from '../types/agent'

interface AgentContextValue {
  isPanelOpen: boolean
  togglePanel: () => void
  currentQuery: string
  setCurrentQuery: (q: string) => void
  isLoading: boolean
  agentResponse: AgentResponse | null
  error: string | null
  activeHighlights: HighlightRelationship[]
  activePulseIds: string[]
  activeNavigationPlan: AgentResponse['navigation_plan']
  submitQuery: (query: string) => Promise<void>
  clearAgentState: () => void
}

const AgentContext = createContext<AgentContextValue | null>(null)

export function AgentProvider({ children }: { children: ReactNode }) {
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [currentQuery, setCurrentQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentResponse, setAgentResponse] = useState<AgentResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeHighlights, setActiveHighlights] = useState<HighlightRelationship[]>([])
  const [activePulseIds, setActivePulseIds] = useState<string[]>([])
  const [activeNavigationPlan, setActiveNavigationPlan] = useState<AgentResponse['navigation_plan']>(null)

  const togglePanel = useCallback(() => {
    setIsPanelOpen(prev => !prev)
  }, [])

  const clearAgentState = useCallback(() => {
    setAgentResponse(null)
    setActiveHighlights([])
    setActivePulseIds([])
    setActiveNavigationPlan(null)
    setError(null)
  }, [])

  const submitQuery = useCallback(async (query: string) => {
    if (!query.trim()) return

    // Clear prior highlights before new query
    clearAgentState()
    setIsLoading(true)
    setCurrentQuery(query)

    try {
      const response = await postAgentQuery(query)
      setAgentResponse(response)
      setActiveHighlights(response.highlight_relationships)
      setActivePulseIds(response.navigation_plan?.pulse_event_ids ?? [])
      setActiveNavigationPlan(response.navigation_plan)
    } catch (e) {
      setError(String(e))
    } finally {
      setIsLoading(false)
    }
  }, [clearAgentState])

  return (
    <AgentContext.Provider
      value={{
        isPanelOpen,
        togglePanel,
        currentQuery,
        setCurrentQuery,
        isLoading,
        agentResponse,
        error,
        activeHighlights,
        activePulseIds,
        activeNavigationPlan,
        submitQuery,
        clearAgentState,
      }}
    >
      {children}
    </AgentContext.Provider>
  )
}

export function useAgentContext(): AgentContextValue {
  const ctx = useContext(AgentContext)
  if (!ctx) throw new Error('useAgentContext must be used inside AgentProvider')
  return ctx
}
