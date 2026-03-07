import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react'
import type { Event, EventType, RelatedEvent, TimelineResponse } from '../types/events'

export const EVENT_TYPE_COLORS: Record<EventType, string> = {
  geopolitics: '#ef4444',
  trade_supply_chain: '#f97316',
  energy_commodities: '#eab308',
  financial_markets: '#22c55e',
  climate_disasters: '#3b82f6',
  policy_regulation: '#a855f7',
  humanitarian_crisis: '#ec4899',
}

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  geopolitics: 'Geopolitics',
  trade_supply_chain: 'Trade & Supply Chain',
  energy_commodities: 'Energy & Commodities',
  financial_markets: 'Financial Markets',
  climate_disasters: 'Climate & Disasters',
  policy_regulation: 'Policy & Regulation',
  humanitarian_crisis: 'Humanitarian Crisis',
}

const ALL_TYPES: EventType[] = [
  'geopolitics',
  'trade_supply_chain',
  'energy_commodities',
  'financial_markets',
  'climate_disasters',
  'policy_regulation',
  'humanitarian_crisis',
]

interface AppContextValue {
  // Events data
  events: Event[]
  setEvents: (events: Event[]) => void
  timeline: TimelineResponse | null
  setTimeline: (t: TimelineResponse) => void

  // Timeline position
  timelinePosition: Date | null
  setTimelinePosition: (d: Date) => void

  // Active filters
  activeFilters: Set<EventType>
  toggleFilter: (type: EventType) => void
  setAllFilters: (active: boolean) => void

  // Selected event (for modal)
  selectedEventId: string | null
  setSelectedEventId: (id: string | null) => void

  // Arcs (derived from related events of all visible events)
  arcs: ArcData[]
  setArcs: (arcs: ArcData[]) => void

  // Auto-spin
  isAutoSpinning: boolean
  stopAutoSpin: () => void
  resetInactivityTimer: () => void
}

export interface ArcData {
  startLat: number
  startLng: number
  endLat: number
  endLng: number
  color: string
  relationshipType: string
  eventAId: string
  eventBId: string
}

const AppContext = createContext<AppContextValue | null>(null)

const AUTO_SPIN_RESUME_MS = 5 * 60 * 1000 // 5 minutes

export function AppProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<Event[]>([])
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null)
  const [timelinePosition, setTimelinePosition] = useState<Date | null>(null)
  const [activeFilters, setActiveFilters] = useState<Set<EventType>>(new Set(ALL_TYPES))
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [arcs, setArcs] = useState<ArcData[]>([])
  const [isAutoSpinning, setIsAutoSpinning] = useState(true)
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const stopAutoSpin = useCallback(() => {
    setIsAutoSpinning(false)
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current)
    }
    inactivityTimerRef.current = setTimeout(() => {
      setIsAutoSpinning(true)
    }, AUTO_SPIN_RESUME_MS)
  }, [])

  const resetInactivityTimer = useCallback(() => {
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current)
    }
    inactivityTimerRef.current = setTimeout(() => {
      setIsAutoSpinning(true)
    }, AUTO_SPIN_RESUME_MS)
  }, [])

  const toggleFilter = useCallback((type: EventType) => {
    stopAutoSpin()
    setActiveFilters(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }, [stopAutoSpin])

  const setAllFilters = useCallback((active: boolean) => {
    stopAutoSpin()
    setActiveFilters(active ? new Set(ALL_TYPES) : new Set())
  }, [stopAutoSpin])

  const setTimelinePositionWithStop = useCallback((d: Date) => {
    stopAutoSpin()
    setTimelinePosition(d)
  }, [stopAutoSpin])

  return (
    <AppContext.Provider
      value={{
        events,
        setEvents,
        timeline,
        setTimeline,
        timelinePosition,
        setTimelinePosition: setTimelinePositionWithStop,
        activeFilters,
        toggleFilter,
        setAllFilters,
        selectedEventId,
        setSelectedEventId,
        arcs,
        setArcs,
        isAutoSpinning,
        stopAutoSpin,
        resetInactivityTimer,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used inside AppProvider')
  return ctx
}

export function buildArcs(
  events: Event[],
  relatedMap: Map<string, RelatedEvent[]>,
  visibleIds: Set<string>,
): ArcData[] {
  const arcs: ArcData[] = []
  const seen = new Set<string>()

  for (const evt of events) {
    if (!visibleIds.has(evt.id)) continue
    const related = relatedMap.get(evt.id) ?? []
    for (const r of related) {
      if (!visibleIds.has(r.event_id)) continue
      const key = [evt.id, r.event_id].sort().join('|')
      if (seen.has(key)) continue
      seen.add(key)
      arcs.push({
        startLat: evt.primary_latitude,
        startLng: evt.primary_longitude,
        endLat: r.primary_latitude,
        endLng: r.primary_longitude,
        color: EVENT_TYPE_COLORS[evt.event_type],
        relationshipType: r.relationship_type,
        eventAId: evt.id,
        eventBId: r.event_id,
      })
    }
  }
  return arcs
}
