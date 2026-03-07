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
      {/* Title badge */}
      <div className="bg-slate-900/90 backdrop-blur border border-slate-700 rounded-full px-4 py-1 text-xs font-semibold text-slate-300 tracking-wider uppercase">
        Global Event Intelligence — Canada Impact
      </div>

      {/* Filter chips row */}
      <div className="bg-slate-900/80 backdrop-blur border border-slate-700 rounded-2xl px-3 py-2 flex items-center gap-2 flex-wrap justify-center">
        {/* All / None toggles */}
        <button
          onClick={() => setAllFilters(true)}
          className={`text-xs px-3 py-1 rounded-full border transition-colors ${
            allActive
              ? 'bg-slate-600 border-slate-500 text-white'
              : 'border-slate-600 text-slate-400 hover:border-slate-400'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setAllFilters(false)}
          className={`text-xs px-3 py-1 rounded-full border transition-colors ${
            noneActive
              ? 'bg-slate-600 border-slate-500 text-white'
              : 'border-slate-600 text-slate-400 hover:border-slate-400'
          }`}
        >
          None
        </button>

        <div className="w-px h-4 bg-slate-700" />

        {ALL_TYPES.map(type => {
          const isActive = activeFilters.has(type)
          const color = EVENT_TYPE_COLORS[type]
          return (
            <button
              key={type}
              onClick={() => toggleFilter(type)}
              className="text-xs px-3 py-1 rounded-full border transition-all"
              style={
                isActive
                  ? {
                      backgroundColor: `${color}22`,
                      borderColor: color,
                      color: color,
                    }
                  : {
                      backgroundColor: 'transparent',
                      borderColor: '#334155',
                      color: '#64748b',
                    }
              }
            >
              <span
                className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
                style={{ backgroundColor: isActive ? color : '#334155' }}
              />
              {EVENT_TYPE_LABELS[type]}
            </button>
          )
        })}
      </div>
    </div>
  )
}
