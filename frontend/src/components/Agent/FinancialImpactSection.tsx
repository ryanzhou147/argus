import type { FinancialImpact } from '../../types/agent'

const DIRECTION_CONFIG = {
  positive: { color: '#22c55e', icon: '↑', label: 'Positive' },
  negative: { color: '#ef4444', icon: '↓', label: 'Negative' },
  mixed: { color: '#eab308', icon: '↕', label: 'Mixed' },
  uncertain: { color: '#94a3b8', icon: '?', label: 'Uncertain' },
}

interface Props {
  impact: FinancialImpact
}

export default function FinancialImpactSection({ impact }: Props) {
  const dir = DIRECTION_CONFIG[impact.impact_direction] ?? DIRECTION_CONFIG.uncertain

  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-800/40 p-3">
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Financial Impact</span>
        <span className="ml-auto text-xs px-1.5 py-0.5 rounded font-semibold"
          style={{ color: dir.color, backgroundColor: `${dir.color}22` }}>
          {dir.icon} {dir.label}
        </span>
      </div>

      <p className="text-slate-300 text-xs leading-relaxed mb-2">{impact.summary}</p>

      {impact.affected_sectors.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {impact.affected_sectors.map(sector => (
            <span key={sector} className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300 border border-slate-600">
              {sector}
            </span>
          ))}
        </div>
      )}

      {impact.uncertainty_notes && (
        <p className="text-xs text-slate-500 italic">{impact.uncertainty_notes}</p>
      )}
    </div>
  )
}
