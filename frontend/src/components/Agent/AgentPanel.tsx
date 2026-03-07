import { useState, useCallback, useEffect, useRef } from 'react'
import { useAgentContext } from '../../context/AgentContext'
import { useAppContext } from '../../context/AppContext'
import AgentAnswerView from './AgentAnswerView'

export default function AgentPanel() {
  const { isPanelOpen, togglePanel, isLoading, agentResponse, error, submitQuery } = useAgentContext()
  const { stopAutoSpin } = useAppContext()
  const [inputValue, setInputValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isPanelOpen) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isPanelOpen])

  const handleSubmit = useCallback(async () => {
    const q = inputValue.trim()
    if (!q || isLoading) return
    stopAutoSpin()
    setInputValue('')
    await submitQuery(q)
  }, [inputValue, isLoading, submitQuery, stopAutoSpin])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const exampleQueries = [
    'Why did the Red Sea shipping disruption happen?',
    'What is the financial impact of the OPEC production cut on Canada?',
    'What events are related to the semiconductor export controls?',
  ]

  return (
    <div
      className="fixed top-0 left-0 h-full z-30 pointer-events-none"
      style={{ width: '420px', maxWidth: '100vw' }}
    >
      <div
        className="h-full w-full pointer-events-auto flex flex-col"
        style={{
          background: 'rgba(10,15,28,0.97)',
          borderRight: '1px solid #1e293b',
          transform: isPanelOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 flex-shrink-0">
          <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-sm font-semibold text-white">AI Globe Copilot</span>
          <span className="text-xs text-slate-500 ml-1">Powered by Gemini</span>
          <button
            onClick={togglePanel}
            className="ml-auto w-7 h-7 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!agentResponse && !isLoading && !error && (
            <div className="flex flex-col gap-4">
              <p className="text-slate-400 text-sm leading-relaxed">
                Ask me anything about global events and their impact on Canada. I'll navigate the globe to show you the relevant events.
              </p>
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Try asking</div>
                <div className="flex flex-col gap-2">
                  {exampleQueries.map(q => (
                    <button
                      key={q}
                      onClick={() => setInputValue(q)}
                      className="text-left text-xs text-slate-400 hover:text-slate-200 bg-slate-800/60 rounded-lg px-3 py-2 border border-slate-700/50 hover:border-slate-600 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Analyzing global events...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="rounded-lg p-3 bg-red-900/20 border border-red-800/40">
              <p className="text-red-400 text-sm">Failed to get agent response.</p>
              <p className="text-red-500 text-xs mt-1">{error}</p>
            </div>
          )}

          {agentResponse && !isLoading && (
            <AgentAnswerView response={agentResponse} />
          )}
        </div>

        {/* Input area */}
        <div className="px-4 py-3 border-t border-slate-800 flex-shrink-0">
          <div className="flex gap-2 items-center">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about global events..."
              disabled={isLoading}
              className="flex-1 bg-slate-800 text-white text-sm px-3 py-2 rounded-lg border border-slate-700 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || isLoading}
              className="w-9 h-9 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors flex-shrink-0"
              aria-label="Submit query"
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
