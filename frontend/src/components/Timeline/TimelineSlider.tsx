import { useEffect, useRef, useState, useCallback } from 'react'
import { useAppContext } from '../../context/AppContext'

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function TimelineSlider() {
  const { timeline, timelinePosition, setTimelinePosition } = useAppContext()
  const [isPlaying, setIsPlaying] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const minTime = timeline ? new Date(timeline.min_time).getTime() : 0
  const maxTime = timeline ? new Date(timeline.max_time).getTime() : 0
  const range = maxTime - minTime || 1

  const currentValue = timelinePosition ? timelinePosition.getTime() : maxTime

  // Initialize timeline position to max (show all events) on mount
  useEffect(() => {
    if (timeline && !timelinePosition) {
      setTimelinePosition(new Date(timeline.max_time))
    }
  }, [timeline, timelinePosition, setTimelinePosition])

  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setTimelinePosition(new Date(Number(e.target.value)))
  }, [setTimelinePosition])

  const startPlay = useCallback(() => {
    if (isPlaying) return
    setIsPlaying(true)
    if (currentValue >= maxTime) {
      setTimelinePosition(new Date(minTime))
    }
  }, [isPlaying, currentValue, maxTime, minTime, setTimelinePosition])

  const stopPlay = useCallback(() => {
    setIsPlaying(false)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!isPlaying) return
    const stepMs = range / 120
    intervalRef.current = setInterval(() => {
      setTimelinePosition(prev => {
        const next = (prev ? prev.getTime() : minTime) + stepMs
        if (next >= maxTime) {
          setIsPlaying(false)
          return new Date(maxTime)
        }
        return new Date(next)
      })
    }, 150)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isPlaying, minTime, maxTime, range, setTimelinePosition])

  if (!timeline) return null

  const pct = ((currentValue - minTime) / range) * 100

  return (
    <div
      className="absolute bottom-0 left-0 right-0 z-20 px-6 pb-4 pt-3"
      style={{ background: 'linear-gradient(to top, rgba(8,8,8,0.97) 0%, rgba(8,8,8,0.85) 70%, transparent 100%)' }}
    >
      {/* Date labels */}
      <div className="flex justify-between text-xs mb-2 px-1" style={{ color: 'var(--text-muted)' }}>
        <span>{formatDate(new Date(minTime))}</span>
        {timelinePosition && (
          <span style={{ color: 'var(--text-secondary)' }}>{formatDate(timelinePosition)}</span>
        )}
        <span>{formatDate(new Date(maxTime))}</span>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3">
        {/* Play/Pause button — square */}
        <button
          onClick={isPlaying ? stopPlay : startPlay}
          className="flex-shrink-0 w-8 h-8 flex items-center justify-center transition-colors"
          style={{
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-strong)',
            color: 'var(--text-primary)',
          }}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <rect x="5" y="4" width="3" height="12"/>
              <rect x="12" y="4" width="3" height="12"/>
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          )}
        </button>

        {/* Slider */}
        <div className="relative flex-1">
          {/* Track background */}
          <div
            className="absolute top-1/2 left-0 h-px w-full pointer-events-none -translate-y-1/2"
            style={{ background: 'var(--border-strong)' }}
          />
          {/* Progress fill */}
          <div
            className="absolute top-1/2 left-0 h-px pointer-events-none -translate-y-1/2"
            style={{ width: `${pct}%`, background: 'var(--text-secondary)' }}
          />
          <input
            type="range"
            min={minTime}
            max={maxTime}
            value={currentValue}
            onChange={handleSliderChange}
            className="relative w-full h-4 appearance-none bg-transparent cursor-pointer"
            style={{ WebkitAppearance: 'none' }}
          />
        </div>
      </div>

      <style>{`
        input[type='range']::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 10px;
          height: 16px;
          border-radius: 0;
          background: #c0c0c0;
          border: 1px solid #444444;
          cursor: pointer;
        }
        input[type='range']::-moz-range-thumb {
          width: 10px;
          height: 16px;
          border-radius: 0;
          background: #c0c0c0;
          border: 1px solid #444444;
          cursor: pointer;
        }
      `}</style>
    </div>
  )
}
