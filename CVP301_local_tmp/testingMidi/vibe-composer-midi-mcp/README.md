# vibe-composer-midi-mcp

- Vibe composer as an MCP server
- Watch [the video for an overview](https://www.youtube.com/watch?v=8Sbbf874YWQ)
- Talk to an LLM and compose music!
- Multi track - not just a piano, but the whole band
- Also can output to a software or a hardware synthesizer for a better sound!

# Complete example on YouTube

[Complete example](https://www.youtube.com/watch?v=8Sbbf874YWQ)

# Example prompts

- `Play an upbeat melody on the piano`
  - [Audio example of that](https://github.com/mikeborozdin/vibe-composer-midi-mcp/raw/refs/heads/main/examples/upbeat-piano.wav)
- `Spicy it up with fast passages with 16th notes`
  - [Audio example of that](https://github.com/mikeborozdin/vibe-composer-midi-mcp/raw/refs/heads/main/examples/upbeat-piano-with-fast-passages.wav)
- `Add a few bars on the saxophone while piano is playing chords`
  - [Audio example of that](https://github.com/mikeborozdin/vibe-composer-midi-mcp/raw/refs/heads/main/examples/with-sax.wav)
- `Add drums for the whole duration of the song`
  - [Audio example of that](https://github.com/mikeborozdin/vibe-composer-midi-mcp/raw/refs/heads/main/examples/full-band.wav)

# Playing it on a software or hardware synthesizer

- Ask an LLM to list MIDI outputs - `Which MIDI outputs are available?`
  - It may tell you that you have `Logic Pro`
- Then ask to play it on logic pro and assign channels: e.g.:

```
Play in on Logic Pro and route the tracks to the following channels:

- Piano - channel 0
- Sax - channel 1
- Drums - channel 2

```

# Installation

- Using an example of Claude Desktop as an MCP client:

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
"vibe-composer-midi-mcp": {
  "command": "npx",
  "args": ["vibe-composer-midi-mcp@latest"]
}
```
