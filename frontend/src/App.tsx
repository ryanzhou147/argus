import { useEffect, useState } from 'react'
import { getTimeline, getRelatedEvents } from './api/client'
import { useAppContext, buildArcs } from './context/AppContext'
import type { RelatedEvent } from './types/events'
import GlobeView from './components/Globe/GlobeView'
import FilterBar from './components/Filters/FilterBar'
import TimelineSlider from './components/Timeline/TimelineSlider'
import EventModal from './components/Modal/EventModal'
import Legend from './components/Legend'
import AgentLauncherButton from './components/Agent/AgentLauncherButton'
import AgentPanel from './components/Agent/AgentPanel'

function LoadingOverlay() {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-950">
      <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
      <p className="text-slate-400 text-sm">Loading event intelligence...</p>
    </div>
  )
}

function ErrorOverlay({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-950">
      <p className="text-red-400 text-sm mb-2">Failed to connect to backend.</p>
      <p className="text-slate-500 text-xs">{message}</p>
      <p className="text-slate-500 text-xs mt-2">Make sure the FastAPI server is running at http://localhost:8000</p>
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
        const timelineData = await getTimeline()
        if (cancelled) return

        setTimeline(timelineData)
        setEvents(timelineData.events)

        // Fetch related events for all events to build arcs
        const relatedMap = new Map<string, RelatedEvent[]>()
        await Promise.allSettled(
          timelineData.events.map(async evt => {
            try {
              const r = await getRelatedEvents(evt.id)
              relatedMap.set(evt.id, r.related_events)
            } catch {
              // Non-critical: arcs just won't show for this event
            }
          })
        )

        if (cancelled) return

        const visibleIds = new Set(timelineData.events.map(e => e.id))
        const arcs = buildArcs(timelineData.events, relatedMap, visibleIds)
        setArcs(arcs)
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
    <div className="relative w-screen h-screen overflow-hidden bg-slate-950">
      {/* Globe — full screen base layer */}
      <div className="absolute inset-0">
        <GlobeView />
      </div>

      {/* Filter bar — top overlay */}
      <FilterBar />

      {/* Legend — bottom-left overlay */}
      <Legend />

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
