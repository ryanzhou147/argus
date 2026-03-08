import { useState, useMemo } from 'react'
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

// Parse answer text into text segments and citation refs
// Returns array of { type: 'text', value: string } | { type: 'cite', id: string, index: number }
type Segment = { type: 'text'; value: string } | { type: 'cite'; id: string; index: number }

function parseAnswerSegments(answer: string, citedMap: Record<string, string>): { segments: Segment[]; orderedIds: string[] } {
  const CITE_RE = /\[cite:([^\]]+)\]/g
  const segments: Segment[] = []
  const orderedIds: string[] = []
  const idToIndex = new Map<string, number>()

  let last = 0
  let match: RegExpExecArray | null

  while ((match = CITE_RE.exec(answer)) !== null) {
    // Gemini sometimes puts multiple IDs in one tag: [cite:uuid1, uuid2]
    const ids = match[1].split(',').map(s => s.trim()).filter(Boolean)
    // Only render this tag if at least one ID resolves
    const validIds = ids.filter(id => citedMap[id])
    if (validIds.length === 0) continue

    if (match.index > last) {
      segments.push({ type: 'text', value: answer.slice(last, match.index) })
    }

    for (const id of validIds) {
      if (!idToIndex.has(id)) {
        idToIndex.set(id, orderedIds.length + 1)
        orderedIds.push(id)
      }
      segments.push({ type: 'cite', id, index: idToIndex.get(id)! })
    }
    last = match.index + match[0].length
  }

  if (last < answer.length) {
    segments.push({ type: 'text', value: answer.slice(last) })
  }

  return { segments, orderedIds }
}

interface Props {
  response: AgentResponse
}

export default function AgentAnswerView({ response }: Props) {
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const { setSelectedEventId, setGlobeFocusTarget, events, stopAutoSpin } = useAppContext()
  const confColor = CONFIDENCE_COLORS[response.confidence]

  const citedMap = response.cited_event_map ?? {}

  const { segments, orderedIds } = useMemo(
    () => parseAnswerSegments(response.answer, citedMap),
    [response.answer, citedMap]
  )

  // Resolve title: try cited_event_map first, then live events list
  const resolveTitle = (id: string) =>
    citedMap[id] ?? events.find(e => e.id === id)?.title ?? id

  const navigateTo = (id: string) => {
    stopAutoSpin()
    const evt = events.find(e => e.id === id)
    if (evt) {
      // Only zoom if this event has globe coordinates
      setGlobeFocusTarget({ lat: evt.primary_latitude, lng: evt.primary_longitude })
      setSelectedEventId(id)
    } else {
      // No-coord article: open the content modal directly without globe navigation
      setSelectedEventId(id)
    }
  }

  // Relevant events that are NOT already cited inline
  const citedSet = new Set(orderedIds)
  const extraRelevant = response.relevant_event_ids.filter(id => !citedSet.has(id)).slice(0, 5)

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

      {/* Answer with inline citation badges */}
      <div>
        <div className="text-xs uppercase tracking-widest mb-1.5" style={{ color: 'var(--text-muted)' }}>Analysis</div>
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {segments.length > 0 ? segments.map((seg, i) => {
            if (seg.type === 'text') return <span key={i}>{seg.value}</span>
            return (
              <button
                key={i}
                onClick={() => navigateTo(seg.id)}
                title={resolveTitle(seg.id)}
                className="inline-flex items-center gap-0.5 mx-0.5 px-1.5 py-0.5 text-[10px] font-mono leading-none transition-colors"
                style={{
                  background: 'var(--bg-raised)',
                  border: '1px solid var(--border-strong)',
                  color: 'var(--accent)',
                  verticalAlign: 'middle',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
              >
                [{seg.index}]
              </button>
            )
          }) : <span>{response.answer}</span>}
        </p>
      </div>

      {/* Numbered reference list for cited events */}
      {orderedIds.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>References</div>
          <div className="flex flex-col gap-1">
            {orderedIds.map((id, idx) => (
              <button
                key={id}
                onClick={() => navigateTo(id)}
                className="flex items-start gap-2 text-left px-2.5 py-2 transition-colors"
                style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                <span
                  className="text-[10px] font-mono flex-shrink-0 mt-0.5 px-1"
                  style={{ color: 'var(--accent)', border: '1px solid var(--border-strong)', background: 'var(--bg-surface)' }}
                >
                  {idx + 1}
                </span>
                <span className="text-xs leading-snug truncate" style={{ color: 'var(--text-secondary)' }}>
                  {resolveTitle(id)}
                </span>
                <svg className="w-2.5 h-2.5 flex-shrink-0 ml-auto mt-0.5 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}

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

      {/* Additional relevant events not cited inline */}
      {extraRelevant.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Also Relevant</div>
          <div className="flex flex-col gap-1">
            {extraRelevant.map(id => (
              <button
                key={id}
                onClick={() => navigateTo(id)}
                className="text-left text-xs px-2.5 py-1.5 transition-colors truncate"
                style={{ color: 'var(--text-secondary)', background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                {resolveTitle(id)}
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
