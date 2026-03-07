import { useState } from 'react'
import type { AgentResponse } from '../../types/agent'
import FinancialImpactSection from './FinancialImpactSection'
import { useAppContext } from '../../context/AppContext'

const CONFIDENCE_COLORS = {
  high: '#4a7a4a',
  medium: '#7a6a30',
  low: '#7a3a3a',
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
        <span
          className="text-xs px-2 py-0.5"
          style={{ color: confColor, border: `1px solid ${confColor}55`, background: `${confColor}11` }}
        >
          {response.confidence.toUpperCase()} CONFIDENCE
        </span>
        <span
          className="text-xs px-2 py-0.5"
          style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
        >
          {QUERY_TYPE_LABELS[response.query_type] ?? response.query_type}
        </span>
        {response.mode === 'fallback_web' && (
          <span className="text-xs px-2 py-0.5" style={{ background: '#2a1a00', color: '#8a6a30', border: '1px solid #3a2800' }}>
            External Sources
          </span>
        )}
      </div>

      {/* Caution banner */}
      {response.caution && (
        <div className="p-3 flex gap-2" style={{ background: 'var(--bg-raised)', border: '1px solid #3a2800', borderLeft: '2px solid #7a5a20' }}>
          <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#8a6a30' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-xs leading-relaxed" style={{ color: '#7a6030' }}>{response.caution}</p>
        </div>
      )}

      {/* Answer */}
      <div>
        <div className="text-xs uppercase tracking-widest mb-1.5" style={{ color: 'var(--text-muted)' }}>Analysis</div>
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{response.answer}</p>
      </div>

      {/* Financial impact */}
      {response.financial_impact && (
        <FinancialImpactSection impact={response.financial_impact} />
      )}

      {/* Update result */}
      {response.update_result && (
        <div
          className="p-3"
          style={{
            background: 'var(--bg-raised)',
            border: `1px solid ${response.update_result.status === 'success' ? '#1a3a1a' : '#3a1a1a'}`,
            borderLeft: `2px solid ${response.update_result.status === 'success' ? '#3a6a3a' : '#6a3a3a'}`,
          }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs font-bold" style={{ color: response.update_result.status === 'success' ? '#4a7a4a' : '#7a4a4a' }}>
              {response.update_result.status === 'success' ? '✓ Update Successful' : '✗ Update Failed'}
            </span>
          </div>
          {response.update_result.field_name && (
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Field: <span style={{ color: 'var(--text-primary)' }}>{response.update_result.field_name}</span>
              {response.update_result.new_value && (
                <> → <span style={{ color: 'var(--text-primary)' }}>{response.update_result.new_value}</span></>
              )}
            </p>
          )}
          {response.update_result.message && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{response.update_result.message}</p>
          )}
        </div>
      )}

      {/* Related events */}
      {response.relevant_event_ids.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Relevant Events</div>
          <div className="flex flex-col gap-1">
            {response.relevant_event_ids.slice(0, 5).map(id => (
              <button
                key={id}
                onClick={() => setSelectedEventId(id)}
                className="text-left text-xs px-2.5 py-1.5 transition-colors truncate"
                style={{ color: 'var(--text-secondary)', background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
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
          <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>External Sources</div>
          <div className="flex flex-col gap-1.5">
            {response.source_snippets.filter(s => s.type === 'external').map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 transition-colors"
                style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                <div className="text-xs font-bold mb-0.5" style={{ color: '#7a6030' }}>{src.source_name}</div>
                <div className="text-xs leading-snug" style={{ color: 'var(--text-secondary)' }}>{src.headline}</div>
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
            className="flex items-center gap-1.5 text-xs transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
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
                <li key={i} className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>{step}</li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}
