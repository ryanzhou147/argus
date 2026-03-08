import { useEffect, useState, useCallback, useRef } from 'react'
import { getContentById } from '../../api/client'
import type { ContentDetail } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../../context/AppContext'
import type { EventType } from '../../types/events'
import { useAgentContext } from '../../context/AgentContext'
import { getMediaUrls, isVideoUrl } from '../../utils/mediaConfig'
import FinancialImpactSection from '../Agent/FinancialImpactSection'

function MissingData({ label }: { label: string }) {
  return (
    <p className="text-xs italic" style={{ color: '#8a4040' }}>
      {label} not available.
    </p>
  )
}

function ExpandableText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const LINE_LIMIT = 3
  // ~80 chars per line * 3 lines
  const CHAR_THRESHOLD = 240
  const isLong = text.length > CHAR_THRESHOLD
  return (
    <div>
      <p
        className="text-xs leading-relaxed"
        style={{
          color: 'var(--text-secondary)',
          display: '-webkit-box',
          WebkitBoxOrient: 'vertical',
          WebkitLineClamp: expanded ? 'unset' : LINE_LIMIT,
          overflow: 'hidden',
        } as React.CSSProperties}
      >
        {text}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-xs mt-1"
          style={{ color: 'var(--text-muted)', textDecoration: 'underline', background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

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


export default function EventModal() {
  const { selectedEventId, setSelectedEventId, events, arcs, setGlobeFocusTarget, stopAutoSpin } = useAppContext()
  const { agentResponse, activeNavigationPlan } = useAgentContext()
  const ev = events.find(e => e.id === selectedEventId) ?? null
  const [detail, setDetail] = useState<ContentDetail | null>(null)
  const [mediaExpanded, setMediaExpanded] = useState(false)
  const heroRef = useRef<HTMLDivElement>(null)
  const heroVideoRef = useRef<HTMLVideoElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!selectedEventId) { setDetail(null); return }
    setDetail(null)
    getContentById(selectedEventId)
      .then(d => {
        setDetail(d)
        if (activeNavigationPlan?.open_modal_event_id === selectedEventId) {
          setTimeout(() => scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' }), 50)
        }
      })
      .catch(() => setDetail(null))
  }, [selectedEventId, activeNavigationPlan])

  const close = useCallback(() => setSelectedEventId(null), [setSelectedEventId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [close])

  const isOpen = !!selectedEventId

  // Related events: derive from arc connections in globe state
  const arcRelated = ev
    ? arcs
        .filter(a => a.eventAId === ev.id || a.eventBId === ev.id)
        .map(a => events.find(e => e.id === (a.eventAId === ev.id ? a.eventBId : a.eventAId)))
        .filter((e): e is typeof events[0] => e !== undefined)
        //.slice(0, 5)
    : []

  return (
    <>
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

        {ev && (
          <div className="flex flex-col">
            {/* Hero media */}
            <div
              ref={heroRef}
              className="relative h-44 flex-shrink-0 overflow-hidden cursor-pointer"
              style={{ background: 'var(--bg-raised)' }}
              onClick={() => {
                setMediaExpanded(v => {
                  const next = !v
                  if (next) heroVideoRef.current?.pause()
                  else heroVideoRef.current?.play()
                  return next
                })
              }}
            >
              {isVideoUrl(ev.image_url) ? (
                <video
                  ref={heroVideoRef}
                  src={getMediaUrls(ev.image_url, ev.image_s3_url).primary}
                  className="w-full h-full object-cover"
                  style={{ filter: 'saturate(0.7) brightness(0.75)' }}
                  autoPlay
                  muted
                  loop
                  playsInline
                  onError={(e) => {
                    const fallback = getMediaUrls(ev.image_url, ev.image_s3_url).fallback
                    if (fallback) (e.target as HTMLVideoElement).src = fallback
                  }}
                />
              ) : (
                <img
                  src={getMediaUrls(ev.image_url, ev.image_s3_url).primary}
                  alt={ev.title}
                  className="w-full h-full object-cover"
                  style={{ filter: 'saturate(0.7) brightness(0.75)' }}
                  onError={(e) => {
                    const fallback = getMediaUrls(ev.image_url, ev.image_s3_url).fallback
                    const img = e.target as HTMLImageElement
                    img.src = fallback ?? '/placeholder-event.svg'
                  }}
                />
              )}

              {/* Expand hint */}
              {!mediaExpanded && (
                <div className="absolute top-2 right-2 rounded-full p-1 pointer-events-none"
                  style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)' }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
                  </svg>
                </div>
              )}
              <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(8,8,8,0.95) 0%, transparent 55%)' }} />
              {/* Type badge */}
              <span
                className="absolute bottom-3 left-4 text-xs font-bold px-2 py-0.5 tracking-wider"
                style={{
                  backgroundColor: `${EVENT_TYPE_COLORS[(ev.event_type as EventType)]}18`,
                  color: EVENT_TYPE_COLORS[(ev.event_type as EventType)],
                  border: `1px solid ${EVENT_TYPE_COLORS[(ev.event_type as EventType)]}66`,
                }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 mr-1.5 align-middle"
                  style={{ backgroundColor: EVENT_TYPE_COLORS[(ev.event_type as EventType)] }}
                />
                {EVENT_TYPE_LABELS[(ev.event_type as EventType)]}
              </span>
            </div>

            {/* Content */}
            <div className="px-5 py-4 flex flex-col gap-4">
              {/* Title */}
              <h2
                className="font-bold text-base leading-snug"
                style={{ color: 'var(--text-bright)' }}
              >
                {ev.title}
              </h2>

              {/* Location + Time */}
              <div className="flex flex-wrap gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {ev.primary_latitude.toFixed(1)}°, {ev.primary_longitude.toFixed(1)}°
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {new Date(ev.start_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}
                  {ev.end_time && ` — ${new Date(ev.end_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}`}
                </span>
              </div>

              {/* Confidence score */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Confidence</div>
                <ConfidenceBar score={ev.confidence_score} />
              </div>

              <div className="h-px" style={{ background: 'var(--border)' }} />

              {/* Summary */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Summary</div>
                {detail?.body
                  ? <ExpandableText text={detail.body} />
                  : <MissingData label="Summary" />}
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
                {ev.canada_impact_summary
                  ? <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{ev.canada_impact_summary}</p>
                  : <MissingData label="Canada impact summary" />}
              </div>

              {/* Financial impact from agent */}
              {agentResponse?.financial_impact && agentResponse.top_event_id === ev.id && (
                <FinancialImpactSection impact={agentResponse.financial_impact} />
              )}

              {/* Engagement snapshot */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Engagement</div>
                {detail?.engagement ? (
                  <div className="flex flex-col gap-1.5">
                    {[
                      { label: 'Twitter', likes: detail.engagement.twitter_likes, comments: detail.engagement.twitter_comments, views: detail.engagement.twitter_views },
                      { label: 'Reddit', likes: detail.engagement.reddit_upvotes, comments: detail.engagement.reddit_comments, views: null },
                    ].map(({ label, likes, comments, views }) => (
                      <div key={label} className="flex items-center gap-3 px-2.5 py-2" style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }}>
                        <span className="text-xs w-12 flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span className="text-xs tabular-nums" style={{ color: 'var(--text-secondary)' }}>♥ {likes.toLocaleString()} likes</span>
                        <span className="text-xs tabular-nums" style={{ color: 'var(--text-secondary)' }}>· {comments.toLocaleString()} comments</span>
                        {views !== null && <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>· {views.toLocaleString()} views</span>}
                      </div>
                    ))}
                  </div>
                ) : <MissingData label="Engagement data" />}
              </div>

              {/* Source */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Source</div>
                {detail?.url ? (
                  <a
                    href={detail.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start justify-between gap-2 p-2.5 transition-colors"
                    style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                    onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                  >
                    <div className="flex-1 min-w-0">
                      {detail.source_name && (
                        <div className="text-xs font-bold mb-0.5" style={{ color: 'var(--text-primary)' }}>{detail.source_name}</div>
                      )}
                      <div className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{detail.url}</div>
                      {detail.published_at && (
                        <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                          {new Date(detail.published_at).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}
                        </div>
                      )}
                    </div>
                    <svg className="w-3 h-3 flex-shrink-0 mt-0.5" style={{ color: 'var(--text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ) : <MissingData label="Source link" />}
              </div>

              {/* Related events — from arc connections */}
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Related Events</div>
                {arcRelated.length > 0 ? (
                  <div className="flex flex-col gap-1.5">
                    {arcRelated.map(rel => (
                      <button
                        key={rel.id}
                        onClick={() => {
                          stopAutoSpin()
                          setSelectedEventId(rel.id)
                          setGlobeFocusTarget({ lat: rel.primary_latitude, lng: rel.primary_longitude })
                        }}
                        className="p-2.5 text-left w-full"
                        style={{
                          background: 'var(--bg-raised)',
                          border: '1px solid var(--border)',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                      >
                        <div className="flex items-start gap-2">
                          <span
                            className="inline-block w-1.5 h-1.5 flex-shrink-0 mt-1"
                            style={{ backgroundColor: EVENT_TYPE_COLORS[rel.event_type] }}
                          />
                          <span className="text-xs font-bold leading-snug flex-1" style={{ color: 'var(--text-bright)' }}>{rel.title}</span>
                        </div>
                        <div className="text-xs mt-1 ml-3" style={{ color: 'var(--text-muted)' }}>
                          {EVENT_TYPE_LABELS[rel.event_type]} · {new Date(rel.start_time).toLocaleDateString('en-CA', { year: 'numeric', month: 'short' })}
                        </div>
                      </button>
                    ))}
                  </div>
                ) : <MissingData label="Related events" />}
              </div>

              <div className="pb-4" />
            </div>
          </div>
        )}
      </div>
    </div>

    {/* Expanded media overlay */}
    {mediaExpanded && ev && (
      <>
        {/* Backdrop */}
        <div
          className="fixed inset-0 z-[9998]"
          style={{
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(6px)',
            animation: 'fadeIn 0.3s ease forwards',
          }}
          onClick={() => { setMediaExpanded(false); heroVideoRef.current?.play() }}
        />
        {/* Expanded media */}
        <div
          className="fixed z-[9999] overflow-hidden shadow-2xl"
          style={{
            width: '56vw',
            maxWidth: '900px',
            aspectRatio: '16/9',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            animation: 'expandMedia 0.3s cubic-bezier(0.34,1.2,0.64,1) forwards',
          }}
          onClick={() => { setMediaExpanded(false); heroVideoRef.current?.play() }}
        >
          {isVideoUrl(ev.image_url) ? (
            <video
              src={getMediaUrls(ev.image_url, ev.image_s3_url).primary}
              className="w-full h-full object-cover"
              autoPlay
              loop
              playsInline
              controls
            />
          ) : (
            <img
              src={getMediaUrls(ev.image_url, ev.image_s3_url).primary}
              alt={ev.title}
              className="w-full h-full object-cover"
            />
          )}
        </div>
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0 } to { opacity: 1 }
          }
          @keyframes expandMedia {
            from { opacity: 0; transform: translate(-50%, -50%) scale(0.7) }
            to   { opacity: 1; transform: translate(-50%, -50%) scale(1) }
          }
        `}</style>
      </>
    )}
    </>
  )
}
