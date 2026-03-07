import { EVENT_TYPE_COLORS, EVENT_TYPE_LABELS } from '../context/AppContext'
import type { EventType } from '../types/events'

const TYPES: EventType[] = [
  'geopolitics',
  'trade_supply_chain',
  'energy_commodities',
  'financial_markets',
  'climate_disasters',
  'policy_regulation',
]

export default function Legend() {
  return (
    <div className="absolute bottom-24 left-4 z-20 bg-slate-900/80 backdrop-blur border border-slate-700 rounded-xl px-3 py-3">
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Event Types</div>
      <div className="flex flex-col gap-1.5">
        {TYPES.map(type => (
          <div key={type} className="flex items-center gap-2">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: EVENT_TYPE_COLORS[type] }}
            />
            <span className="text-xs text-slate-300">{EVENT_TYPE_LABELS[type]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
