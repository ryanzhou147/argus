import { useEffect, useState, useCallback } from 'react'
import { getEventById } from '../../api/client'
import type { EventDetail } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../../context/AppContext'
import { getEventImageUrl } from '../../utils/mediaConfig'

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = score >= 0.85 ? '#22c55e' : score >= 0.70 ? '#eab308' : '#ef4444'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-slate-700 rounded-full h-1.5">
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-semibold tabular-nums" style={{ color }}>{pct}%</span>
    </div>
  )
}

function RelTypeChip({ type }: { type: string }) {
  const colors: Record<string, string> = {
    market_reaction: '#22c55e',
    commodity_link: '#eab308',
    supply_chain_link: '#f97316',
    regional_spillover: '#3b82f6',
    policy_impact: '#a855f7',
    same_event_family: '#ec4899',
  }
  const c = colors[type] ?? '#94a3b8'
  return (
    <span className="text-xs px-2 py-0.5 rounded-full border" style={{ color: c, borderColor: `${c}55`, backgroundColor: `${c}11` }}>
      {type.replace(/_/g, ' ')}
    </span>
  )
}

export default function EventModal() {
  const { selectedEventId, setSelectedEventId } = useAppContext()
  const [detail, setDetail] = useState<EventDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedEventId) {
      setDetail(null)
      return
    }
    setLoading(true)
    setError(null)
    getEventById(selectedEventId)
      .then(d => { setDetail(d); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [selectedEventId])

  const close = useCallback(() => setSelectedEventId(null), [setSelectedEventId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [close])

  const isOpen = !!selectedEventId

  return (
    <div
      className="absolute top-0 right-0 h-full z-30 flex pointer-events-none"
      style={{ width: '420px', maxWidth: '100vw' }}
    >
      {/* Backdrop click */}
      {isOpen && (
        <div
          className="fixed inset-0 pointer-events-auto"
          style={{ zIndex: -1 }}
          onClick={close}
        />
      )}

      <div
        className="h-full ml-auto w-full pointer-events-auto overflow-y-auto flex flex-col"
        style={{
          background: 'rgba(15,23,42,0.97)',
          borderLeft: '1px solid #1e293b',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
        }}
      >
        {/* Close button */}
        <button
          onClick={close}
          className="absolute top-4 left-4 z-10 w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center transition-colors text-slate-400 hover:text-white"
          aria-label="Close"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center p-6 text-red-400 text-sm">
            Failed to load event details.
          </div>
        )}

        {detail && !loading && (
          <div className="flex flex-col">
            {/* Hero image */}
            <div className="relative h-48 bg-slate-800 flex-shrink-0 overflow-hidden">
              <img
                src={getEventImageUrl(detail.image_url)}
                alt={detail.title}
                className="w-full h-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).src = '/placeholder-event.svg' }}
              />
              <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(15,23,42,0.9) 0%, transparent 60%)' }} />
              {/* Type badge */}
              <span
                className="absolute bottom-3 left-4 text-xs font-semibold px-2.5 py-1 rounded-full"
                style={{
                  backgroundColor: `${EVENT_TYPE_COLORS[detail.event_type]}22`,
                  color: EVENT_TYPE_COLORS[detail.event_type],
                  border: `1px solid ${EVENT_TYPE_COLORS[detail.event_type]}55`,
                }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
                  style={{ backgroundColor: EVENT_TYPE_COLORS[detail.event_type] }}
                />
                {EVENT_TYPE_LABELS[detail.event_type]}
              </span>
            </div>

            {/* Content */}
            <div className="px-5 py-4 flex flex-col gap-4">
              {/* Title */}
              <h2 className="text-white font-bold text-lg leading-snug">{detail.title}</h2>

              {/* Location + Time */}
              <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {detail.primary_latitude.toFixed(1)}°, {detail.primary_longitude.toFixed(1)}°
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {new Date(detail.start_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}
                  {detail.end_time && ` – ${new Date(detail.end_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}`}
                </span>
              </div>

              {/* Confidence score */}
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">Confidence</div>
                <ConfidenceBar score={detail.confidence_score} />
              </div>

              <div className="border-t border-slate-800" />

              {/* Summary */}
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">Summary</div>
                <p className="text-slate-300 text-sm leading-relaxed">{detail.summary}</p>
              </div>

              {/* Canada Impact */}
              <div className="bg-red-950/30 border border-red-900/40 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-lg">🍁</span>
                  <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Canada Impact</span>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{detail.canada_impact_summary}</p>
              </div>

              {/* Entities */}
              {detail.entities.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Key Entities</div>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.entities.map(name => (
                      <span key={name} className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Engagement snapshot */}
              {detail.engagement && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Engagement</div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: 'Reddit Upvotes', value: detail.engagement.reddit_upvotes, icon: '▲' },
                      { label: 'Reddit Comments', value: detail.engagement.reddit_comments, icon: '💬' },
                      { label: 'Polymarket Volume', value: detail.engagement.poly_volume, icon: '📊' },
                      { label: 'Poly Comments', value: detail.engagement.poly_comments, icon: '🗨' },
                    ].map(({ label, value, icon }) => (
                      <div key={label} className="bg-slate-800/60 rounded-lg p-2.5 border border-slate-700/50">
                        <div className="text-xs text-slate-500 mb-0.5">{icon} {label}</div>
                        <div className="text-white font-semibold text-sm tabular-nums">
                          {value.toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sources */}
              {detail.sources.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Sources</div>
                  <div className="flex flex-col gap-2">
                    {detail.sources.slice(0, 4).map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-slate-800/60 rounded-lg p-3 border border-slate-700/50 hover:border-slate-500 transition-colors group"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-semibold text-blue-400 mb-0.5">{src.source_name}</div>
                            <div className="text-slate-300 text-xs leading-snug group-hover:text-white transition-colors line-clamp-2">{src.headline}</div>
                          </div>
                          <svg className="w-3 h-3 text-slate-500 flex-shrink-0 mt-0.5 group-hover:text-slate-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </div>
                        <div className="text-xs text-slate-500 mt-1.5">
                          {new Date(src.published_at).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Related events */}
              {detail.related_events.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Related Events</div>
                  <div className="flex flex-col gap-2">
                    {detail.related_events.slice(0, 5).map(rel => (
                      <div key={rel.event_id} className="bg-slate-800/60 rounded-lg p-3 border border-slate-700/50">
                        <div className="flex items-start gap-2 mb-1.5">
                          <span
                            className="inline-block w-2 h-2 rounded-full flex-shrink-0 mt-1"
                            style={{ backgroundColor: EVENT_TYPE_COLORS[rel.event_type] }}
                          />
                          <span className="text-slate-200 text-xs font-medium leading-snug flex-1">{rel.title}</span>
                          <span className="text-slate-500 text-xs tabular-nums flex-shrink-0">{Math.round(rel.relationship_score * 100)}%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <RelTypeChip type={rel.relationship_type} />
                        </div>
                        <p className="text-slate-500 text-xs mt-1.5 leading-snug line-clamp-2">{rel.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pb-4" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
