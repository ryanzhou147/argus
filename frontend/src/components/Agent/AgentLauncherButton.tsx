import { useAgentContext } from '../../context/AgentContext'

export default function AgentLauncherButton() {
  const { isPanelOpen, togglePanel, isLoading } = useAgentContext()

  return (
    <button
      onClick={togglePanel}
      className="fixed top-4 right-4 z-40 w-12 h-12 rounded-full flex items-center justify-center transition-all shadow-lg"
      style={{
        background: isPanelOpen ? '#1d4ed8' : 'rgba(30,41,59,0.95)',
        border: '1px solid',
        borderColor: isPanelOpen ? '#3b82f6' : '#334155',
      }}
      aria-label={isPanelOpen ? 'Close AI Agent' : 'Open AI Agent'}
      title="AI Globe Copilot"
    >
      {isLoading ? (
        <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      ) : (
        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      )}
    </button>
  )
}
