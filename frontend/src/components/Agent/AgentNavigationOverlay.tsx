import { useEffect, useRef } from 'react'
import { useAgentContext } from '../../context/AgentContext'
import { useAppContext } from '../../context/AppContext'

interface Props {
  globeRef: React.RefObject<any>
}

const ZOOM_ALTITUDE: Record<string, number> = {
  cluster: 2.5,
  event: 1.2,
}

export default function AgentNavigationOverlay({ globeRef }: Props) {
  const { activeNavigationPlan, agentResponse } = useAgentContext()
  const { setSelectedEventId, events, stopAutoSpin } = useAppContext()
  const prevPlanRef = useRef<string | null>(null)

  useEffect(() => {
    if (!activeNavigationPlan) return
    const planKey = JSON.stringify(activeNavigationPlan)
    if (planKey === prevPlanRef.current) return
    prevPlanRef.current = planKey

    const globe = globeRef.current
    if (!globe) return

    // Stop auto-spin immediately on agent navigation
    stopAutoSpin()

    const { center_on_event_id, zoom_level, open_modal_event_id, pulse_event_ids } = activeNavigationPlan

    // Animate camera to center event
    if (center_on_event_id) {
      const targetEvent = events.find(e => e.id === center_on_event_id)
      if (targetEvent) {
        const altitude = ZOOM_ALTITUDE[zoom_level ?? 'cluster'] ?? 2.0
        globe.pointOfView(
          {
            lat: targetEvent.primary_latitude,
            lng: targetEvent.primary_longitude,
            altitude,
          },
          1500
        )

        // Sequenced multi-event focus: after centering on anchor, briefly show connected events
        const otherPulseIds = pulse_event_ids.filter(id => id !== center_on_event_id)
        if (otherPulseIds.length > 0) {
          otherPulseIds.slice(0, 3).forEach((id, idx) => {
            const evt = events.find(e => e.id === id)
            if (!evt) return
            setTimeout(() => {
              globe.pointOfView(
                {
                  lat: evt.primary_latitude,
                  lng: evt.primary_longitude,
                  altitude: ZOOM_ALTITUDE.cluster,
                },
                800
              )
              // Return to anchor after brief pause
              setTimeout(() => {
                if (targetEvent) {
                  globe.pointOfView(
                    {
                      lat: targetEvent.primary_latitude,
                      lng: targetEvent.primary_longitude,
                      altitude: ZOOM_ALTITUDE[zoom_level ?? 'cluster'] ?? 2.0,
                    },
                    800
                  )
                }
              }, 1200)
            }, 2500 + idx * 2500)
          })
        }

        // Auto-open modal after camera animation completes
        if (open_modal_event_id) {
          setTimeout(() => {
            setSelectedEventId(open_modal_event_id)
          }, 2000)
        }
      }
    }
  }, [activeNavigationPlan, agentResponse, globeRef, events, setSelectedEventId, stopAutoSpin])

  return null
}
