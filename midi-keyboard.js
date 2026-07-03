(function () {
  const FULL_START = 21;
  const FULL_END = 108;
  const PERFECT_MS = 50;
  const GOOD_MS = 110;
  const BARS_TO_SHOW = 8;
  const STORAGE_KEY = 'parris-piano-state';
  const PLAN_KEY = 'parris-piano-last-plan';
  const RECORDING_KEY = 'parris-piano-last-recording';

  const appState = {
    visibleStart: FULL_START,
    visibleOctaves: 'full',
    fitWidth: true,
    docked: true,
    hideKeyboard: false,
    selectedInputId: '',
    metronomeBpm: 100,
  };

  const session = {
    perBarStats: {},
    noteCount: 0,
    perfectCount: 0,
    goodCount: 0,
    poorCount: 0,
    streak: 0,
    bestStreak: 0,
    lastResult: 'Waiting',
    lastDeltaMs: null,
    currentInputName: 'Waiting for MIDI input',
    activeNotes: new Set(),
    activity: [],
    recording: false,
    recordedEvents: [],
    recordStart: 0,
    lastPlan: null,
    lastRecording: null,
    loadedSong: null,
    loopStart: null,
    loopEnd: null,
    loopEnabled: false,
  };

  let midiAccess = null;
  let currentInput = null;
  let audioCtx = null;
  let metronomeTimer = null;
  let metronomeRunning = false;
  let metronomeBeat = 0;
  let beat0 = null;
  let beatInterval = 60 / appState.metronomeBpm;
  let recordTimer = null;

  function noteName(note) {
    const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    return names[note % 12] + (Math.floor(note / 12) - 1);
  }

  function isBlack(note) {
    return [1, 3, 6, 8, 10].includes(note % 12);
  }

  function storageGet(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : fallback;
    } catch (error) {
      console.warn('Failed to read local storage', error);
      return fallback;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to write local storage', error);
    }
  }

  function storageRemove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to clear local storage', error);
    }
  }

  function nowSeconds() {
    return audioCtx ? audioCtx.currentTime : performance.now() / 1000;
  }

  function loadSettings() {
    const saved = storageGet(STORAGE_KEY, null);
    if (!saved) return;
    if (typeof saved.visibleStart === 'number') appState.visibleStart = saved.visibleStart;
    if (saved.visibleOctaves === 'full' || Number.isInteger(saved.visibleOctaves)) appState.visibleOctaves = saved.visibleOctaves;
    if (typeof saved.fitWidth === 'boolean') appState.fitWidth = saved.fitWidth;
    if (typeof saved.docked === 'boolean') appState.docked = saved.docked;
    if (typeof saved.hideKeyboard === 'boolean') appState.hideKeyboard = saved.hideKeyboard;
    if (typeof saved.selectedInputId === 'string') appState.selectedInputId = saved.selectedInputId;
    if (typeof saved.metronomeBpm === 'number') appState.metronomeBpm = saved.metronomeBpm;
  }

  function saveSettings() {
    storageSet(STORAGE_KEY, {
      visibleStart: appState.visibleStart,
      visibleOctaves: appState.visibleOctaves,
      fitWidth: appState.fitWidth,
      docked: appState.docked,
      hideKeyboard: appState.hideKeyboard,
      selectedInputId: appState.selectedInputId,
      metronomeBpm: appState.metronomeBpm,
    });
  }

  function ensureAudio() {
    if (!audioCtx) {
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (error) {
        console.warn('AudioContext error', error);
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch((error) => console.warn('AudioContext resume failed', error));
    }
  }

  function setStatus(kind, text) {
    const status = document.getElementById('midi-status');
    const state = document.getElementById('midi-state');
    if (!status || !state) return;
    status.className = `status-badge status-${kind}`;
    state.textContent = text;
  }

  function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return '--';
    const total = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(total / 60);
    const remainder = total % 60;
    return `${minutes}:${String(remainder).padStart(2, '0')}`;
  }

  function updateLoopDisplay() {
    const info = document.getElementById('loop-info');
    const toggle = document.getElementById('toggle-loop');
    if (!info || !toggle) return;
    let text = `A: ${formatTime(session.loopStart)} B: ${formatTime(session.loopEnd)}`;
    if (session.loopStart !== null && session.loopEnd !== null && session.loopEnd > session.loopStart) {
      text += ` (${formatTime(session.loopEnd - session.loopStart)} span)`;
    }
    info.textContent = text;
    toggle.textContent = `Loop: ${session.loopEnabled ? 'On' : 'Off'}`;
  }

  function updateButtonStates() {
    const downloadRecording = document.getElementById('download-recording');
    const downloadPlan = document.getElementById('download-plan');
    const recordButton = document.getElementById('record-toggle');
    if (downloadRecording) {
      const hasRecording = Boolean(
        (session.lastRecording && Array.isArray(session.lastRecording.events) && session.lastRecording.events.length) ||
          session.recordedEvents.length
      );
      downloadRecording.disabled = !hasRecording;
    }
    if (downloadPlan) downloadPlan.disabled = !(session.lastPlan && Array.isArray(session.lastPlan.loops) && session.lastPlan.loops.length);
    const clearSong = document.getElementById('clear-midi-song');
    if (clearSong) clearSong.disabled = !session.loadedSong;
    if (recordButton) {
      recordButton.textContent = session.recording ? 'Stop Recording' : 'Start Recording';
      recordButton.disabled = !currentInput && !session.recording;
    }
  }

  function displayLoadedSong(song) {
    const songInfo = document.getElementById('song-info');
    if (!songInfo) return;
    if (!song) {
      songInfo.innerHTML = '<div class="activity-empty">No MIDI song loaded.</div>';
      return;
    }

    const trackNames = song.trackNames ? `<div>${song.trackNames}</div>` : '';
    songInfo.innerHTML = `
      <div class="song-summary">
        <strong>${song.title}</strong>
        <div>${song.trackCount} track${song.trackCount === 1 ? '' : 's'}, ${song.noteCount} note${song.noteCount === 1 ? '' : 's'}</div>
        ${trackNames}
        <div>${formatTime(song.durationSec)} · ${song.tempo} BPM</div>
      </div>
    `;
  }

  function clearLoadedSong() {
    session.loadedSong = null;
    displayLoadedSong(null);
    updateButtonStates();
    addActivity('MIDI song cleared', 'Ready for a new song file', 'neutral');
  }

  async function loadMidiFile(file) {
    if (!window.Midi) {
      window.alert('MIDI parser library is not available. Please ensure the app can access the network.');
      return;
    }

    try {
      const buffer = await file.arrayBuffer();
      const midi = new window.Midi(buffer);
      const song = {
        title: midi.name || file.name,
        trackCount: midi.tracks.length,
        noteCount: midi.tracks.reduce((sum, track) => sum + (track.notes?.length || 0), 0),
        durationSec: midi.duration || 0,
        tempo: Math.round((midi.header.tempos?.[0]?.bpm ?? appState.metronomeBpm) || appState.metronomeBpm),
        trackNames: midi.tracks.map((track) => track.name).filter(Boolean).join(', '),
      };
      session.loadedSong = song;
      displayLoadedSong(song);
      updateButtonStates();
      addActivity('MIDI song loaded', song.title, 'good');
    } catch (error) {
      console.error('Failed to load MIDI file', error);
      window.alert('Unable to parse the selected MIDI file.');
    }
  }

  function setMidiControlAvailability(enabled) {
    const select = document.getElementById('midi-inputs');
    const refresh = document.getElementById('refresh-midi');
    if (select) select.disabled = !enabled;
    if (refresh) refresh.disabled = !enabled;
  }

  function updateMidiAvailability() {
    const enabled = Boolean(midiAccess);
    setMidiControlAvailability(enabled);
    if (!enabled) {
      const select = document.getElementById('midi-inputs');
      if (select) select.innerHTML = '<option value="">No MIDI support</option>';
    }
    updateButtonStates();
  }

  function getVisibleNotes() {
    if (appState.visibleOctaves === 'full') return { start: FULL_START, end: FULL_END };
    const start = Math.max(FULL_START, Math.min(appState.visibleStart, FULL_END - appState.visibleOctaves * 12 + 1));
    const end = Math.min(FULL_END, start + appState.visibleOctaves * 12 - 1);
    return { start, end };
  }

  function fitKeysToWidth(container) {
    const keyboard = container.querySelector('#keyboard');
    if (!keyboard) return;
    const whiteKeys = Array.from(keyboard.querySelectorAll('.key.white'));
    if (!whiteKeys.length) return;
    const available = Math.max(220, container.clientWidth - 20);
    const whiteWidth = Math.max(36, Math.floor(available / whiteKeys.length));
    const blackWidth = Math.round(whiteWidth * 0.62);
    whiteKeys.forEach((key) => {
      key.style.width = `${whiteWidth}px`;
    });
    keyboard.querySelectorAll('.key.black').forEach((key) => {
      key.style.width = `${blackWidth}px`;
      key.style.marginLeft = `${-(blackWidth / 2)}px`;
    });
  }

  function createKeyboard(container) {
    container.innerHTML = '';
    const { start, end } = getVisibleNotes();
    const wrapper = document.createElement('div');
    wrapper.id = 'keyboard';
    const row = document.createElement('div');
    row.className = 'keys';
    for (let note = start; note <= end; note += 1) {
      const key = document.createElement('div');
      key.className = `key ${isBlack(note) ? 'black' : 'white'}`;
      key.dataset.note = String(note);
      key.title = noteName(note);
      key.innerHTML = `<div style="pointer-events:none">${noteName(note)}</div>`;
      row.appendChild(key);
    }
    wrapper.appendChild(row);
    container.appendChild(wrapper);
    if (appState.fitWidth) fitKeysToWidth(container);
    session.activeNotes.forEach((note) => highlight(note));
  }

  function refreshKeyboard() {
    const container = document.getElementById('keyboard-container');
    if (container) createKeyboard(container);
  }

  function applyBodyClasses() {
    document.body.classList.toggle('keyboard-hidden', appState.hideKeyboard);
    document.body.classList.toggle('keyboard-docked', appState.docked && !appState.hideKeyboard);
    document.body.style.paddingBottom = appState.docked && !appState.hideKeyboard ? '300px' : '';
  }

  function updateControlLabels() {
    const fitButton = document.getElementById('fit-width');
    const dockButton = document.getElementById('dock-toggle');
    const hideToggle = document.getElementById('hide-keyboard-toggle');
    const tempo = document.getElementById('tempo');
    const bpm = document.getElementById('bpm-value');
    const range = document.getElementById('key-range');
    if (fitButton) fitButton.textContent = appState.fitWidth ? 'Fixed Size' : 'Fit Width';
    if (dockButton) dockButton.textContent = appState.docked ? 'Close Keyboard' : 'Expand Keyboard';
    if (hideToggle) hideToggle.checked = appState.hideKeyboard;
    if (tempo) tempo.value = String(appState.metronomeBpm);
    if (bpm) bpm.textContent = `${appState.metronomeBpm} BPM`;
    if (range) range.value = String(appState.visibleOctaves);
  }

  function highlight(note) {
    const key = document.querySelector(`#keyboard [data-note='${note}']`);
    if (key) key.classList.add('active');
  }

  function release(note) {
    const key = document.querySelector(`#keyboard [data-note='${note}']`);
    if (key) key.classList.remove('active');
  }

  function updateHeldNotes() {
    const held = document.getElementById('active-notes');
    if (!held) return;
    if (!session.activeNotes.size) {
      held.textContent = 'No notes held.';
      return;
    }
    const notes = Array.from(session.activeNotes).sort((a, b) => a - b).map(noteName);
    held.textContent = `Held notes: ${notes.join(', ')}`;
  }

  function renderActivity() {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;
    feed.innerHTML = '';
    if (!session.activity.length) {
      const empty = document.createElement('div');
      empty.className = 'activity-empty';
      empty.textContent = 'Play a note to start the activity feed.';
      feed.appendChild(empty);
      return;
    }
    session.activity.forEach((item) => {
      const row = document.createElement('div');
      row.className = `activity-item ${item.kind}`;
      const left = document.createElement('strong');
      const right = document.createElement('span');
      left.textContent = item.label;
      right.textContent = item.detail;
      row.appendChild(left);
      row.appendChild(right);
      feed.appendChild(row);
    });
  }

  function addActivity(label, detail, kind = 'neutral') {
    session.activity.unshift({ label, detail, kind });
    session.activity = session.activity.slice(0, 10);
    renderActivity();
  }
  function updateSessionSummary() {
    const total = session.noteCount;
    const weightedAccuracy = total ? Math.round(((session.perfectCount + session.goodCount * 0.7) / total) * 100) : 0;
    const noteCount = document.getElementById('session-note-count');
    const inputName = document.getElementById('session-input-name');
    const accuracy = document.getElementById('session-accuracy');
    const accuracyDetail = document.getElementById('session-accuracy-detail');
    const streak = document.getElementById('session-streak');
    const bestStreak = document.getElementById('session-best-streak');
    const lastResult = document.getElementById('session-last-result');
    const lastDelta = document.getElementById('session-last-delta');

    if (noteCount) noteCount.textContent = String(total);
    if (inputName) inputName.textContent = session.currentInputName;
    if (accuracy) accuracy.textContent = `${weightedAccuracy}%`;
    if (accuracyDetail) {
      accuracyDetail.textContent = total
        ? `Perfect ${session.perfectCount} | Good ${session.goodCount} | Poor ${session.poorCount}`
        : 'No scored notes yet';
    }
    if (streak) streak.textContent = String(session.streak);
    if (bestStreak) bestStreak.textContent = `Best streak: ${session.bestStreak}`;
    if (lastResult) lastResult.textContent = session.lastResult;
    if (lastDelta) lastDelta.textContent = session.lastDeltaMs === null
      ? 'Play with the metronome to score timing'
      : `Offset ${session.lastDeltaMs > 0 ? '+' : ''}${session.lastDeltaMs} ms`;
  }

  function updateScoreUI() {
    const bars = document.getElementById('score-bars');
    const summary = document.getElementById('score-summary');
    if (!bars || !summary) return;

    const indices = Object.keys(session.perBarStats).map((value) => parseInt(value, 10)).sort((a, b) => a - b);
    const lastBars = indices.slice(-BARS_TO_SHOW);
    bars.innerHTML = '';

    lastBars.forEach((barIndex) => {
      const stats = session.perBarStats[barIndex];
      const wrapper = document.createElement('div');
      wrapper.className = 'score-bar';
      wrapper.title = `Bar ${barIndex + 1}: ${stats.total} notes`;

      const fill = document.createElement('div');
      fill.className = 'score-bar-fill';

      const poor = document.createElement('div');
      poor.style.height = `${stats.total ? Math.round((stats.poor / stats.total) * 100) : 0}%`;
      poor.style.background = 'linear-gradient(180deg, #ff8c73, #ff6048)';

      const good = document.createElement('div');
      good.style.height = `${stats.total ? Math.round((stats.good / stats.total) * 100) : 0}%`;
      good.style.background = 'linear-gradient(180deg, #ffd978, #ffb74d)';

      const perfect = document.createElement('div');
      perfect.style.height = `${stats.total ? Math.round((stats.perfect / stats.total) * 100) : 0}%`;
      perfect.style.background = 'linear-gradient(180deg, #8de2ff, #67c9f0)';

      fill.appendChild(perfect);
      fill.appendChild(good);
      fill.appendChild(poor);

      const label = document.createElement('div');
      label.className = 'score-bar-label';
      label.textContent = `B${barIndex + 1}`;

      wrapper.appendChild(fill);
      wrapper.appendChild(label);
      bars.appendChild(wrapper);
    });

    document.getElementById('score-bars-count').textContent = String(BARS_TO_SHOW);
    document.getElementById('score-total').textContent = String(session.noteCount);
    document.getElementById('score-perfect').textContent = String(session.perfectCount);
    document.getElementById('score-good').textContent = String(session.goodCount);
    document.getElementById('score-poor').textContent = String(session.poorCount);

    if (!session.noteCount) {
      summary.textContent = 'No notes scored yet.';
      return;
    }

    const weakestBar = Object.entries(session.perBarStats)
      .map(([barIndex, stats]) => ({
        barIndex: parseInt(barIndex, 10),
        poorRatio: stats.total ? stats.poor / stats.total : 0,
        total: stats.total,
      }))
      .sort((a, b) => b.poorRatio - a.poorRatio || b.total - a.total)[0];

    summary.textContent = weakestBar && weakestBar.total
      ? `Best streak ${session.bestStreak}. Focus next on bar ${weakestBar.barIndex + 1}, where ${Math.round(weakestBar.poorRatio * 100)}% of recent hits were poor.`
      : `Best streak ${session.bestStreak}. Keep building consistent hits with the metronome.`;
  }

  function scoreNoteOn(note, timestamp) {
    if (beat0 === null) {
      beat0 = timestamp;
      beatInterval = 60 / appState.metronomeBpm;
    }

    const relativeTime = timestamp - beat0;
    const beatIndex = Math.max(0, Math.round(relativeTime / beatInterval));
    const expectedTime = beat0 + beatIndex * beatInterval;
    const deltaMs = Math.round((timestamp - expectedTime) * 1000);
    const absoluteDelta = Math.abs(deltaMs);

    let result = 'poor';
    if (absoluteDelta <= PERFECT_MS) result = 'perfect';
    else if (absoluteDelta <= GOOD_MS) result = 'good';

    const barIndex = Math.floor(beatIndex / 4);
    if (!session.perBarStats[barIndex]) session.perBarStats[barIndex] = { total: 0, perfect: 0, good: 0, poor: 0 };
    session.perBarStats[barIndex].total += 1;
    session.perBarStats[barIndex][result] += 1;

    session.noteCount += 1;
    session.lastResult = result.toUpperCase();
    session.lastDeltaMs = deltaMs;
    if (result === 'perfect') {
      session.perfectCount += 1;
      session.streak += 1;
    } else if (result === 'good') {
      session.goodCount += 1;
      session.streak += 1;
    } else {
      session.poorCount += 1;
      session.streak = 0;
    }
    session.bestStreak = Math.max(session.bestStreak, session.streak);

    updateScoreUI();
    updateSessionSummary();
    return { note, result, deltaMs, barIndex };
  }

  function generatePracticePlan() {
    const items = Object.keys(session.perBarStats).map((key) => {
      const stats = session.perBarStats[key];
      return {
        bar: parseInt(key, 10),
        total: stats.total,
        poorRatio: stats.total ? stats.poor / stats.total : 0,
        goodRatio: stats.total ? stats.good / stats.total : 0,
      };
    });

    if (!items.length) return { generatedAt: new Date().toISOString(), bpm: appState.metronomeBpm, loops: [] };
    items.sort((a, b) => b.poorRatio - a.poorRatio || a.goodRatio - b.goodRatio || b.total - a.total);

    return {
      generatedAt: new Date().toISOString(),
      bpm: appState.metronomeBpm,
      summary: `Work through ${Math.min(4, items.length)} focused loop targets, then return to full tempo.`,
      loops: items.slice(0, Math.min(4, items.length)).map((item, index) => ({
        order: index + 1,
        barStart: Math.max(1, item.bar),
        barEnd: item.bar + 2,
        focusBar: item.bar + 1,
        reason: `Poor timing on ${Math.round(item.poorRatio * 100)}% of recent notes`,
        targetTempo: Math.max(40, Math.round(appState.metronomeBpm * (item.poorRatio > 0.5 ? 0.7 : 0.82))),
        reps: item.poorRatio > 0.5 ? 10 : 6,
      })),
    };
  }

  function displayPlan(plan) {
    const output = document.getElementById('plan-output');
    if (!output) return;
    if (!plan || !Array.isArray(plan.loops) || !plan.loops.length) {
      output.innerHTML = "<div class='activity-empty'>No plan generated yet.</div>";
      return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'plan-summary';
    wrapper.innerHTML = `
      <div class="plan-summary-header">
        <strong>Generated:</strong> ${new Date(plan.generatedAt).toLocaleString()}<br>
        <strong>Base tempo:</strong> ${plan.bpm} BPM
      </div>
      <div class="plan-summary-description">${plan.summary || 'Focused work set.'}</div>
    `;

    const loops = document.createElement('div');
    loops.className = 'plan-loop-list';

    plan.loops.forEach((loop) => {
      const card = document.createElement('div');
      card.className = 'plan-loop';
      card.innerHTML = `
        <div class="plan-loop-header">Loop ${loop.order}</div>
        <div class="plan-loop-row"><strong>Bars</strong><span>${loop.barStart}-${loop.barEnd}</span></div>
        <div class="plan-loop-row"><strong>Focus</strong><span>Bar ${loop.focusBar}</span></div>
        <div class="plan-loop-row"><strong>Tempo</strong><span>${loop.targetTempo} BPM</span></div>
        <div class="plan-loop-row"><strong>Reps</strong><span>${loop.reps}</span></div>
        <div class="plan-loop-note">${loop.reason}</div>
      `;
      loops.appendChild(card);
    });

    output.innerHTML = '';
    output.appendChild(wrapper);
    output.appendChild(loops);
  }

  function downloadPlan(plan) {
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `practice-plan-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function dispatchRecordingUpdate(recording) {
    window.dispatchEvent(new CustomEvent('parris-recording-updated', { detail: recording }));
  }

  function currentRecordingPayload() {
    if (!session.recordedEvents.length) return null;
    return {
      meta: {
        recordedAt: new Date().toISOString(),
        source: currentInput ? currentInput.name || 'Unknown input' : session.currentInputName,
        bpm: appState.metronomeBpm,
      },
      events: session.recordedEvents,
    };
  }

  function updateRecordTimer() {
    const timer = document.getElementById('record-timer');
    if (!timer) return;
    if (!session.recording) {
      timer.textContent = '00:00';
      return;
    }
    const elapsed = Math.floor(nowSeconds() - session.recordStart);
    timer.textContent = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;
  }

  function startRecording() {
    session.recordedEvents = [];
    session.recordStart = nowSeconds();
    session.recording = true;
    updateRecordTimer();
    recordTimer = window.setInterval(updateRecordTimer, 500);
    addActivity('Recording started', `${appState.metronomeBpm} BPM`, 'neutral');
    updateButtonStates();
  }

  function stopRecording() {
    session.recording = false;
    if (recordTimer) {
      clearInterval(recordTimer);
      recordTimer = null;
    }
    updateRecordTimer();
    const payload = currentRecordingPayload();
    if (payload) {
      session.lastRecording = payload;
      storageSet(RECORDING_KEY, payload);
      dispatchRecordingUpdate(payload);
      addActivity('Recording saved', `${payload.events.length} MIDI events`, 'neutral');
    }
    updateButtonStates();
  }

  function downloadRecording() {
    const payload = session.lastRecording || currentRecordingPayload();
    if (!payload) {
      window.alert('No recorded events available yet.');
      return;
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `midi-recording-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function clearSession() {
    if (session.recording) stopRecording();
    session.perBarStats = {};
    session.noteCount = 0;
    session.perfectCount = 0;
    session.goodCount = 0;
    session.poorCount = 0;
    session.streak = 0;
    session.bestStreak = 0;
    session.lastResult = 'Waiting';
    session.lastDeltaMs = null;
    session.activity = [];
    session.activeNotes.clear();
    session.recordedEvents = [];
    session.lastRecording = null;
    session.lastPlan = null;
    session.loopStart = null;
    session.loopEnd = null;
    session.loopEnabled = false;
    beat0 = null;
    storageRemove(PLAN_KEY);
    storageRemove(RECORDING_KEY);
    document.getElementById('plan-output').textContent = 'No plan generated yet.';
    updateLoopDisplay();
    renderActivity();
    updateHeldNotes();
    updateScoreUI();
    updateSessionSummary();
    updateButtonStates();
    dispatchRecordingUpdate(null);
    addActivity('Session reset', 'Scoring, plan, and recording were cleared', 'neutral');
  }
  function playClick(accent) {
    if (!audioCtx) return;
    const time = audioCtx.currentTime;
    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    oscillator.type = 'square';
    oscillator.frequency.value = accent ? 1360 : 1040;
    gain.gain.value = 0.0001;
    oscillator.connect(gain);
    gain.connect(audioCtx.destination);
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(accent ? 0.55 : 0.38, time + 0.001);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.06);
    oscillator.start(time);
    oscillator.stop(time + 0.07);

    const indicator = document.getElementById('beat-indicator');
    if (!indicator) return;
    indicator.classList.add('beat-live');
    indicator.textContent = accent ? 'Beat 1' : `Beat ${metronomeBeat + 1}`;
    setTimeout(() => {
      indicator.classList.remove('beat-live');
      indicator.textContent = 'Beat';
    }, 120);
  }

  function startMetronome() {
    if (metronomeRunning) return;
    ensureAudio();
    beatInterval = 60 / appState.metronomeBpm;
    beat0 = nowSeconds();
    metronomeBeat = 0;
    metronomeRunning = true;
    playClick(true);
    metronomeTimer = window.setInterval(() => {
      metronomeBeat = (metronomeBeat + 1) % 4;
      playClick(metronomeBeat === 0);
    }, beatInterval * 1000);
    document.getElementById('metronome-toggle').textContent = 'Stop Metronome';
    addActivity('Metronome started', `${appState.metronomeBpm} BPM`, 'neutral');
  }

  function stopMetronome() {
    if (metronomeTimer) {
      clearInterval(metronomeTimer);
      metronomeTimer = null;
    }
    metronomeRunning = false;
    const button = document.getElementById('metronome-toggle');
    if (button) button.textContent = 'Start Metronome';
  }

  function setLoopA() {
    session.loopStart = nowSeconds();
    updateLoopDisplay();
    addActivity('Loop A set', `At ${formatTime(session.loopStart)}`, 'neutral');
  }

  function setLoopB() {
    session.loopEnd = nowSeconds();
    updateLoopDisplay();
    addActivity('Loop B set', `At ${formatTime(session.loopEnd)}`, 'neutral');
  }

  function toggleLoop() {
    session.loopEnabled = !session.loopEnabled;
    updateLoopDisplay();
  }

  function listInputs(select) {
    select.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '(Choose input)';
    select.appendChild(placeholder);
    if (!midiAccess) return;
    for (const input of midiAccess.inputs.values()) {
      const option = document.createElement('option');
      option.value = input.id;
      option.textContent = input.name || input.manufacturer || input.id;
      select.appendChild(option);
    }
  }

  function attachInputById(id) {
    if (currentInput) currentInput.onmidimessage = null;
    currentInput = id && midiAccess ? midiAccess.inputs.get(id) : null;
    appState.selectedInputId = currentInput ? currentInput.id : '';
    saveSettings();

    if (currentInput) {
      currentInput.onmidimessage = onMIDIMessage;
      session.currentInputName = `Listening: ${currentInput.name || 'Unknown MIDI input'}`;
      setStatus('connected', session.currentInputName);
      addActivity('MIDI connected', currentInput.name || currentInput.id, 'neutral');
    } else {
      session.currentInputName = midiAccess ? 'Ready - choose an input' : 'Waiting for MIDI input';
      setStatus(midiAccess ? 'ready' : 'disconnected', midiAccess ? 'Ready - choose an input' : 'Disconnected');
    }
    updateSessionSummary();
  }

  function refreshInputs(options = {}) {
    const select = document.getElementById('midi-inputs');
    if (!select || !midiAccess) return;
    const announce = Boolean(options.announce);
    const previousId = appState.selectedInputId || (currentInput ? currentInput.id : '');
    listInputs(select);

    let nextId = '';
    if (previousId && midiAccess.inputs.has(previousId)) {
      nextId = previousId;
    } else {
      for (const input of midiAccess.inputs.values()) {
        const fingerprint = `${input.name || ''} ${input.manufacturer || ''}`.toLowerCase();
        if (/yamaha|cvp|clavinova|digital piano/.test(fingerprint)) {
          nextId = input.id;
          break;
        }
      }
    }

    if (nextId) {
      select.value = nextId;
      attachInputById(nextId);
    } else {
      select.value = '';
      attachInputById('');
      setStatus('disconnected', 'No MIDI input detected');
    }

    if (announce) addActivity('MIDI list refreshed', `${midiAccess.inputs.size} input(s) found`, 'neutral');
  }

  function initMIDI() {
    if (!navigator.requestMIDIAccess) {
      setStatus('unsupported', 'Web MIDI unsupported in this browser');
      updateMidiAvailability();
      return;
    }

    navigator.requestMIDIAccess({ sysex: false }).then((access) => {
      midiAccess = access;
      setStatus('ready', 'Ready - choose an input');
      refreshInputs();
      updateMidiAvailability();
      midiAccess.onstatechange = (event) => {
        refreshInputs();
        updateMidiAvailability();
        const port = event.port;
        addActivity(
          'Device change',
          `${port.name || 'Unknown device'} is ${port.state}`,
          port.state === 'connected' ? 'good' : 'poor'
        );
      };
    }).catch((error) => {
      setStatus('error', 'MIDI access failed');
      updateMidiAvailability();
      console.warn('MIDI init error', error);
    });
  }

  function onMIDIMessage(event) {
    const data = Array.from(event.data || []);
    const status = data[0] & 0xf0;
    const note = data[1];
    const velocity = data[2] || 0;
    const timestamp = nowSeconds();

    if (session.recording) {
      session.recordedEvents.push({ time: Number((timestamp - session.recordStart).toFixed(4)), data });
    }

    if (status === 0x90 && velocity > 0) {
      highlight(note);
      session.activeNotes.add(note);
      const score = scoreNoteOn(note, timestamp);
      addActivity(noteName(note), `${score.result.toUpperCase()} ${score.deltaMs > 0 ? '+' : ''}${score.deltaMs} ms`, score.result);
    } else if (status === 0x80 || (status === 0x90 && velocity === 0)) {
      release(note);
      session.activeNotes.delete(note);
    }

    updateHeldNotes();
  }

  function restoreSavedArtifacts() {
    const lastPlan = storageGet(PLAN_KEY, null);
    const lastRecording = storageGet(RECORDING_KEY, null);
    if (lastPlan && Array.isArray(lastPlan.loops)) {
      session.lastPlan = lastPlan;
      displayPlan(lastPlan);
    }
    if (lastRecording && Array.isArray(lastRecording.events)) {
      session.lastRecording = lastRecording;
      dispatchRecordingUpdate(lastRecording);
      session.currentInputName = `Last take: ${lastRecording.meta?.source || 'Unknown input'}`;
    }
    updateButtonStates();
  }

  function panLeft() {
    if (appState.visibleOctaves === 'full') return;
    appState.visibleStart = Math.max(FULL_START, appState.visibleStart - 12);
    saveSettings();
    refreshKeyboard();
  }

  function panRight() {
    if (appState.visibleOctaves === 'full') return;
    const maxStart = FULL_END - appState.visibleOctaves * 12 + 1;
    appState.visibleStart = Math.min(maxStart, appState.visibleStart + 12);
    saveSettings();
    refreshKeyboard();
  }
  document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    applyBodyClasses();
    updateControlLabels();
    updateLoopDisplay();
    updateScoreUI();
    updateSessionSummary();
    renderActivity();
    updateHeldNotes();

    const keyboardContainer = document.getElementById('keyboard-container');
    if (!keyboardContainer) return;
    createKeyboard(keyboardContainer);

    document.getElementById('pan-left').addEventListener('click', panLeft);
    document.getElementById('pan-right').addEventListener('click', panRight);
    document.getElementById('refresh-midi').addEventListener('click', () => refreshInputs({ announce: true }));
    document.getElementById('download-recording').addEventListener('click', downloadRecording);
    document.getElementById('clear-session').addEventListener('click', clearSession);

    document.getElementById('midi-inputs').addEventListener('change', (event) => {
      attachInputById(event.target.value);
    });

    document.getElementById('key-range').addEventListener('change', (event) => {
      const value = event.target.value;
      appState.visibleOctaves = value === 'full' ? 'full' : parseInt(value, 10);
      if (appState.visibleOctaves !== 'full') {
        const maxStart = FULL_END - appState.visibleOctaves * 12 + 1;
        appState.visibleStart = Math.max(FULL_START, Math.min(appState.visibleStart, maxStart));
      } else {
        appState.visibleStart = FULL_START;
      }
      saveSettings();
      refreshKeyboard();
    });

    document.getElementById('fit-width').addEventListener('click', () => {
      appState.fitWidth = !appState.fitWidth;
      updateControlLabels();
      saveSettings();
      refreshKeyboard();
    });

    document.getElementById('dock-toggle').addEventListener('click', () => {
      appState.docked = !appState.docked;
      if (appState.docked) appState.fitWidth = true;
      applyBodyClasses();
      updateControlLabels();
      saveSettings();
      refreshKeyboard();
    });

    document.getElementById('tempo').addEventListener('input', (event) => {
      appState.metronomeBpm = parseInt(event.target.value, 10);
      beatInterval = 60 / appState.metronomeBpm;
      updateControlLabels();
      saveSettings();
      if (metronomeRunning) {
        stopMetronome();
        startMetronome();
      }
    });

    document.getElementById('metronome-toggle').addEventListener('click', () => {
      if (metronomeRunning) stopMetronome();
      else startMetronome();
    });

    document.getElementById('set-loop-a').addEventListener('click', setLoopA);
    document.getElementById('set-loop-b').addEventListener('click', setLoopB);
    document.getElementById('toggle-loop').addEventListener('click', toggleLoop);

    document.getElementById('record-toggle').addEventListener('click', () => {
      if (session.recording) stopRecording();
      else startRecording();
    });

    document.getElementById('hide-keyboard-toggle').addEventListener('change', (event) => {
      appState.hideKeyboard = event.target.checked;
      if (appState.hideKeyboard) appState.docked = false;
      applyBodyClasses();
      updateControlLabels();
      saveSettings();
    });

    document.getElementById('gen-plan').addEventListener('click', () => {
      session.lastPlan = generatePracticePlan();
      displayPlan(session.lastPlan);
      storageSet(PLAN_KEY, session.lastPlan);
      updateButtonStates();
    });

    document.getElementById('download-plan').addEventListener('click', () => {
      if (!session.lastPlan) {
        window.alert('Generate a practice plan first.');
        return;
      }
      downloadPlan(session.lastPlan);
    });

    const midiFileInput = document.getElementById('midi-file-input');
    const loadMidiButton = document.getElementById('load-midi-button');
    const clearMidiButton = document.getElementById('clear-midi-song');

    if (loadMidiButton && midiFileInput) {
      loadMidiButton.addEventListener('click', () => midiFileInput.click());
      midiFileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (files && files.length) {
          loadMidiFile(files[0]);
        }
        event.target.value = '';
      });
    }

    if (clearMidiButton) {
      clearMidiButton.addEventListener('click', clearLoadedSong);
    }

    window.addEventListener('resize', () => {
      if (appState.fitWidth) fitKeysToWidth(keyboardContainer);
    });

    restoreSavedArtifacts();
    updateButtonStates();
    initMIDI();
  });
})();
