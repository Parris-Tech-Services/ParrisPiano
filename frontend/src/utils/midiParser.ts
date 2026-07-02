// Async MIDI parser with Web Worker support

let worker: Worker | null = null;

export interface ParsedMidi {
  events: Array<{
    pitch: number;
    startTime: number;
    duration: number;
  }>;
  meta: Record<string, any>;
}

export default async function parseMidiFile(buffer: ArrayBuffer): Promise<ParsedMidi> {
  // Try to use Web Worker if available
  if (typeof Worker !== 'undefined') {
    try {
      return await parseMidiInWorker(buffer);
    } catch (error) {
      console.warn('Web Worker parsing failed, falling back to main thread:', error);
      // Fall through to main thread parsing
    }
  }
  
  // Fallback to main thread parsing (synchronous)
  return parseMidiInMainThread(buffer);
}

async function parseMidiInWorker(buffer: ArrayBuffer): Promise<ParsedMidi> {
  return new Promise((resolve, reject) => {
    // Create worker if needed
    if (!worker) {
      // In a real app, you'd need to bundle the worker file
      // For now, we'll use inline worker creation
      const workerCode = `
        importScripts('https://cdn.jsdelivr.net/npm/@tonejs/midi@2.0.27/build/Midi.js');
        self.onmessage = async (e) => {
          try {
            const midi = new Midi(e.data.buffer);
            const events = [];
            const meta = { duration: midi.duration, tracks: midi.tracks.length };
            
            midi.tracks.forEach(track => {
              track.notes.forEach(note => {
                events.push({
                  pitch: note.midi,
                  startTime: note.time,
                  duration: note.duration,
                });
              });
            });
            
            events.sort((a, b) => a.startTime - b.startTime);
            
            self.postMessage({ success: true, events, meta });
          } catch (error) {
            self.postMessage({ success: false, error: error.message });
          }
        };
      `;
      
      const blob = new Blob([workerCode], { type: 'application/javascript' });
      worker = new Worker(URL.createObjectURL(blob));
    }
    
    const timeout = setTimeout(() => {
      reject(new Error('MIDI parsing timeout'));
    }, 30000); // 30 second timeout
    
    worker.onmessage = (e: MessageEvent) => {
      clearTimeout(timeout);
      if (e.data.success) {
        resolve({ events: e.data.events, meta: e.data.meta });
      } else {
        reject(new Error(e.data.error));
      }
    };
    
    worker.onerror = (error) => {
      clearTimeout(timeout);
      reject(error);
    };
    
    worker.postMessage({ buffer });
  });
}

function parseMidiInMainThread(buffer: ArrayBuffer): ParsedMidi {
  // Synchronous parsing fallback
  // This will block the main thread but is better than nothing
  const { Midi } = require('@tonejs/midi');
  const midi = new Midi(buffer);
  
  const events: Array<{
    pitch: number;
    startTime: number;
    duration: number;
  }> = [];
  
  const meta: Record<string, any> = {
    duration: midi.duration,
    tracks: midi.tracks.length,
  };
  
  midi.tracks.forEach((track) => {
    track.notes.forEach((note) => {
      events.push({
        pitch: note.midi,
        startTime: note.time,
        duration: note.duration,
      });
    });
  });
  
  events.sort((a, b) => a.startTime - b.startTime);
  
  return { events, meta };
}

