import { useEffect, useState } from 'react'
import { getContentArcs, getContentPoints } from './api/client'
import { EVENT_TYPE_COLORS, useAppContext } from './context/AppContext'
import type { ArcData } from './context/AppContext'
import type { Event, EventType, TimelineResponse } from './types/events'
import GlobeView from './components/Globe/GlobeView'
import FilterBar from './components/Filters/FilterBar'
import TimelineSlider from './components/Timeline/TimelineSlider'
import EventModal from './components/Modal/EventModal'
import AgentLauncherButton from './components/Agent/AgentLauncherButton'
import AgentPanel from './components/Agent/AgentPanel'

function LoadingOverlay() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center" style={{ background: 'var(--bg-base)' }}>
      <div className="w-8 h-8 border border-[#505050] border-t-transparent animate-spin mb-4" style={{ borderRadius: 0 }} />
      <p className="text-xs tracking-widest uppercase" style={{ color: 'var(--text-secondary)' }}>Loading event intelligence...</p>
    </div>
  )
}

function ErrorOverlay({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center" style={{ background: 'var(--bg-base)' }}>
      <p className="text-xs mb-2 tracking-wider uppercase" style={{ color: '#8a3030' }}>Failed to connect to backend.</p>
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{message}</p>
      <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>Make sure the FastAPI server is running at http://localhost:8000</p>
    </div>
  )
}

export default function App() {
  const { setEvents, setTimeline, setArcs } = useAppContext()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [data, arcsData] = await Promise.all([
          getContentPoints(),
          getContentArcs(0.4).catch(() => ({ arcs: [] })),
        ])
        if (cancelled) return

        const KNOWN_TYPES: EventType[] = [
          'geopolitics', 'trade_supply_chain', 'energy_commodities',
          'financial_markets', 'climate_disasters', 'policy_regulation',
          'humanitarian_crisis',
        ]

        const mappedEvents: Event[] = data.points.map(p => ({
          id: p.id,
          title: p.title ?? 'Unknown',
          event_type: (KNOWN_TYPES.includes(p.event_type as EventType)
            ? p.event_type
            : 'geopolitics') as EventType,
          primary_latitude: p.latitude,
          primary_longitude: p.longitude,
          start_time: p.published_at ?? new Date().toISOString(),
          end_time: null,
          confidence_score: 0.5,
          canada_impact_summary: '',
          image_url: p.image_url ?? null,
          image_s3_url: p.s3_url ?? null,
        }))

        const times = mappedEvents
          .map(e => new Date(e.start_time).getTime())
          .filter(t => !isNaN(t))
        const twoWeeksAgo = new Date(Date.now() - 31 * 24 * 60 * 60 * 1000)
        const minTime = twoWeeksAgo.toISOString()
        const maxTime = times.length
          ? new Date(Math.max(...times)).toISOString()
          : new Date().toISOString()

        const syntheticTimeline: TimelineResponse = {
          events: mappedEvents,
          min_time: minTime,
          max_time: maxTime,
        }

        const mappedArcs: ArcData[] = arcsData.arcs.map(a => {
          const eventType = (KNOWN_TYPES.includes(a.event_type_a as EventType)
            ? a.event_type_a
            : 'geopolitics') as EventType
          return {
            startLat: a.start_lat,
            startLng: a.start_lng,
            endLat: a.end_lat,
            endLng: a.end_lng,
            color: EVENT_TYPE_COLORS[eventType],
            relationshipType: 'embedding_similarity',
            eventAId: a.event_a_id,
            eventBId: a.event_b_id,
          }
        })

        setTimeline(syntheticTimeline)
        setEvents(mappedEvents)
        setArcs(mappedArcs)
        setLoading(false)
      } catch (e) {
        if (!cancelled) {
          setError(String(e))
          setLoading(false)
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [setEvents, setTimeline, setArcs])

  if (loading) return <LoadingOverlay />
  if (error) return <ErrorOverlay message={error} />

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Globe — full screen base layer */}
      <div className="absolute inset-0">
        <GlobeView />
      </div>

      {/* Filter bar — top overlay */}
      <FilterBar />

      {/* Timeline slider — bottom overlay */}
      <TimelineSlider />

      {/* Event modal — right side overlay */}
      <EventModal />

      {/* Agent panel — left slide-out overlay */}
      <AgentPanel />

      {/* Agent launcher button — top-right corner */}
      <AgentLauncherButton />
    </div>
  )
}
