import { useRef, useEffect, useMemo, useCallback, useState } from 'react'
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
  const { activeHighlights } = useAgentContext()

  // Track camera altitude via ref so the points array never recalculates on zoom.
  // A rAF-throttled tick triggers re-renders so the pointRadius accessor picks up
  // the new altitude without rebuilding or rememoising the points array.
  const altRef = useRef(2.5)
  const rafRef = useRef<number | null>(null)
  const [, setAltitudeTick] = useState(0)

  const handleZoom = useCallback(({ altitude }: { altitude: number }) => {
    // onZoom fires during rotation/inertia too — skip if altitude didn't actually change
    if (Math.abs(altitude - altRef.current) < 0.01) return
    altRef.current = altitude
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null
        setAltitudeTick(t => t + 1)
      })
    }
  }, [])

  // Compute visible event IDs based on timeline + filters
  const visibleIds = useMemo(() => {
    const ids = new Set<string>()
    for (const evt of events) {
      if (!activeFilters.has(evt.event_type)) continue
      if (timelinePosition && new Date(evt.start_time) > timelinePosition) continue
      ids.add(evt.id)
    }
    return ids
  }, [events, timelinePosition, activeFilters])

  // All points — never filtered out, so pointsData is stable and react-globe.gl
  // never re-animates on filter change. Visibility is controlled via pointRadius/pointColor.
  const allPoints = useMemo<GlobePoint[]>(() => {
    return events.map(evt => {
      const baseColor = EVENT_TYPE_COLORS[evt.event_type] ?? '#888888'
      return {
        id: evt.id,
        lat: evt.primary_latitude,
        lng: evt.primary_longitude,
        color: baseColor,
        size: 0.2,
        label: `<div style="background:rgba(15,23,42,0.9);color:white;padding:8px 12px;border-radius:6px;font-size:12px;max-width:200px;border:1px solid ${baseColor}"><strong>${evt.title}</strong><br/><span style="color:${baseColor};font-size:11px">${evt.event_type.replace(/_/g, ' ')}</span></div>`,
        event: evt,
        isPulsing: false,
      }
    })
  }, [events])

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

  // Cancel any pending rAF on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [])

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
        pointsData={allPoints}
        pointLat="lat"
        pointLng="lng"
        pointColor={(d: object) => {
          const p = d as GlobePoint
          return visibleIds.has(p.id) ? p.color : 'rgba(0,0,0,0)'
        }}
        pointRadius={(d: object) => {
          const p = d as GlobePoint
          if (!visibleIds.has(p.id)) return 0
          return Math.max(p.size * (altRef.current / 2.5), 0.1)
        }}
        pointResolution={6}
        pointAltitude={0.015}
        pointLabel="label"
        onPointClick={handlePointClick}
        onZoom={handleZoom}
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
