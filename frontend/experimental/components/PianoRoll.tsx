import React, { useEffect, useRef, useCallback, useMemo } from 'react';

interface TargetNote {
  pitch: number;      // MIDI note number (0-127)
  startTime: number; // Start time in seconds
  duration: number;   // Duration in seconds
}

interface PianoRollProps {
  targetNotes: TargetNote[];
  currentTime: number; // Current playback time in seconds
}

const PianoRoll: React.FC<PianoRollProps> = ({ targetNotes, currentTime }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const keysRef = useRef<Map<number, number>>(new Map()); // Map pitch to x-position
  const lastFilterTimeRef = useRef<number>(0);
  const cachedVisibleNotesRef = useRef<TargetNote[]>([]);

  // Piano roll configuration
  const NOTE_HEIGHT = 20; // Height of each note bar in pixels
  const HIT_LINE_Y = 0.85; // Hit line position (85% from top)
  const NOTE_SPEED = 200; // Pixels per second (falling speed)
  const LOOK_AHEAD = 3; // Seconds ahead to show notes
  const LOOK_BACK = 0.5; // Seconds behind to show notes
  const FILTER_THROTTLE = 0.05; // Re-filter only every 50ms (20fps instead of 60fps)

  // Memoize visible notes - only recalculate when currentTime changes significantly
  const visibleNotes = useMemo(() => {
    // Throttle filtering: only re-filter every 50ms
    const timeDiff = Math.abs(currentTime - lastFilterTimeRef.current);
    if (timeDiff < FILTER_THROTTLE && lastFilterTimeRef.current > 0) {
      // Return cached result if time hasn't changed much
      return cachedVisibleNotesRef.current;
    }
    lastFilterTimeRef.current = currentTime;

    // Binary search optimization: if notes are sorted by time, we can use binary search
    // For now, simple filter but with early exit optimizations
    const result: TargetNote[] = [];
    const timeWindowStart = currentTime - LOOK_BACK;
    const timeWindowEnd = currentTime + LOOK_AHEAD;

    // Early exit optimizations
    for (let i = 0; i < targetNotes.length; i++) {
      const note = targetNotes[i];
      const noteEndTime = note.startTime + note.duration;

      // Skip notes that are too far in the past
      if (noteEndTime < timeWindowStart) {
        continue; // Skip but don't break (notes might not be sorted)
      }

      // Break early if we've passed all relevant notes (assuming sorted)
      if (note.startTime > timeWindowEnd) {
        break;
      }

      // Include note if it's within window
      if (noteEndTime >= timeWindowStart && note.startTime <= timeWindowEnd) {
        result.push(note);
      }
    }

    cachedVisibleNotesRef.current = result;
    return result;
  }, [targetNotes, currentTime]);

  // Initialize keyboard layout (map MIDI notes to x positions)
  const initializeKeys = useCallback((canvas: HTMLCanvasElement) => {
    const keys = new Map<number, number>();
    const width = canvas.width;
    const keyWidth = width / 88; // 88 keys total
    
    // MIDI note 21 (A0) to 108 (C8) = 88 keys
    let xPos = 0;
    for (let note = 21; note <= 108; note++) {
      keys.set(note, xPos);
      xPos += keyWidth;
    }
    
    keysRef.current = keys;
  }, []);

  // Get note color based on pitch (white vs black key) - memoized
  const getNoteColor = useCallback((pitch: number): string => {
    const noteClass = pitch % 12;
    const isBlackKey = [1, 3, 6, 8, 10].includes(noteClass);
    
    if (isBlackKey) {
      return '#4a5568'; // Dark gray for black keys
    }
    
    // Color gradient for white keys based on octave
    const octave = Math.floor(pitch / 12);
    const hue = (octave * 30) % 360;
    return `hsl(${hue}, 70%, 60%)`;
  }, []);

  // Render the piano roll - optimized to use memoized visibleNotes
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const hitLineY = height * HIT_LINE_Y;

    // Clear canvas
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines for each octave (only redraw if canvas size changed)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    const keyWidth = width / 88;
    for (let i = 0; i <= 88; i++) {
      const x = i * keyWidth;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Draw hit line
    ctx.strokeStyle = '#ff6b6b';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, hitLineY);
    ctx.lineTo(width, hitLineY);
    ctx.stroke();

    // Draw hit line label
    ctx.fillStyle = '#ff6b6b';
    ctx.font = '14px Arial';
    ctx.fillText('HIT LINE', 10, hitLineY - 5);

    // Draw notes - using pre-filtered visibleNotes
    visibleNotes.forEach(note => {
      const xPos = keysRef.current.get(note.pitch);
      if (xPos === undefined) return;

      const noteStartY = hitLineY - (currentTime - note.startTime) * NOTE_SPEED;
      const noteEndY = hitLineY - (currentTime - (note.startTime + note.duration)) * NOTE_SPEED;
      const noteHeight = Math.max(4, noteEndY - noteStartY);

      // Determine if note has passed hit line
      const hasPassed = noteEndY > hitLineY;
      const isActive = noteStartY <= hitLineY && noteEndY >= hitLineY;

      // Set color and opacity
      let color = getNoteColor(note.pitch);
      let opacity = 1.0;

      if (hasPassed) {
        // Notes that have passed turn gray and fade
        color = '#6b7280';
        opacity = 0.3;
      } else if (isActive) {
        // Active notes at hit line are brighter
        opacity = 1.0;
        color = '#60a5fa'; // Bright blue for active notes
      }

      // Draw note rectangle
      ctx.fillStyle = color;
      ctx.globalAlpha = opacity;
      ctx.fillRect(xPos, noteStartY, keyWidth - 2, noteHeight);

      // Draw note border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      ctx.strokeRect(xPos, noteStartY, keyWidth - 2, noteHeight);

      ctx.globalAlpha = 1.0;
    });

    // Draw time indicator
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.font = '12px Arial';
    ctx.fillText(`Time: ${currentTime.toFixed(2)}s`, width - 120, 20);
    ctx.fillText(`Notes: ${visibleNotes.length}`, width - 120, 40);
  }, [visibleNotes, currentTime, getNoteColor]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Initialize canvas size
    const resizeCanvas = () => {
      const container = canvas.parentElement;
      if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight || 600;
        initializeKeys(canvas);
      }
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Animation loop
    const animate = () => {
      render();
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [render, initializeKeys]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#0f0f1e' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
    </div>
  );
};

export default PianoRoll;
export type { TargetNote, PianoRollProps };
