import { useState } from 'react'
import type { AgentResponse } from '../../types/agent'
import FinancialImpactSection from './FinancialImpactSection'
import { useAppContext } from '../../context/AppContext'

const CONFIDENCE_COLORS = {
  high: '#22c55e',
  medium: '#eab308',
  low: '#ef4444',
}

const QUERY_TYPE_LABELS: Record<string, string> = {
  event_explanation: 'Event Explanation',
  impact_analysis: 'Impact Analysis',
  connection_discovery: 'Connection Discovery',
  entity_relevance: 'Entity Relevance',
  update_request: 'Data Update',
}

interface Props {
  response: AgentResponse
}

export default function AgentAnswerView({ response }: Props) {
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const { setSelectedEventId, events } = useAppContext()
  const confColor = CONFIDENCE_COLORS[response.confidence]

  const getEventTitle = (id: string) => {
    return events.find(e => e.id === id)?.title ?? id
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs px-2 py-0.5 rounded-full border"
          style={{ color: confColor, borderColor: `${confColor}55`, backgroundColor: `${confColor}11` }}>
          {response.confidence.toUpperCase()} CONFIDENCE
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          {QUERY_TYPE_LABELS[response.query_type] ?? response.query_type}
        </span>
        {response.mode === 'fallback_web' && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800">
            External Sources
          </span>
        )}
      </div>

      {/* Caution banner */}
      {response.caution && (
        <div className="rounded-lg p-3 bg-amber-900/20 border border-amber-800/40 flex gap-2">
          <svg className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-amber-300 text-xs leading-relaxed">{response.caution}</p>
        </div>
      )}

      {/* Answer */}
      <div>
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">Analysis</div>
        <p className="text-slate-200 text-sm leading-relaxed">{response.answer}</p>
      </div>

      {/* Financial impact */}
      {response.financial_impact && (
        <FinancialImpactSection impact={response.financial_impact} />
      )}

      {/* Update result */}
      {response.update_result && (
        <div className={`rounded-lg p-3 border ${response.update_result.status === 'success' ? 'bg-green-900/20 border-green-800/40' : 'bg-red-900/20 border-red-800/40'}`}>
          <div className="flex items-center gap-1.5 mb-1">
            {response.update_result.status === 'success' ? (
              <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <span className={`text-xs font-semibold ${response.update_result.status === 'success' ? 'text-green-400' : 'text-red-400'}`}>
              {response.update_result.status === 'success' ? 'Update Successful' : 'Update Failed'}
            </span>
          </div>
          {response.update_result.field_name && (
            <p className="text-xs text-slate-400">
              Field: <span className="text-slate-200 font-mono">{response.update_result.field_name}</span>
              {response.update_result.new_value && (
                <> → <span className="text-slate-200">{response.update_result.new_value}</span></>
              )}
            </p>
          )}
          {response.update_result.message && (
            <p className="text-xs text-slate-400 mt-1">{response.update_result.message}</p>
          )}
        </div>
      )}

      {/* Related events */}
      {response.relevant_event_ids.length > 0 && (
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Relevant Events</div>
          <div className="flex flex-col gap-1.5">
            {response.relevant_event_ids.slice(0, 5).map(id => (
              <button
                key={id}
                onClick={() => setSelectedEventId(id)}
                className="text-left text-xs text-blue-400 hover:text-blue-300 bg-slate-800/60 rounded px-2.5 py-1.5 border border-slate-700/50 hover:border-slate-600 transition-colors truncate"
              >
                {getEventTitle(id)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* External sources */}
      {response.mode === 'fallback_web' && response.source_snippets.filter(s => s.type === 'external').length > 0 && (
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">External Sources</div>
          <div className="flex flex-col gap-2">
            {response.source_snippets.filter(s => s.type === 'external').map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-slate-800/60 rounded-lg p-2.5 border border-slate-700/50 hover:border-slate-500 transition-colors group"
              >
                <div className="text-xs font-semibold text-amber-400 mb-0.5">{src.source_name}</div>
                <div className="text-slate-300 text-xs leading-snug group-hover:text-white transition-colors">{src.headline}</div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning steps */}
      {response.reasoning_steps.length > 0 && (
        <div>
          <button
            onClick={() => setReasoningOpen(prev => !prev)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <svg
              className={`w-3 h-3 transition-transform ${reasoningOpen ? 'rotate-90' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Reasoning steps ({response.reasoning_steps.length})
          </button>
          {reasoningOpen && (
            <ol className="mt-2 flex flex-col gap-1 pl-4 list-decimal">
              {response.reasoning_steps.map((step, i) => (
                <li key={i} className="text-xs text-slate-400 leading-relaxed">{step}</li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}
