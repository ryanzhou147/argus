import { useAppContext, EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../../context/AppContext'
import type { EventType } from '../../types/events'

const ALL_TYPES: EventType[] = [
  'geopolitics',
  'trade_supply_chain',
  'energy_commodities',
  'financial_markets',
  'climate_disasters',
  'policy_regulation',
  'humanitarian_crisis',
]

export default function FilterBar() {
  const { activeFilters, toggleFilter, setAllFilters } = useAppContext()

  const allActive = activeFilters.size === ALL_TYPES.length
  const noneActive = activeFilters.size === 0

  return (
    <div
      className="absolute top-4 left-1/2 z-20 -translate-x-1/2 flex flex-col items-center gap-2"
    >

      {/* Filter chips row */}
      <div
        className="px-3 py-2 flex items-center gap-2 flex-wrap justify-center"
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
        }}
      >
        {/* All / None toggles */}
        <button
          onClick={() => setAllFilters(true)}
          className="text-xs px-3 py-1 transition-colors"
          style={
            allActive
              ? { background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)' }
              : { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }
          }
        >
          All
        </button>
        <button
          onClick={() => setAllFilters(false)}
          className="text-xs px-3 py-1 transition-colors"
          style={
            noneActive
              ? { background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)' }
              : { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)' }
          }
        >
          None
        </button>

        <div className="w-px h-4" style={{ background: 'var(--border)' }} />

        {ALL_TYPES.map(type => {
          const isActive = activeFilters.has(type)
          const color = EVENT_TYPE_COLORS[type]
          return (
            <button
              key={type}
              onClick={() => toggleFilter(type)}
              className="text-xs px-3 py-1 transition-all"
              style={
                isActive
                  ? {
                      backgroundColor: `${color}18`,
                      borderColor: `${color}88`,
                      border: `1px solid ${color}88`,
                      color: color,
                    }
                  : {
                      backgroundColor: 'transparent',
                      border: '1px solid var(--border)',
                      color: 'var(--text-muted)',
                    }
              }
            >
              <span
                className="inline-block w-1.5 h-1.5 mr-1.5 align-middle"
                style={{ backgroundColor: isActive ? color : 'var(--border-strong)' }}
              />
              {EVENT_TYPE_LABELS[type]}
            </button>
          )
        })}
      </div>
    </div>
  )
}
