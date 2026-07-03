import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// Interfaces
export interface TargetNote {
  pitch: number;      // MIDI note number (0-127)
  startTime: number;  // Start time in seconds
  duration: number;   // Duration in seconds
  id?: string | number; // Unique identifier if available, else index
}

export interface MidiEvent {
  note: number;
  velocity: number;
  timestamp: number; // In seconds, matching song time
  type: 'noteOn' | 'noteOff';
}

export interface ScoreState {
  hits: number;
  misses: number;
  streak: number;
}

interface GameLoopOutput {
  score: ScoreState;
  feedbackMessage: string | null;
  shouldPause: boolean;
}

// Constants for scoring windows (in seconds)
const WINDOW_PERFECT = 0.050; // ±50ms
const WINDOW_GOOD = 0.110;    // ±110ms
const TIME_UPDATE_THROTTLE = 0.1; // Update missed notes every 100ms instead of every frame

export const useGameLoop = (
  currentSong: TargetNote[],
  liveMidiInput: MidiEvent | null,
  currentTime: number,
  waitModeEnabled: boolean
): GameLoopOutput => {
  // Use refs for score to avoid state thrashing
  const scoreRef = useRef<ScoreState>({ hits: 0, misses: 0, streak: 0 });
  const [score, setScore] = useState<ScoreState>({ hits: 0, misses: 0, streak: 0 });
  
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [shouldPause, setShouldPause] = useState(false);

  // Keep track of processed notes to avoid double scoring
  const processedNotesRef = useRef<Set<number>>(new Set());
  
  // Track last time we checked for misses (throttling)
  const lastMissCheckRef = useRef<number>(0);
  
  // Batch update timer for score
  const scoreUpdateTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Memoize sorted notes by time for faster searching
  const sortedNotesRef = useRef<Array<{ note: TargetNote; index: number }>>([]);
  
  useEffect(() => {
    // Re-sort notes when song changes
    sortedNotesRef.current = currentSong
      .map((note, index) => ({ note, index }))
      .sort((a, b) => a.note.startTime - b.note.startTime);
    processedNotesRef.current.clear();
    scoreRef.current = { hits: 0, misses: 0, streak: 0 };
    setScore({ hits: 0, misses: 0, streak: 0 });
  }, [currentSong]);

  // Batch score updates to avoid excessive re-renders
  const updateScore = useCallback((updates: Partial<ScoreState>) => {
    scoreRef.current = { ...scoreRef.current, ...updates };
    
    // Debounce state update - only update React state every 200ms
    if (scoreUpdateTimerRef.current) {
      clearTimeout(scoreUpdateTimerRef.current);
    }
    
    scoreUpdateTimerRef.current = setTimeout(() => {
      setScore({ ...scoreRef.current });
    }, 200);
  }, []);

  // Optimized note search - binary search for time-based lookup
  const findNoteIndex = useCallback((pitch: number, timestamp: number): number => {
    // Binary search for notes around the timestamp
    const sorted = sortedNotesRef.current;
    let left = 0;
    let right = sorted.length - 1;
    let bestIndex = -1;
    let minDiff = Infinity;

    // Find notes within time window using binary search
    while (left <= right) {
      const mid = Math.floor((left + right) / 2);
      const noteTime = sorted[mid].note.startTime;
      
      if (Math.abs(noteTime - timestamp) < WINDOW_GOOD) {
        // Found a candidate, search nearby
        for (let i = Math.max(0, mid - 10); i < Math.min(sorted.length, mid + 10); i++) {
          const { note, index } = sorted[i];
          if (processedNotesRef.current.has(index)) continue;
          if (note.pitch !== pitch) continue;
          
          const diff = Math.abs(note.startTime - timestamp);
          if (diff <= WINDOW_GOOD && diff < minDiff) {
            minDiff = diff;
            bestIndex = index;
          }
        }
        break;
      } else if (noteTime < timestamp - WINDOW_GOOD) {
        left = mid + 1;
      } else {
        right = mid - 1;
      }
    }

    return bestIndex;
  }, []);

  // Handle incoming MIDI Input - optimized
  useEffect(() => {
    if (!liveMidiInput || liveMidiInput.type !== 'noteOn') return;

    const { note, timestamp } = liveMidiInput;
    const bestMatchIndex = findNoteIndex(note, timestamp);

    if (bestMatchIndex !== -1) {
      // Hit!
      processedNotesRef.current.add(bestMatchIndex);
      
      const targetNote = currentSong[bestMatchIndex];
      const diff = Math.abs(targetNote.startTime - timestamp);
      
      let message = '';
      if (diff <= WINDOW_PERFECT) {
        message = 'Perfect!';
      } else {
        message = 'Good';
      }

      setFeedbackMessage(message);
      const timer = setTimeout(() => setFeedbackMessage(null), 1000);

      updateScore({
        hits: scoreRef.current.hits + 1,
        streak: scoreRef.current.streak + 1
      });

      return () => clearTimeout(timer);
    }
  }, [liveMidiInput, findNoteIndex, currentSong, updateScore]);

  // Handle Time Updates (Missed Notes & Wait Mode) - THROTTLED
  useEffect(() => {
    const now = Date.now();
    
    // Throttle: only check every 100ms instead of every frame
    if (now - lastMissCheckRef.current < TIME_UPDATE_THROTTLE * 1000) {
      return;
    }
    lastMissCheckRef.current = now;

    let shouldPauseNow = false;
    let missedCount = 0;
    let newStreak = scoreRef.current.streak;

    // Only check notes around currentTime (optimization)
    const timeWindow = 2.0; // Check 2 seconds ahead/behind
    const sorted = sortedNotesRef.current;
    
    // Binary search for notes in time window
    let startIdx = 0;
    let endIdx = sorted.length;
    
    for (let i = 0; i < sorted.length; i++) {
      const { note, index } = sorted[i];
      
      // Skip if already processed
      if (processedNotesRef.current.has(index)) continue;
      
      // Skip if too far in future
      if (note.startTime > currentTime + timeWindow) break;
      
      // Skip if too far in past (already missed)
      if (note.startTime < currentTime - timeWindow) continue;

      // Check for missed notes
      if (currentTime > note.startTime + WINDOW_GOOD) {
        processedNotesRef.current.add(index);
        missedCount++;
        newStreak = 0; // Reset streak on miss
      }

      // Wait Mode logic
      if (waitModeEnabled && !processedNotesRef.current.has(index)) {
        if (currentTime >= note.startTime) {
          shouldPauseNow = true;
        }
      }
    }

    // Batch update score only if there were misses
    if (missedCount > 0) {
      updateScore({
        misses: scoreRef.current.misses + missedCount,
        streak: newStreak
      });
      
      if (missedCount === 1) {
        setFeedbackMessage('Miss');
        setTimeout(() => setFeedbackMessage(null), 500);
      }
    }

    setShouldPause(shouldPauseNow);

  }, [currentTime, waitModeEnabled, updateScore]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (scoreUpdateTimerRef.current) {
        clearTimeout(scoreUpdateTimerRef.current);
      }
    };
  }, []);

  return { score, feedbackMessage, shouldPause };
};
