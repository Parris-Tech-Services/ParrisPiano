(function () {
  const RECORDING_KEYS = ["parris-piano-last-recording", "lastRecording"];
  const TONE_MIDI_URL = "https://cdn.jsdelivr.net/npm/@tonejs/midi@2.0.27/build/Midi.js";

  function getElements() {
    return {
      status: document.getElementById("sheet-status"),
      preview: document.getElementById("sheet-preview"),
      panel: document.getElementById("sheet-panel"),
    };
  }

  function setStatus(text) {
    const { status } = getElements();
    if (status) status.textContent = text;
  }

  function clearPreview(message) {
    const { preview } = getElements();
    if (!preview) return;
    preview.innerHTML = `<div class="activity-empty">${message}</div>`;
  }

  function readStoredRecording() {
    for (const key of RECORDING_KEYS) {
      try {
        const raw = localStorage.getItem(key);
        if (raw) return JSON.parse(raw);
      } catch (error) {
        console.warn(`Failed to read recording from ${key}`, error);
      }
    }
    return null;
  }

  function writeLegacyFallback(recording) {
    try {
      localStorage.setItem(RECORDING_KEYS[0], JSON.stringify(recording));
    } catch (error) {
      console.warn("Failed to persist latest recording for sheet preview", error);
    }
  }

  function ensureToneMidi() {
    return new Promise((resolve, reject) => {
      if (window.Midi) {
        resolve(window.Midi);
        return;
      }

      const existing = document.querySelector('script[data-tone-midi="1"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(window.Midi), { once: true });
        existing.addEventListener("error", () => reject(new Error("Failed to load ToneJS MIDI")), { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = TONE_MIDI_URL;
      script.dataset.toneMidi = "1";
      script.onload = () => resolve(window.Midi);
      script.onerror = () => reject(new Error("Failed to load ToneJS MIDI"));
      document.head.appendChild(script);
    });
  }

  /** Map MIDI note 0–127 to VexFlow key string (concert pitch; middle C = MIDI 60 = c/4). */
  function noteToKey(midiNote) {
    const note = Math.max(0, Math.min(127, Math.round(Number(midiNote))));
    const names = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"];
    const octave = Math.floor(note / 12) - 1;
    return `${names[note % 12]}/${octave}`;
  }

  function extractClusters(recording) {
    if (!recording || !Array.isArray(recording.events)) return [];

    const noteOns = recording.events
      .filter((event) => Array.isArray(event.data) && event.data.length >= 3 && (event.data[0] & 0xf0) === 0x90 && event.data[2] > 0)
      .map((event) => ({ time: Number(event.time || 0), note: event.data[1] }))
      .sort((a, b) => a.time - b.time);

    const clusters = [];
    noteOns.forEach((event) => {
      const current = clusters[clusters.length - 1];
      if (!current || event.time - current.time > 0.18) {
        clusters.push({ time: event.time, notes: [event.note] });
      } else if (!current.notes.includes(event.note)) {
        current.notes.push(event.note);
      }
    });

    return clusters.slice(0, 12);
  }

  function chooseClef(clusters) {
    const notes = clusters.flatMap((cluster) => cluster.notes);
    if (!notes.length) return "treble";
    const average = notes.reduce((sum, note) => sum + note, 0) / notes.length;
    return average < 60 ? "bass" : "treble";
  }

  function buildMeasures(clusters, clef, VF) {
    const notes = clusters.map((cluster) => new VF.StaveNote({
      clef,
      keys: cluster.notes.sort((a, b) => a - b).map(noteToKey),
      duration: "q",
    }));

    const measures = [];
    for (let index = 0; index < notes.length; index += 4) {
      const measure = notes.slice(index, index + 4);
      while (measure.length < 4) {
        measure.push(new VF.StaveNote({ clef, keys: ["b/4"], duration: "qr" }));
      }
      measures.push(measure);
    }
    return measures;
  }

  function renderRecording(recording) {
    const { preview } = getElements();
    if (!preview) return;
    if (!window.Vex || !window.Vex.Flow) {
      setStatus("VexFlow was not available, so notation preview could not be drawn.");
      clearPreview("Notation preview unavailable.");
      return;
    }

    const clusters = extractClusters(recording);
    if (!clusters.length) {
      setStatus("Record a phrase or import a MIDI file to render notation.");
      clearPreview("No playable note data found in the latest recording.");
      return;
    }

    const VF = window.Vex.Flow;
    const clef = chooseClef(clusters);
    const measures = buildMeasures(clusters, clef, VF);
    const width = Math.max(420, preview.clientWidth - 24 || 420);
    const height = Math.max(160, measures.length * 110);

    preview.innerHTML = "";
    preview.style.background = "#ffffff";
    preview.style.padding = "12px";
    preview.style.borderRadius = "12px";
    preview.style.overflowX = "auto";

    const renderer = new VF.Renderer(preview, VF.Renderer.Backends.SVG);
    renderer.resize(width, height);
    const context = renderer.getContext();

    measures.forEach((measureNotes, index) => {
      const y = 12 + index * 100;
      const stave = new VF.Stave(10, y, width - 20);
      if (index === 0) stave.addClef(clef).addTimeSignature("4/4");
      stave.setContext(context).draw();

      const voice = new VF.Voice({ num_beats: 4, beat_value: 4 });
      voice.addTickables(measureNotes);
      new VF.Formatter().joinVoices([voice]).format([voice], width - 90);
      voice.draw(context, stave);
    });

    setStatus(`Notation preview ready from ${recording.meta?.source || "latest input"} at ${recording.meta?.bpm || 100} BPM.`);
  }

  async function recordingFromMidiFile(file) {
    const Midi = await ensureToneMidi();
    const buffer = await file.arrayBuffer();
    const midi = new Midi(buffer);
    const recording = {
      meta: {
        source: file.name,
        bpm: midi.header?.tempos?.[0]?.bpm ? Math.round(midi.header.tempos[0].bpm) : 120,
      },
      events: [],
    };

    midi.tracks.forEach((track) => {
      track.notes.forEach((note) => {
        recording.events.push({
          time: Number(note.time.toFixed(4)),
          data: [144, note.midi, Math.max(1, Math.round((note.velocity || 1) * 127))],
        });
        recording.events.push({
          time: Number((note.time + note.duration).toFixed(4)),
          data: [128, note.midi, 0],
        });
      });
    });

    recording.events.sort((a, b) => a.time - b.time);
    return recording;
  }

  function installControls() {
    const { panel, preview } = getElements();
    if (!panel || !preview || panel.querySelector("#sheet-tools")) return;

    const tools = document.createElement("div");
    tools.id = "sheet-tools";
    tools.className = "control-row";
    tools.style.marginBottom = "12px";
    tools.innerHTML = `
      <button id="sheet-render-last" class="btn btn-secondary" type="button">Render Latest Recording</button>
      <label class="btn btn-secondary" for="sheet-upload-json">Import Recording JSON</label>
      <input id="sheet-upload-json" type="file" accept="application/json" style="display:none">
      <label class="btn btn-secondary" for="sheet-upload-midi">Import MIDI File</label>
      <input id="sheet-upload-midi" type="file" accept=".mid,.midi,audio/midi" style="display:none">
    `;
    preview.before(tools);

    panel.querySelector("#sheet-render-last").addEventListener("click", () => {
      const recording = readStoredRecording();
      if (!recording) {
        setStatus("No saved recording found yet. Record a take first or import a file.");
        clearPreview("No saved recording available yet.");
        return;
      }
      renderRecording(recording);
    });

    panel.querySelector("#sheet-upload-json").addEventListener("change", (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const recording = JSON.parse(reader.result);
          writeLegacyFallback(recording);
          renderRecording(recording);
        } catch (error) {
          setStatus(`Could not read JSON recording: ${error.message || error}`);
          clearPreview("The selected JSON file was not a valid recording export.");
        }
      };
      reader.readAsText(file);
    });

    panel.querySelector("#sheet-upload-midi").addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      setStatus(`Importing ${file.name}...`);
      try {
        const recording = await recordingFromMidiFile(file);
        writeLegacyFallback(recording);
        renderRecording(recording);
      } catch (error) {
        setStatus(`Could not import MIDI: ${error.message || error}`);
        clearPreview("The selected MIDI file could not be parsed.");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    installControls();
    const recording = readStoredRecording();
    if (recording) renderRecording(recording);
    else clearPreview("Record a short phrase or import a MIDI file to generate notation here.");
  });

  window.addEventListener("parris-recording-updated", (event) => {
    if (event.detail) renderRecording(event.detail);
    else {
      setStatus("Record a phrase or import a file to render notation.");
      clearPreview("Record a short phrase or import a MIDI file to generate notation here.");
    }
  });
})();
