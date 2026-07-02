import { Midi } from "@tonejs/midi";

export interface TargetNote {
  midi: number; // MIDI note number (e.g., 60 = Middle C)
  time: number; // start time in seconds
  duration: number; // duration in seconds
}

/**
 * Parse a MIDI File object into a list of TargetNotes.
 * Filters out non-note events and returns notes sorted by start time.
 */
export async function parseMidiFile(file: File): Promise<TargetNote[]> {
  const arrayBuffer = await file.arrayBuffer();

  let midi: Midi;
  try {
    midi = new Midi(arrayBuffer);
  } catch (err) {
    throw new Error(`Failed to parse MIDI: ${String(err)}`);
  }

  // tonejs Midi normalizes note timings to seconds by default
  const notes: TargetNote[] = midi.tracks.flatMap((track) =>
    track.notes.map((note) => ({
      midi: note.midi,
      time: note.time,
      duration: note.duration,
    }))
  );

  // Filter out any non-note events (already excluded) and sort by start time
  notes.sort((a, b) => a.time - b.time);

  return notes;
}
