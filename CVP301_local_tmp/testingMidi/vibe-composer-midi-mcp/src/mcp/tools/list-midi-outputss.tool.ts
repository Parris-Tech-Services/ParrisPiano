import { Midi } from "../../midi/midi";

const ListMidiOutputsMcpTool = {
  name: "list-midi-outputs",
  title: "List MIDI outputs",
  description: "Lists MIDI outputs",
  handler: async (): Promise<{ content: { type: "text"; text: string }[] }> => {
    const midi = new Midi();
    await midi.init();

    const outputs = await midi.listOutputs();

    return {
      content: [{ type: "text", text: JSON.stringify(outputs, null, 2) }],
    };
  },
};

export { ListMidiOutputsMcpTool };
