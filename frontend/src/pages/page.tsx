import React, { useCallback, useEffect, useState, useMemo } from 'react'
import parseMidiFile from '../utils/midiParser'
import PianoRoll from '../../../components/PianoRoll'
import useGameLoop from '../../../hooks/useGameLoop'

type Song = {
  title?: string
  events?: Array<{
    pitch: number;
    startTime: number;
    duration: number;
  }>
  metadata?: Record<string, any>
}

export default function Page(): JSX.Element {
  const [song, setSong] = useState<Song | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [liveMidiInput, setLiveMidiInput] = useState<any>(null)
  
  // Convert song events to TargetNote format
  const targetNotes = useMemo(() => {
    if (!song?.events) return []
    return song.events.map((ev, idx) => ({
      pitch: ev.pitch,
      startTime: ev.startTime,
      duration: ev.duration,
      id: idx,
    }))
  }, [song])

  // Use optimized game loop
  const { score, feedbackMessage, shouldPause } = useGameLoop(
    targetNotes,
    liveMidiInput,
    currentTime,
    false // waitModeEnabled
  )

  // Handler for dropped file(s) - with async parsing
  const onFile = useCallback(async (file: File) => {
    setIsLoading(true)
    setLoadingProgress(0)
    
    try {
      // Show progress (simulated - real implementation would track actual progress)
      setLoadingProgress(10)
      
      const buffer = await file.arrayBuffer()
      setLoadingProgress(50)
      
      // Parse in worker (non-blocking)
      const parsed = await parseMidiFile(buffer)
      setLoadingProgress(90)
      
      const loaded: Song = { 
        title: file.name, 
        events: parsed.events, 
        metadata: parsed.meta 
      }
      
      setSong(loaded)
      setLoadingProgress(100)
      
      // Small delay to show completion
      setTimeout(() => {
        setIsLoading(false)
        setLoadingProgress(0)
      }, 300)
    } catch (err) {
      console.error('Failed to load MIDI:', err)
      alert('Failed to load MIDI file')
      setIsLoading(false)
      setLoadingProgress(0)
    }
  }, [])

  // Simple file input dropzone
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f) onFile(f)
  }, [onFile])

  const onSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) onFile(f)
  }, [onFile])

  // Playback loop - use requestAnimationFrame instead of setInterval
  useEffect(() => {
    if (!isPlaying || !song) return

    let animationFrameId: number
    const startTime = performance.now() - (currentTime * 1000)

    const tick = () => {
      const now = performance.now()
      const elapsed = (now - startTime) / 1000
      
      setCurrentTime(elapsed)
      
      if (!shouldPause) {
        animationFrameId = requestAnimationFrame(tick)
      }
    }

    animationFrameId = requestAnimationFrame(tick)

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId)
      }
    }
  }, [isPlaying, song, shouldPause, currentTime])

  // MIDI input handling (if Web MIDI API is available)
  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.requestMIDIAccess) {
      return
    }

    let midiAccess: MIDIAccess | null = null
    let currentInput: MIDIInput | null = null

    navigator.requestMIDIAccess().then((access) => {
      midiAccess = access
      
      // Auto-select first input
      const inputs = Array.from(access.inputs.values())
      if (inputs.length > 0) {
        currentInput = inputs[0]
        currentInput.onmidimessage = (e: MIDIMessageEvent) => {
          const [status, note, velocity] = e.data
          const isNoteOn = (status & 0xf0) === 0x90 && velocity > 0
          
          if (isNoteOn) {
            setLiveMidiInput({
              note,
              velocity,
              timestamp: currentTime,
              type: 'noteOn',
            })
          }
        }
      }
    })

    return () => {
      if (currentInput) {
        currentInput.onmidimessage = null
      }
      if (midiAccess) {
        midiAccess.close()
      }
    }
  }, [currentTime])

  return (
    <div style={{ padding: 16 }} onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
      <header>
        <h1>Parris Piano — Tutor</h1>
        <div style={{ marginBottom: 8 }}>
          <input 
            type="file" 
            accept=".mid,.midi" 
            onChange={onSelect}
            disabled={isLoading}
          />
          {isLoading && (
            <div>
              <progress value={loadingProgress} max={100} />
              <span>Loading... {loadingProgress}%</span>
            </div>
          )}
          <button 
            onClick={() => setIsPlaying(!isPlaying)} 
            disabled={!song || isLoading}
          >
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          <button 
            onClick={() => { 
              setSong(null)
              setCurrentTime(0)
              setIsPlaying(false)
            }}
            disabled={isLoading}
          >
            Unload
          </button>
        </div>
      </header>

      <main>
        <section style={{ display: 'flex', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <h2>Visualizer</h2>
            {song && (
              <PianoRoll 
                targetNotes={targetNotes}
                currentTime={currentTime}
              />
            )}
          </div>

          <aside style={{ width: 320 }}>
            <h3>Song</h3>
            <div>{song?.title ?? 'No song loaded'}</div>

            <h3>Controls</h3>
            <div>Playhead: {currentTime.toFixed(2)}s</div>
            <div>Tempo: {song?.metadata?.tempo ?? '—'}</div>

            <h3>Score</h3>
            <div>Hits: {score.hits}</div>
            <div>Misses: {score.misses}</div>
            <div>Streak: {score.streak}</div>
            {feedbackMessage && (
              <div style={{ color: 'green', fontWeight: 'bold' }}>
                {feedbackMessage}
              </div>
            )}
          </aside>
        </section>
      </main>
    </div>
  )
}
