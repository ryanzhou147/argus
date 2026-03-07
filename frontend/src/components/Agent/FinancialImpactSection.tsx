import type { FinancialImpact } from '../../types/agent'

const DIRECTION_CONFIG = {
  positive: { color: '#4a7a4a', icon: '↑', label: 'Positive' },
  negative: { color: '#7a3a3a', icon: '↓', label: 'Negative' },
  mixed: { color: '#7a6a30', icon: '↕', label: 'Mixed' },
  uncertain: { color: '#606060', icon: '?', label: 'Uncertain' },
}

interface Props {
  impact: FinancialImpact
}

export default function FinancialImpactSection({ impact }: Props) {
  const dir = DIRECTION_CONFIG[impact.impact_direction] ?? DIRECTION_CONFIG.uncertain

  return (
    <div className="p-3" style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)', borderLeft: `2px solid ${dir.color}` }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-secondary)' }}>Financial Impact</span>
        <span
          className="ml-auto text-xs px-1.5 py-0.5 font-bold"
          style={{ color: dir.color, background: `${dir.color}18` }}
        >
          {dir.icon} {dir.label}
        </span>
      </div>

      <p className="text-xs leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>{impact.summary}</p>

      {impact.affected_sectors.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {impact.affected_sectors.map(sector => (
            <span
              key={sector}
              className="text-xs px-2 py-0.5"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            >
              {sector}
            </span>
          ))}
        </div>
      )}

      {impact.uncertainty_notes && (
        <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>{impact.uncertainty_notes}</p>
      )}
    </div>
  )
}
