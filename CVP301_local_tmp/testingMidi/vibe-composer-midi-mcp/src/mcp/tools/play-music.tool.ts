import { z } from "zod";
import { Drums, Instruments } from "../../midi/instruments";
import { Midi } from "../../midi/midi";

const inputSchema = {
  bpm: z.number().describe("The BPM of the song"),
  midiOuputName: z
    .string()
    .optional()
    .describe("The MIDI output name to use. Don't add unless requested."),
  tracks: z
    .array(
      z.object({
        instrumentName: z
          .enum([
            "drums",
            ...(Object.keys(Instruments) as [string, ...string[]]),
          ])
          .describe(
            `The instrument of the track. Available instruments: ${Object.keys(
              Instruments
            ).join(
              ", "
            )}. If you want to make it a drum track, set the instrumentName to 'drums'.`
          ),
        channel: z
          .number()
          .optional()
          .describe(
            "The MIDI channel of the track. Don't add unless requested."
          ),
        notes: z
          .array(
            z.object({
              note: z
                .array(z.string())
                .nullable()
                .optional()
                .describe(
                  "The notes to play. Use array for chords. Or put one element for single note. Use an empty array for rest/silence"
                ),
              drums: z
                .array(z.string())
                .nullable()
                .optional()
                .describe(
                  "The drums to play. Use array for multiple drums. Use an empty array for rest/silence. Available drums: " +
                    Object.keys(Drums).join(", ")
                ),
              noteDuration: z
                .string()
                .describe(
                  "The note duration, e.g.: 1/32, 1/16, 1/8, 1/4, 1/2, 1"
                ),
            })
          )
          .describe(
            `"Array of notes or drums to play with timing. 
            
            - If you want to play a drum track, use the drums property. 
            - If you want to play a non-drum instrument, use the note property.
            
            Example:
            
            [{note: ['C2', 'E2'], noteDuration: '1/8'}, {note: [], noteDuration: '1/8'}, {note: ['G2'], noteDuration: '1/8'}, {note: null, noteDuration: '1/8'}]. 
            
            Or 
            
            [{drums: ['bass_drum_1', 'closed_hi_hat'], noteDuration: '1/8'}, {drums: ['closed_hi_hat'], noteDuration: '1/8'}, {drums: ['closed_hi_hat', 'acoustic_snare'], noteDuration: '1/8'}, {drums: ['closed_hi_hat'], noteDuration: '1/8'}]. 
            
            An array could be a bar or several bars.
            --------------------------------------------------------------------------------
              
            IMPORTANT FOR FOR DRUM TRACKS:
           
            - notes are played one after another. 
            - we wait until the whole duration of a note before we play another one. 
            - So don't do this: "notes" :[{"drums: ["bass_drum_1", "closed_hi_hat"], noteDuration: '1/4'},{"drums: [ "closed_hi_hat"], noteDuration: '1/4'} {drums: ['closed_hi_hat', 'acoustic_snare'], noteDuration: '1/4'}...].`
          ),
      })
    )
    .describe(
      `Array of tracks to play.
      
      - If you want to make it a drum track, set the instrumentName to 'drums'. and Use the 'drums' proprerty in notation. 
      - Otherwise, use the 'note' property in 'notes'.
      - Unless asked otherwise, add 10 bars assuming 4/4 time signature.
      - Unless asked otherwise, make sure that each has the same number of bars.
      - Sometimes you make some tracks longer or shorter than others. Avoid that.
      `
    ),
};

const inputSchemaObject = z.object(inputSchema);

type PlayMusicMcpToolInput = z.infer<typeof inputSchemaObject>;

const PlayMusicMcpTool = {
  name: "play",
  title: "Play a music score",
  description: "Plays a music score",
  inputSchema,
  handler: async (
    input: PlayMusicMcpToolInput
  ): Promise<{ content: { type: "text"; text: string }[] }> => {
    const midi = new Midi();

    await midi.init();

    await midi.playScore({
      bpm: input.bpm,
      midiOuputName: input.midiOuputName,
      tracks: input.tracks as any,
    });

    return {
      content: [
        {
          type: "text",
          text: "Playing music score",
        },
      ],
    };
  },
};

export { PlayMusicMcpTool };
