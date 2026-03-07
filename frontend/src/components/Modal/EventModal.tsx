import { useEffect, useState, useCallback, useRef } from 'react'
import { getEventById } from '../../api/client'
import type { EventDetail } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../../context/AppContext'
import { useAgentContext } from '../../context/AgentContext'
import { getMediaUrls } from '../../utils/mediaConfig'
import FinancialImpactSection from '../Agent/FinancialImpactSection'

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = score >= 0.85 ? '#5a8a5a' : score >= 0.70 ? '#8a7a3a' : '#8a3030'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-px" style={{ background: 'var(--border-strong)' }}>
        <div className="h-px transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>{pct}%</span>
    </div>
  )
}

function RelTypeChip({ type }: { type: string }) {
  const colors: Record<string, string> = {
    market_reaction: '#5a8a5a',
    commodity_link: '#8a7a3a',
    supply_chain_link: '#8a5a30',
    regional_spillover: '#3a5a8a',
    policy_impact: '#6a4a8a',
    same_event_family: '#8a3a6a',
  }
  const c = colors[type] ?? '#666666'
  return (
    <span
      className="text-xs px-2 py-0.5"
      style={{ color: c, border: `1px solid ${c}66`, background: `${c}11` }}
    >
      {type.replace(/_/g, ' ')}
    </span>
  )
}

export default function EventModal() {
  const { selectedEventId, setSelectedEventId } = useAppContext()
  const { agentResponse, activeNavigationPlan } = useAgentContext()
  const [detail, setDetail] = useState<EventDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!selectedEventId) {
      setDetail(null)
      return
    }
    setLoading(true)
    setError(null)
    getEventById(selectedEventId)
      .then(d => {
        setDetail(d)
        setLoading(false)
        if (activeNavigationPlan?.open_modal_event_id === selectedEventId) {
          setTimeout(() => scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' }), 50)
        }
      })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [selectedEventId, activeNavigationPlan])

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
      <div
        ref={scrollRef}
        className="h-full ml-auto w-full pointer-events-auto overflow-y-auto flex flex-col"
        style={{
          background: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border)',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.25s ease',
        }}
      >
        {/* Close button — square */}
        <button
          onClick={close}
          className="absolute top-3 left-3 z-10 w-7 h-7 flex items-center justify-center transition-colors"
          style={{
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-strong)',
            color: 'var(--text-secondary)',
          }}
          aria-label="Close"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="w-6 h-6 border border-[#505050] border-t-transparent animate-spin" style={{ borderRadius: 0 }} />
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center p-6 text-xs" style={{ color: '#8a3030' }}>
            Failed to load event details.
          </div>
        )}

        {detail && !loading && (
          <div className="flex flex-col">
            {/* Hero image */}
            <div className="relative h-44 flex-shrink-0 overflow-hidden" style={{ background: 'var(--bg-raised)' }}>
              <img
                src={getEventImageUrl(detail.image_url)}
                alt={detail.title}
                className="w-full h-full object-cover"
                style={{ filter: 'saturate(0.7) brightness(0.75)' }}
                onError={(e) => { (e.target as HTMLImageElement).src = '/placeholder-event.svg' }}
              />
              <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(8,8,8,0.95) 0%, transparent 55%)' }} />
              {/* Type badge */}
              <span
                className="absolute bottom-3 left-4 text-xs font-bold px-2 py-0.5 tracking-wider"
                style={{
                  backgroundColor: `${EVENT_TYPE_COLORS[detail.event_type]}18`,
                  color: EVENT_TYPE_COLORS[detail.event_type],
                  border: `1px solid ${EVENT_TYPE_COLORS[detail.event_type]}66`,
                }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 mr-1.5 align-middle"
                  style={{ backgroundColor: EVENT_TYPE_COLORS[detail.event_type] }}
                />
                {EVENT_TYPE_LABELS[detail.event_type]}
              </span>
            </div>

            {/* Content */}
            <div className="px-5 py-4 flex flex-col gap-4">
              {/* Title */}
              <h2
                className="font-bold text-base leading-snug"
                style={{ color: 'var(--text-bright)' }}
              >
                {detail.title}
              </h2>

              {/* Location + Time */}
              <div className="flex flex-wrap gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
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
                  {detail.end_time && ` — ${new Date(detail.end_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}`}
                </span>
              </div>

              {/* Confidence score */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Confidence</div>
                <ConfidenceBar score={detail.confidence_score} />
              </div>

              <div className="h-px" style={{ background: 'var(--border)' }} />

              {/* Summary */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Summary</div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{detail.summary}</p>
              </div>

              {/* Canada Impact */}
              <div
                className="p-3"
                style={{
                  background: 'var(--bg-raised)',
                  borderLeft: '2px solid #7a3030',
                }}
              >
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-xs font-bold uppercase tracking-widest" style={{ color: '#8a4040' }}>CA Impact</span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{detail.canada_impact_summary}</p>
              </div>

              {/* Financial impact from agent */}
              {agentResponse?.financial_impact && agentResponse.top_event_id === detail.id && (
                <FinancialImpactSection impact={agentResponse.financial_impact} />
              )}

              {/* Entities */}
              {detail.entities.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Key Entities</div>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.entities.map(name => (
                      <span
                        key={name}
                        className="text-xs px-2 py-0.5"
                        style={{
                          background: 'var(--bg-raised)',
                          color: 'var(--text-secondary)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Engagement snapshot */}
              {detail.engagement && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Engagement</div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {[
                      { label: 'Reddit Upvotes', value: detail.engagement.reddit_upvotes, icon: '▲' },
                      { label: 'Reddit Comments', value: detail.engagement.reddit_comments, icon: '▼' },
                      { label: 'Poly Volume', value: detail.engagement.poly_volume, icon: '◆' },
                      { label: 'Poly Comments', value: detail.engagement.poly_comments, icon: '◇' },
                      { label: 'Twitter Likes', value: detail.engagement.twitter_likes, icon: '♥' },
                      { label: 'Twitter Views', value: detail.engagement.twitter_views, icon: '◎' },
                      { label: 'Twitter Comments', value: detail.engagement.twitter_comments, icon: '◉' },
                      { label: 'Twitter Reposts', value: detail.engagement.twitter_reposts, icon: '⇄' },
                    ].map(({ label, value, icon }) => (
                      <div
                        key={label}
                        className="p-2"
                        style={{
                          background: 'var(--bg-raised)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        <div className="text-xs mb-0.5" style={{ color: 'var(--text-muted)' }}>{icon} {label}</div>
                        <div className="text-xs font-bold tabular-nums" style={{ color: 'var(--text-bright)' }}>
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
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Sources</div>
                  <div className="flex flex-col gap-1.5">
                    {detail.sources.slice(0, 4).map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2.5 transition-colors group"
                        style={{
                          background: 'var(--bg-raised)',
                          border: '1px solid var(--border)',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-bold mb-0.5" style={{ color: 'var(--text-primary)' }}>{src.source_name}</div>
                            <div className="text-xs leading-snug line-clamp-2" style={{ color: 'var(--text-secondary)' }}>{src.headline}</div>
                          </div>
                          <svg className="w-3 h-3 flex-shrink-0 mt-0.5" style={{ color: 'var(--text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </div>
                        <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
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
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Related Events</div>
                  <div className="flex flex-col gap-1.5">
                    {detail.related_events.slice(0, 5).map(rel => (
                      <div
                        key={rel.event_id}
                        className="p-2.5"
                        style={{
                          background: 'var(--bg-raised)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        <div className="flex items-start gap-2 mb-1.5">
                          <span
                            className="inline-block w-1.5 h-1.5 flex-shrink-0 mt-1"
                            style={{ backgroundColor: EVENT_TYPE_COLORS[rel.event_type] }}
                          />
                          <span className="text-xs font-bold leading-snug flex-1" style={{ color: 'var(--text-bright)' }}>{rel.title}</span>
                          <span className="text-xs tabular-nums flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{Math.round(rel.relationship_score * 100)}%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <RelTypeChip type={rel.relationship_type} />
                        </div>
                        <p className="text-xs mt-1.5 leading-snug line-clamp-2" style={{ color: 'var(--text-muted)' }}>{rel.reason}</p>
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
