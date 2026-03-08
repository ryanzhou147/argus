import { useEffect, useState, useCallback, useRef } from 'react'
import { getContentById, postConfidenceScore } from '../../api/client'
import type { ContentDetail } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../../context/AppContext'
import type { EventType } from '../../types/events'
import { useAgentContext } from '../../context/AgentContext'
import { getMediaUrls } from '../../utils/mediaConfig'
import FinancialImpactSection from '../Agent/FinancialImpactSection'
import RealTimeAnalysisSection from './RealTimeAnalysisSection'

function HeroVideo({ src, fallbackSrc, onMediaFailed, onMediaReady }: { src: string; fallbackSrc?: string | null; onMediaFailed?: () => void; onMediaReady?: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setFailed(false)
  }, [src])

  useEffect(() => {
    if (failed) onMediaFailed?.()
  }, [failed, onMediaFailed])

  useEffect(() => {
    const v = videoRef.current
    if (!v || failed) return
    v.muted = true
    v.play().catch(() => {})
  }, [src, failed])

  if (failed) {
    return (
      <img
        src={fallbackSrc || '/placeholder-event.svg'}
        alt=""
        className="w-full h-full object-cover"
        style={{ filter: 'saturate(0.7) brightness(0.75)' }}
        onError={(e) => {
          const img = e.target as HTMLImageElement
          if (!img.dataset.errored) {
            img.dataset.errored = '1'
            img.src = '/placeholder-event.svg'
          }
        }}
      />
    )
  }

  return (
    <video
      ref={videoRef}
      src={src}
      className="w-full h-full object-cover"
      style={{ filter: 'saturate(0.7) brightness(0.75)' }}
      muted
      loop
      playsInline
      preload="auto"
      onCanPlay={() => onMediaReady?.()}
      onError={() => setFailed(true)}
      onStalled={() => {
        const v = videoRef.current
        if (v && v.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) setFailed(true)
      }}
    />
  )
}

function MediaLightbox({
  src,
  isVideo,
  fallbackSrc,
  onClose,
}: {
  src: string
  isVideo: boolean
  fallbackSrc?: string | null
  onClose: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    v.muted = false
    v.currentTime = 0
    v.play().catch(() => {})
  }, [src])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center pointer-events-auto"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 w-9 h-9 flex items-center justify-center transition-colors"
        style={{
          background: 'rgba(255,255,255,0.08)',
          border: '1px solid rgba(255,255,255,0.15)',
          color: 'rgba(255,255,255,0.7)',
        }}
        aria-label="Close fullscreen"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div
        className="relative"
        style={{ maxWidth: '90vw', maxHeight: '85vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {isVideo ? (
          <video
            ref={videoRef}
            src={src}
            className="block"
            style={{ maxWidth: '90vw', maxHeight: '85vh', objectFit: 'contain' }}
            controls
            autoPlay
            loop
            playsInline
            preload="auto"
            onError={(e) => {
              const v = e.target as HTMLVideoElement
              if (fallbackSrc && !v.dataset.errored) {
                v.dataset.errored = '1'
                v.poster = fallbackSrc
              }
            }}
          />
        ) : (
          <img
            src={src}
            alt=""
            className="block"
            style={{ maxWidth: '90vw', maxHeight: '85vh', objectFit: 'contain' }}
            onError={(e) => {
              const img = e.target as HTMLImageElement
              if (fallbackSrc && !img.dataset.errored) {
                img.dataset.errored = '1'
                img.src = fallbackSrc
              }
            }}
          />
        )}
      </div>
    </div>
  )
}
        
// Module-level cache for confidence scores (keyed by content ID)
const confidenceCache = new Map<string, number>()

function isEngagementEmpty(engagement: ContentDetail['engagement']): boolean {
  if (!engagement) return true
  return (
    (engagement.twitter_likes ?? 0) === 0 &&
    (engagement.twitter_comments ?? 0) === 0 &&
    (engagement.twitter_views ?? 0) === 0 &&
    (engagement.twitter_reposts ?? 0) === 0 &&
    (engagement.reddit_upvotes ?? 0) === 0 &&
    (engagement.reddit_comments ?? 0) === 0
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
  const [lightbox, setLightbox] = useState<{ src: string; isVideo: boolean; fallback: string | null } | null>(null)
  const [mediaLoaded, setMediaLoaded] = useState(false)
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!selectedEventId) { setDetail(null); setConfidenceScore(null); setMediaLoaded(false); return }
    setDetail(null)
    setConfidenceScore(null)
    setMediaLoaded(false)
    getContentById(selectedEventId)
      .then(d => {
        setDetail(d)
        if (activeNavigationPlan?.open_modal_event_id === selectedEventId) {
          setTimeout(() => scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' }), 50)
        }
      })
      .catch(() => setDetail(null))
  }, [selectedEventId, activeNavigationPlan])

  // Fetch Gemini-generated confidence score when event has the default 0.5
  useEffect(() => {
    if (!ev || ev.confidence_score !== 0.5) return

    const cached = confidenceCache.get(ev.id)
    if (cached !== undefined) {
      setConfidenceScore(cached)
      return
    }

    postConfidenceScore(ev.id)
      .then(res => {
        confidenceCache.set(ev.id, res.confidence_score)
        setConfidenceScore(res.confidence_score)
      })
      .catch(() => {
        // Keep displaying 0.5 on failure
      })
  }, [ev?.id, ev?.confidence_score]) // eslint-disable-line react-hooks/exhaustive-deps

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
            {(() => {
              const media = getMediaUrls(ev.image_url, ev.image_s3_url)
              const isPlaceholder = media.primary === '/placeholder-event.svg'
              return (
                <div className="relative h-44 flex-shrink-0 overflow-hidden" style={{ background: 'var(--bg-raised)' }}>
                  {media.isVideo ? (
                    <HeroVideo
                      key={ev.id}
                      src={media.primary}
                      fallbackSrc={media.fallback}
                      onMediaReady={() => setMediaLoaded(true)}
                      onMediaFailed={() => setMediaLoaded(false)}
                    />
                  ) : (
                    <img
                      key={ev.id}
                      src={media.primary}
                      alt={ev.title}
                      className="w-full h-full object-cover"
                      style={{ filter: 'saturate(0.7) brightness(0.75)' }}
                      onLoad={(e) => {
                        const cur = (e.target as HTMLImageElement).src
                        setMediaLoaded(!cur.endsWith('/placeholder-event.svg'))
                      }}
                      onError={(e) => {
                        const img = e.target as HTMLImageElement
                        const step = parseInt(img.dataset.errorStep || '0', 10)
                        if (step === 0 && media.fallback) {
                          img.dataset.errorStep = '1'
                          img.src = media.fallback
                        } else if (step <= 1) {
                          img.dataset.errorStep = '2'
                          img.src = '/placeholder-event.svg'
                          setMediaLoaded(false)
                        }
                      }}
                    />
                  )}
                  <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(8,8,8,0.95) 0%, transparent 55%)' }} />

                  {mediaLoaded && (
                    <button
                      onClick={() => setLightbox({ src: media.primary, isVideo: media.isVideo, fallback: media.fallback })}
                      className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center transition-opacity opacity-60 hover:opacity-100"
                      style={{
                        background: 'rgba(0,0,0,0.5)',
                        border: '1px solid rgba(255,255,255,0.15)',
                        color: 'rgba(255,255,255,0.8)',
                      }}
                      aria-label="View fullscreen"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="square" strokeWidth={2} d="M15 3h6m0 0v6m0-6L14 10M9 21H3m0 0v-6m0 6l7-7" />
                      </svg>
                    </button>
                  )}

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
              )
            })()}

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
                <ConfidenceBar score={confidenceScore ?? ev.confidence_score} />
              </div>

              <div className="h-px" style={{ background: 'var(--border)' }} />

              {/* Summary */}
              {detail?.body && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Summary</div>
                  <ExpandableText text={detail.body} />
                </div>
              )}

              {/* Real-Time Analysis */}
              <RealTimeAnalysisSection contentId={ev.id} />

              {/* Financial impact from agent */}
              {agentResponse?.financial_impact && agentResponse.top_event_id === ev.id && (
                <FinancialImpactSection impact={agentResponse.financial_impact} />
              )}

              {/* Engagement snapshot */}
              {!isEngagementEmpty(detail?.engagement ?? null) && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Engagement</div>
                  <div className="flex flex-col gap-1.5">
                    {[
                      { label: 'Twitter', likes: detail!.engagement!.twitter_likes, comments: detail!.engagement!.twitter_comments, views: detail!.engagement!.twitter_views },
                      { label: 'Reddit', likes: detail!.engagement!.reddit_upvotes, comments: detail!.engagement!.reddit_comments, views: null },
                    ].map(({ label, likes, comments, views }) => (
                      <div key={label} className="flex items-center gap-3 px-2.5 py-2" style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)' }}>
                        <span className="text-xs w-12 flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span className="text-xs tabular-nums" style={{ color: 'var(--text-secondary)' }}>♥ {likes.toLocaleString()} likes</span>
                        <span className="text-xs tabular-nums" style={{ color: 'var(--text-secondary)' }}>· {comments.toLocaleString()} comments</span>
                        {views !== null && <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>· {views.toLocaleString()} views</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source */}
              {detail?.url && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Source</div>
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
                </div>
              )}

              {/* Related events — from arc connections */}
              {arcRelated.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Related Events</div>
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
                </div>
              )}

              <div className="pb-4" />
            </div>
          </div>
        )}
      </div>

      {lightbox && (
        <MediaLightbox
          src={lightbox.src}
          isVideo={lightbox.isVideo}
          fallbackSrc={lightbox.fallback}
          onClose={() => setLightbox(null)}
        />
      )}
    </div>
  )
}
