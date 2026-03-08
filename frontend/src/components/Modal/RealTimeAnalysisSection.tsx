import { useEffect, useState } from 'react'
import { postRealtimeAnalysis } from '../../api/client'
import { useUserPersona } from '../../context/UserPersonaContext'

interface Props {
  contentId: string
}

const TIMEOUT_MS = 10_000

// Module-level cache: keyed by `${contentId}:${role}:${industry}`
const analysisCache = new Map<string, string>()

export default function RealTimeAnalysisSection({ contentId }: Props) {
  const { role, industry } = useUserPersona()
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshCounter, setRefreshCounter] = useState(0)

  const cacheKey = `${contentId}:${role ?? ''}:${industry ?? ''}`

  useEffect(() => {
    // Cache hit: show immediately, no fetch
    const cached = analysisCache.get(cacheKey)
    if (cached) {
      setAnalysis(cached)
      setLoading(false)
      return
    }

    let cancelled = false
    setAnalysis(null)
    setLoading(true)

    // Timeout: only stop the spinner, do NOT set cancelled
    const timeoutId = setTimeout(() => {
      if (!cancelled) {
        setLoading(false)
      }
    }, TIMEOUT_MS)

    postRealtimeAnalysis(contentId, role, industry)
      .then(res => {
        if (!cancelled) {
          analysisCache.set(cacheKey, res.analysis)
          setAnalysis(res.analysis)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
      .finally(() => clearTimeout(timeoutId))

    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [contentId, role, industry, refreshCounter]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleRefresh() {
    analysisCache.delete(cacheKey)
    setRefreshCounter(c => c + 1)
  }

  if (loading) {
    return (
      <div className="p-3" style={{ background: 'var(--bg-raised)', borderLeft: '2px solid #2a4a3a' }}>
        <div className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: '#5a8a6a' }}>
          Real-Time Analysis
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="h-2.5 rounded-sm animate-pulse" style={{ background: 'var(--border-strong)', width: '80%' }} />
          <div className="h-2.5 rounded-sm animate-pulse" style={{ background: 'var(--border-strong)', width: '65%' }} />
          <div className="h-2.5 rounded-sm animate-pulse" style={{ background: 'var(--border-strong)', width: '72%' }} />
        </div>
      </div>
    )
  }

  if (!analysis) return null

  return (
    <div className="p-3" style={{ background: 'var(--bg-raised)', borderLeft: '2px solid #2a4a3a' }}>
      <div className="text-xs font-bold uppercase tracking-widest mb-1.5" style={{ color: '#5a8a6a' }}>
        Real-Time Analysis
      </div>
      <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {analysis}
      </p>
      <button
        onClick={handleRefresh}
        className="mt-2 text-xs px-2 py-0.5"
        style={{
          background: 'var(--bg-raised)',
          border: '1px solid var(--border-strong)',
          color: 'var(--text-muted)',
          cursor: 'pointer',
        }}
      >
        Fetch New Info
      </button>
    </div>
  )
}
