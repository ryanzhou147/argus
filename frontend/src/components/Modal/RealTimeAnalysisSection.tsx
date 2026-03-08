import { useEffect, useState } from 'react'
import { postRealtimeAnalysis } from '../../api/client'
import { useUserPersona } from '../../context/UserPersonaContext'

interface Props {
  contentId: string
}

const TIMEOUT_MS = 10_000

export default function RealTimeAnalysisSection({ contentId }: Props) {
  const { role, industry } = useUserPersona()
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setAnalysis(null)
    setLoading(true)

    const timeoutId = setTimeout(() => {
      if (!cancelled) {
        cancelled = true
        setLoading(false)
      }
    }, TIMEOUT_MS)

    postRealtimeAnalysis(contentId, role, industry)
      .then(res => {
        if (!cancelled) {
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
  }, [contentId, role, industry])

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
    </div>
  )
}
