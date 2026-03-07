import { useRef, useEffect, useMemo, useCallback } from 'react'
import Globe from 'react-globe.gl'
import type { Event } from '../../types/events'
import { useAppContext, EVENT_TYPE_COLORS, type ArcData } from '../../context/AppContext'

interface GlobePoint {
  id: string
  lat: number
  lng: number
  color: string
  size: number
  label: string
  event: Event
}

export default function GlobeView() {
  const globeRef = useRef<any>(null)
  const { events, timelinePosition, activeFilters, setSelectedEventId, arcs } = useAppContext()

  // Compute visible events based on timeline + filters
  const visibleEvents = useMemo<Event[]>(() => {
    return events.filter(evt => {
      if (!activeFilters.has(evt.event_type)) return false
      if (timelinePosition && new Date(evt.start_time) > timelinePosition) return false
      return true
    })
  }, [events, timelinePosition, activeFilters])

  // Build point data for react-globe.gl
  const points = useMemo<GlobePoint[]>(() => {
    return visibleEvents.map(evt => ({
      id: evt.id,
      lat: evt.primary_latitude,
      lng: evt.primary_longitude,
      color: EVENT_TYPE_COLORS[evt.event_type],
      size: 0.5 + evt.confidence_score * 0.4,
      label: `<div style="background:rgba(15,23,42,0.9);color:white;padding:8px 12px;border-radius:6px;font-size:12px;max-width:200px;border:1px solid ${EVENT_TYPE_COLORS[evt.event_type]}"><strong>${evt.title}</strong><br/><span style="color:${EVENT_TYPE_COLORS[evt.event_type]};font-size:11px">${evt.event_type.replace(/_/g, ' ')}</span></div>`,
      event: evt,
    }))
  }, [visibleEvents])

  // Build visible arc IDs
  const visibleIds = useMemo(() => new Set(visibleEvents.map(e => e.id)), [visibleEvents])

  const visibleArcs = useMemo<ArcData[]>(() => {
    return arcs.filter(a => visibleIds.has(a.eventAId) && visibleIds.has(a.eventBId))
  }, [arcs, visibleIds])

  const handlePointClick = useCallback((point: object) => {
    const p = point as GlobePoint
    if (p?.id) setSelectedEventId(p.id)
  }, [setSelectedEventId])

  // Auto-rotate globe slowly
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    globe.controls().autoRotate = true
    globe.controls().autoRotateSpeed = 0.3
  }, [])

  // Stop auto-rotate when event is selected
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    // keep rotating regardless
  })

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
          const arc = d as ArcData
          return [arc.color, `${arc.color}44`]
        }}
        arcAltitude={0.25}
        arcStroke={0.4}
        arcDashLength={0.4}
        arcDashGap={0.2}
        arcDashAnimateTime={2000}
        // Atmosphere
        atmosphereColor="#1e40af"
        atmosphereAltitude={0.15}
        width={window.innerWidth}
        height={window.innerHeight}
      />
    </div>
  )
}
