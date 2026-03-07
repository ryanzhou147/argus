import { useState, useCallback, useEffect, useRef } from 'react'
import { useAgentContext } from '../../context/AgentContext'
import { useAppContext } from '../../context/AppContext'
import AgentAnswerView from './AgentAnswerView'

export default function AgentPanel() {
  const { isPanelOpen, togglePanel, isLoading, agentResponse, error, submitQuery } = useAgentContext()
  const { stopAutoSpin } = useAppContext()
  const [inputValue, setInputValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    if (isPanelOpen) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isPanelOpen])

  const handleSubmit = useCallback(async () => {
    const q = inputValue.trim()
    if (!q || isLoading) return
    stopAutoSpin()
    setInputValue('')
    await submitQuery(q)
  }, [inputValue, isLoading, submitQuery, stopAutoSpin])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  // Cleanup on unmount or if recording state changes unexpectedly
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Pick best supported MIME type across browsers (Chrome: webm, Firefox: ogg)
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : ''

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Use actual MIME type from recorder, not a hardcoded assumption
        const actualMime = mediaRecorder.mimeType || 'audio/webm'
        const ext = actualMime.includes('mp4') ? 'mp4' : actualMime.includes('ogg') ? 'ogg' : 'webm'
        const audioBlob = new Blob(audioChunksRef.current, { type: actualMime })
        audioChunksRef.current = []

        setIsTranscribing(true)
        setIsRecording(false)

        try {
          const formData = new FormData()
          formData.append('file', audioBlob, `audio.${ext}`)
          formData.append('model_id', 'scribe_v1')

          const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
            method: 'POST',
            headers: {
              'xi-api-key': import.meta.env.VITE_ELEVENLABS_API_KEY || '',
            },
            body: formData,
          })

          if (!response.ok) {
            const errText = await response.text()
            throw new Error(`ElevenLabs ${response.status}: ${errText}`)
          }

          const data = await response.json()
          if (data.text) {
            setInputValue(prev => (prev.length > 0 ? `${prev} ${data.text}` : data.text))
          }
        } catch (err) {
          console.error('Voice transcription error:', err)
        } finally {
          setIsTranscribing(false)
          stream.getTracks().forEach(track => track.stop())
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Microphone access error:', err)
      setIsRecording(false)
    }
  }

  const stopRecording = () => {
    // Check the recorder's actual state, not React state, to avoid stale closure
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const exampleQueries = [
    'Why did the Red Sea shipping disruption happen?',
    'What is the financial impact of the OPEC production cut on Canada?',
    'What events are related to the semiconductor export controls?',
  ]

  return (
    <div
      className="fixed top-0 left-0 h-full z-30 pointer-events-none"
      style={{ width: '420px', maxWidth: '100vw' }}
    >
      <div
        className="h-full w-full pointer-events-auto flex flex-col"
        style={{
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          transform: isPanelOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.25s ease',
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <svg className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-xs font-bold tracking-widest uppercase" style={{ color: 'var(--text-bright)' }}>AI Globe Copilot</span>
          <span className="text-xs ml-1" style={{ color: 'var(--text-muted)' }}>Gemini</span>
          <button
            onClick={togglePanel}
            className="ml-auto w-6 h-6 flex items-center justify-center transition-colors"
            style={{ background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', color: 'var(--text-secondary)' }}
            aria-label="Close panel"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!agentResponse && !isLoading && !error && (
            <div className="flex flex-col gap-4">
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Ask me anything about global events and their impact on Canada. I'll navigate the globe to show you the relevant events.
              </p>
              <div>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>Try asking</div>
                <div className="flex flex-col gap-1.5">
                  {exampleQueries.map(q => (
                    <button
                      key={q}
                      onClick={() => setInputValue(q)}
                      className="text-left text-xs px-3 py-2 transition-colors"
                      style={{ color: 'var(--text-secondary)', background: 'var(--bg-raised)', border: '1px solid var(--border)' }}
                      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
                      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-6 h-6 border border-[#505050] border-t-transparent animate-spin" style={{ borderRadius: 0 }} />
              <p className="text-xs tracking-widest uppercase" style={{ color: 'var(--text-secondary)' }}>Analyzing global events...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="p-3" style={{ background: 'var(--bg-raised)', border: '1px solid #3a2020', borderLeft: '2px solid #7a3030' }}>
              <p className="text-xs" style={{ color: '#8a4040' }}>Failed to get agent response.</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{error}</p>
            </div>
          )}

          {agentResponse && !isLoading && (
            <AgentAnswerView response={agentResponse} />
          )}
        </div>

        {/* Input area */}
        <div className="px-4 py-3 flex-shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="flex gap-2 items-center">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? "Listening..." : isTranscribing ? "Transcribing..." : "Ask about global events..."}
              disabled={isLoading || isRecording || isTranscribing}
              className="flex-1 text-xs px-3 py-2 transition-colors disabled:opacity-50"
              style={{ background: 'var(--bg-raised)', color: 'var(--text-primary)', border: '1px solid var(--border-strong)', outline: 'none' }}
              onFocus={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
            />
            <button
              onClick={toggleRecording}
              disabled={isLoading || isTranscribing}
              className={`w-9 h-9 flex items-center justify-center transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed ${isRecording ? 'animate-pulse' : ''}`}
              style={{
                 background: isRecording ? '#dc2626' : 'var(--bg-raised)',
                 border: '1px solid var(--border-strong)',
                 color: isRecording ? '#fff' : 'var(--text-primary)'
              }}
              aria-label={isRecording ? "Stop recording" : "Start voice recording"}
            >
              {isTranscribing ? (
                <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent animate-spin rounded-full" />
              ) : isRecording ? (
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 18h12V6H6v12z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              )}
            </button>
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || isLoading}
              className="w-9 h-9 flex items-center justify-center transition-colors flex-shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)' }}
              aria-label="Submit query"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
