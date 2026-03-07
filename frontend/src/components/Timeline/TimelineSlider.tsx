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
    // Reset to start if at end
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
    const stepMs = range / 120 // advance in 120 steps
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
    <div className="absolute bottom-0 left-0 right-0 z-20 px-6 pb-4 pt-3" style={{ background: 'linear-gradient(to top, rgba(15,23,42,0.95) 0%, rgba(15,23,42,0.85) 70%, transparent 100%)' }}>
      {/* Date labels */}
      <div className="flex justify-between text-xs text-slate-400 mb-2 px-1">
        <span>{formatDate(new Date(minTime))}</span>
        {timelinePosition && (
          <span className="text-blue-400 font-medium">{formatDate(timelinePosition)}</span>
        )}
        <span>{formatDate(new Date(maxTime))}</span>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3">
        {/* Play/Pause button */}
        <button
          onClick={isPlaying ? stopPlay : startPlay}
          className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-colors"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <rect x="5" y="4" width="3" height="12"/>
              <rect x="12" y="4" width="3" height="12"/>
            </svg>
          ) : (
            <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6 4l12 6-12 6z"/>
            </svg>
          )}
        </button>

        {/* Slider */}
        <div className="relative flex-1">
          {/* Progress track */}
          <div className="absolute top-1/2 left-0 h-1 rounded-full bg-slate-700 -translate-y-1/2 w-full pointer-events-none" />
          <div
            className="absolute top-1/2 left-0 h-1 rounded-full bg-blue-500 -translate-y-1/2 pointer-events-none"
            style={{ width: `${pct}%` }}
          />
          <input
            type="range"
            min={minTime}
            max={maxTime}
            value={currentValue}
            onChange={handleSliderChange}
            className="relative w-full h-4 appearance-none bg-transparent cursor-pointer"
            style={{
              WebkitAppearance: 'none',
            }}
          />
        </div>
      </div>

      <style>{`
        input[type='range']::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3b82f6;
          border: 2px solid #fff;
          cursor: pointer;
          box-shadow: 0 0 0 2px rgba(59,130,246,0.4);
        }
        input[type='range']::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3b82f6;
          border: 2px solid #fff;
          cursor: pointer;
          box-shadow: 0 0 0 2px rgba(59,130,246,0.4);
        }
      `}</style>
    </div>
  )
}
