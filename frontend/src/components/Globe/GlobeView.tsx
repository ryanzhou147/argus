import { useRef, useEffect, useMemo, useCallback } from 'react'
import Globe from 'react-globe.gl'
import type { Event } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, type ArcData } from '../../context/AppContext'
import { useAgentContext } from '../../context/AgentContext'
import AgentNavigationOverlay from '../Agent/AgentNavigationOverlay'

interface GlobePoint {
  id: string
  lat: number
  lng: number
  color: string
  size: number
  label: string
  event: Event
  isPulsing: boolean
}

export default function GlobeView() {
  const globeRef = useRef<any>(null)
  const { events, timelinePosition, activeFilters, setSelectedEventId, arcs, isAutoSpinning, stopAutoSpin } = useAppContext()
  const { activePulseIds, activeHighlights } = useAgentContext()

  // Compute visible events based on timeline + filters
  const visibleEvents = useMemo<Event[]>(() => {
    return events.filter(evt => {
      if (!activeFilters.has(evt.event_type)) return false
      if (timelinePosition && new Date(evt.start_time) > timelinePosition) return false
      return true
    })
  }, [events, timelinePosition, activeFilters])

  // Build point data for react-globe.gl
  const pulseSet = useMemo(() => new Set(activePulseIds), [activePulseIds])

  const points = useMemo<GlobePoint[]>(() => {
    return visibleEvents.map(evt => {
      const isPulsing = pulseSet.has(evt.id)
      const baseColor = EVENT_TYPE_COLORS[evt.event_type]
      const color = isPulsing ? '#ffffff' : baseColor
      return {
        id: evt.id,
        lat: evt.primary_latitude,
        lng: evt.primary_longitude,
        color,
        size: isPulsing ? (0.5 + evt.confidence_score * 0.4) * 1.8 : 0.5 + evt.confidence_score * 0.4,
        label: `<div style="background:rgba(15,23,42,0.9);color:white;padding:8px 12px;border-radius:6px;font-size:12px;max-width:200px;border:1px solid ${baseColor}"><strong>${evt.title}</strong><br/><span style="color:${baseColor};font-size:11px">${evt.event_type.replace(/_/g, ' ')}</span></div>`,
        event: evt,
        isPulsing,
      }
    })
  }, [visibleEvents, pulseSet])

  // Build visible arc IDs
  const visibleIds = useMemo(() => new Set(visibleEvents.map(e => e.id)), [visibleEvents])

  // Build highlighted arc pairs from agent context
  const highlightedArcKeys = useMemo(() => {
    return new Set(activeHighlights.map(h => [h.event_a_id, h.event_b_id].sort().join('|')))
  }, [activeHighlights])

  const visibleArcs = useMemo<ArcData[]>(() => {
    return arcs
      .filter(a => visibleIds.has(a.eventAId) && visibleIds.has(a.eventBId))
      .map(a => {
        const key = [a.eventAId, a.eventBId].sort().join('|')
        if (highlightedArcKeys.has(key)) {
          return { ...a, color: '#ffffff', highlighted: true }
        }
        return a
      })
  }, [arcs, visibleIds, highlightedArcKeys])

  const handlePointClick = useCallback((point: object) => {
    const p = point as GlobePoint
    if (p?.id) {
      stopAutoSpin()
      setSelectedEventId(p.id)
    }
  }, [setSelectedEventId, stopAutoSpin])

  // Auto-rotate globe based on isAutoSpinning state
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    globe.controls().autoRotate = isAutoSpinning
    globe.controls().autoRotateSpeed = 0.3
  }, [isAutoSpinning])

  // Stop auto-spin on any user interaction with globe controls
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    const controls = globe.controls()
    const handleStart = () => stopAutoSpin()
    controls.addEventListener('start', handleStart)
    return () => controls.removeEventListener('start', handleStart)
  }, [stopAutoSpin])

  return (
    <div className="w-full h-full">
      <Globe
        ref={globeRef}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        // Points
        pointsData={points}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointRadius="size"
        pointAltitude={0.015}
        pointLabel="label"
        onPointClick={handlePointClick}
        // Arcs
        arcsData={visibleArcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor={(d: object) => {
          const arc = d as ArcData & { highlighted?: boolean }
          if (arc.highlighted) return ['#ffffff', '#ffffff88']
          return [arc.color, `${arc.color}44`]
        }}
        arcAltitude={0.25}
        arcStroke={(d: object) => {
          const arc = d as ArcData & { highlighted?: boolean }
          return arc.highlighted ? 1.2 : 0.4
        }}
        arcDashLength={0.4}
        arcDashGap={0.2}
        arcDashAnimateTime={2000}
        // Atmosphere
        atmosphereColor="#1e40af"
        atmosphereAltitude={0.15}
        width={window.innerWidth}
        height={window.innerHeight}
      />
      <AgentNavigationOverlay globeRef={globeRef} />
    </div>
  )
}
