// Web Worker for MIDI parsing to avoid blocking main thread

import { Midi } from '@tonejs/midi';

self.onmessage = async (e: MessageEvent<{ buffer: ArrayBuffer }>) => {
  try {
    const { buffer } = e.data;
    
    // Parse MIDI file in worker thread
    const midi = new Midi(buffer);
    
    // Extract events
    const events: Array<{
      pitch: number;
      startTime: number;
      duration: number;
    }> = [];
    
    const meta: Record<string, any> = {
      duration: midi.duration,
      tracks: midi.tracks.length,
    };
    
    // Process all tracks
    midi.tracks.forEach((track, trackIndex) => {
      track.notes.forEach((note) => {
        events.push({
          pitch: note.midi,
          startTime: note.time,
          duration: note.duration,
        });
      });
    });
    
    // Sort by time
    events.sort((a, b) => a.startTime - b.startTime);
    
    // Send result back to main thread
    self.postMessage({
      success: true,
      events,
      meta,
    });
  } catch (error) {
    self.postMessage({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

