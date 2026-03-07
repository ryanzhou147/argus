import { useRef, useEffect, useMemo, useCallback, useState } from 'react'
import Globe from 'react-globe.gl'
import * as THREE from 'three'
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

  // Monochrome globe material — medium dark grey base
  const globeMaterial = useMemo(() => new THREE.MeshPhongMaterial({
    color: '#141414',
    emissive: '#0a0a0a',
    specular: '#2a2a2a',
    shininess: 4,
  }), [])

  // Country hex-dot layer
  const [countriesData, setCountriesData] = useState<{ features: object[] }>({ features: [] })
  useEffect(() => {
    fetch('/countries.geojson').then(r => r.json()).then(setCountriesData)
  }, [])

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
        label: `<div style="background:#111111;color:#b8b8b8;padding:6px 10px;font-size:11px;max-width:200px;border:1px solid #2a2a2a;font-family:Space Mono,Courier New,monospace"><strong style="color:#d0d0d0;font-size:11px">${evt.title}</strong><br/><span style="color:${baseColor};font-size:10px">${evt.event_type.replace(/_/g, ' ')}</span></div>`,
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

  // Disable raycasting on arc tube meshes so they never block point clicks
  useEffect(() => {
    const globe = globeRef.current
    if (!globe) return
    const timer = setTimeout(() => {
      globe.scene().traverse((obj: THREE.Object3D) => {
        const mesh = obj as THREE.Mesh
        if (mesh.isMesh && mesh.geometry?.type === 'TubeGeometry') {
          mesh.raycast = () => {}
        }
      })
    }, 50)
    return () => clearTimeout(timer)
  }, [visibleArcs])

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
    <div className="w-full h-full bg-black">
      <Globe
        ref={globeRef}
        globeMaterial={globeMaterial}
        showGraticules={false}
        backgroundImageUrl=""
        // Country hex dots — land layer
        hexPolygonsData={countriesData.features}
        hexPolygonResolution={4}
        hexPolygonMargin={0.7}
        hexPolygonAltitude={0.004}
        hexPolygonColor={(d: object) => {
          const props = (d as { properties?: Record<string, string> }).properties ?? {}
          const isCanada = props.ISO_A3 === 'CAN' || props.iso_a3 === 'CAN' || props.ADMIN === 'Canada' || props.NAME === 'Canada'
          return isCanada ? 'rgba(220, 60, 40, 0.95)' : 'rgba(255, 255, 255, 0.5)'
        }}
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
          if (arc.highlighted) return ['#ffffffaa', '#ffffff44']
          return [`${arc.color}55`, `${arc.color}22`]
        }}
        arcAltitude={0.25}
        arcStroke={(d: object) => {
          const arc = d as ArcData & { highlighted?: boolean }
          return arc.highlighted ? 0.8 : 0.25
        }}
        arcDashLength={1}
        arcDashGap={0}
        // Atmosphere
        atmosphereColor="#555555"
        atmosphereAltitude={0.06}
        width={window.innerWidth}
        height={window.innerHeight}
      />
      <AgentNavigationOverlay globeRef={globeRef} />
    </div>
  )
}
