// Simple MIDI -> on-screen keyboard mapping
(function(){
  const FULL_START = 21; // A0
  const FULL_END = 108;  // C8

  function noteName(n){
    const names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
    return names[n % 12] + (Math.floor(n/12) - 1);
  }

  function isBlack(n){
    return [1,3,6,8,10].includes(n % 12);
  }

  function injectStyles(){
    const css = `
      #keyboard { position: relative; user-select: none; height:220px; margin-top:8px; }
      #keyboard .keys { display:flex; position:relative; height:100%; align-items:flex-start; white-space:nowrap; }
      #keyboard .key { box-sizing:border-box; border:1px solid rgba(0,0,0,0.18); cursor:default; display:inline-flex; }
      #keyboard .key.white { width:48px; height:100%; background:#fff; border-radius:6px; margin-right:2px; align-items:flex-end; justify-content:center; padding-bottom:8px; font-size:11px; color:#111; }
      #keyboard .key.black { width:30px; height:62%; background:#111; color:#fff; position:relative; margin-left:-15px; z-index:3; border-radius:6px; align-items:flex-start; justify-content:center; padding-top:8px; font-size:11px; top:0; }
      #keyboard .key.active.white { background: linear-gradient(180deg,#fffbeb,#ffd6c1); box-shadow:0 8px 24px rgba(255,90,40,0.18) inset; }
      #keyboard .key.active.black { background: linear-gradient(180deg,#ffd6c1,#ff8a5a); box-shadow:0 8px 20px rgba(255,120,92,0.22) inset; }
      #keyboard-container { overflow:auto; -webkit-overflow-scrolling:touch; }
      #beat-indicator { width:12px; height:12px; border-radius:50%; background:rgba(255,255,255,0.06); border:1px solid rgba(0,0,0,0.25); }
      #beat-indicator.beat { background: var(--accent); box-shadow:0 6px 18px rgba(255,122,92,0.25); }
      /* Docked (expanded) keyboard */
      .keyboard-docked #keyboard-container {
        position: fixed !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        height: 260px !important;
        max-height: 40vh !important;
        background: linear-gradient(180deg, rgba(15,17,20,0.98), rgba(8,9,11,0.98));
        padding: 12px 18px !important;
        box-shadow: 0 -20px 80px rgba(0,0,0,0.7);
        z-index: 9999 !important;
        border-top-left-radius: 14px;
        border-top-right-radius: 14px;
        margin: 0 !important;
      }
      .keyboard-docked #keyboard { height:220px; }
      .keyboard-docked #keyboard .key.white { width:72px !important; font-size:12px !important; }
      .keyboard-docked #keyboard .key.black { width:44px !important; margin-left:-22px !important; font-size:12px !important; }
      .keyboard-docked body { padding-bottom: 280px; }
      /* Hidden keyboard mode */
      .keyboard-hidden #keyboard-container { display: none !important; }
      .keyboard-hidden body { padding-bottom: 0 !important; }
    `;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
  }

  // Metronome state
  let audioCtx = null;
  let metronomeTimer = null;
  let metronomeRunning = false;
  let metronomeBpm = 100;
  // beat/score state
  let beat0 = null; // reference time of beat 0 in seconds
  let beatInterval = 60/100; // seconds per beat (init based on default BPM)
  const PERFECT_MS = 50;
  const GOOD_MS = 110;
  let perBarStats = {}; // map barIndex -> { total, perfect, good, poor }
  let barsToShow = 8;
  // Loop A/B state (seconds)
  let loopStart = null;
  let loopEnd = null;
  let loopEnabled = false;
  const PRACTICE_HISTORY_KEY = 'practiceHistory';

  function getPracticeHistory(){
    try{
      const saved = JSON.parse(localStorage.getItem(PRACTICE_HISTORY_KEY) || '[]');
      return Array.isArray(saved) ? saved : [];
    }catch(e){
      return [];
    }
  }

  function renderPracticeHistory(){
    const container = document.getElementById('practice-history');
    if(!container) return;
    const history = getPracticeHistory();
    if(!history.length){
      container.textContent = 'No recorded sessions yet.';
      return;
    }
    container.innerHTML = history.map(entry => `
      <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.03)">
        <strong style="color:var(--text)">${new Date(entry.recordedAt).toLocaleString()}</strong>
        <span>${entry.durationSeconds}s</span>
        <span>${entry.notes} notes</span>
        <span>${entry.accuracy}% accuracy</span>
        <span>${entry.bpm} BPM</span>
      </div>
    `).join('');
  }

  function savePracticeHistory(entry){
    try{
      const history = [entry, ...getPracticeHistory()].slice(0, 10);
      localStorage.setItem(PRACTICE_HISTORY_KEY, JSON.stringify(history));
      renderPracticeHistory();
    }catch(e){ console.warn('save practice history error', e); }
  }

  function ensureAudio(){
    if(!audioCtx){
      try{ audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }catch(e){ console.warn('AudioContext error', e); }
    }
  }

  function playClick(){
    if(!audioCtx) return;
    const t = audioCtx.currentTime;
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = 'square';
    o.frequency.value = 1000;
    g.gain.value = 0.0001;
    o.connect(g); g.connect(audioCtx.destination);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.5, t + 0.001);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
    o.start(t); o.stop(t + 0.07);
    // visual
    const ind = document.getElementById('beat-indicator'); if(ind){ ind.classList.add('beat'); setTimeout(()=>ind.classList.remove('beat'),80); }
  }

  function startMetronome(){
    if(metronomeRunning) return;
    ensureAudio();
    const interval = 60000 / metronomeBpm;
    playClick();
    metronomeTimer = setInterval(playClick, interval);
    metronomeRunning = true;
    const btn = document.getElementById('metronome-toggle'); if(btn) btn.textContent = 'Stop Metronome';
    // anchor beat0 to current time so scoring has a reference
    beat0 = nowSeconds();
    beatInterval = 60 / metronomeBpm;
  }

  function stopMetronome(){
    if(metronomeTimer){ clearInterval(metronomeTimer); metronomeTimer = null; }
    metronomeRunning = false;
    const btn = document.getElementById('metronome-toggle'); if(btn) btn.textContent = 'Start Metronome';
  }

  // scoring helpers
  function scoreNoteOn(note, timestamp){
    if(beat0 === null){
      // if metronome hasn't started, assume beat0 at first note
      beat0 = timestamp;
    }
    const rel = timestamp - beat0;
    const beatIndex = Math.round(rel / beatInterval);
    const beatTime = beat0 + beatIndex * beatInterval;
    const deltaMs = Math.round((timestamp - beatTime) * 1000);
    const absDelta = Math.abs(deltaMs);
    let result = 'poor';
    if(absDelta <= PERFECT_MS) result = 'perfect';
    else if(absDelta <= GOOD_MS) result = 'good';

    const barIndex = Math.floor(beatIndex / 4); // assume 4/4 bars
    if(!perBarStats[barIndex]) perBarStats[barIndex] = { total:0, perfect:0, good:0, poor:0 };
    perBarStats[barIndex].total += 1;
    perBarStats[barIndex][result] += 1;
    updateScoreUI();
    return { barIndex, result, deltaMs };
  }

  function updateScoreUI(){
    const bars = document.getElementById('score-bars');
    const summary = document.getElementById('score-summary');
    if(!bars || !summary) return;
    // collect last N bar indices
    const indices = Object.keys(perBarStats).map(n=>parseInt(n,10)).sort((a,b)=>a-b);
    const last = indices.slice(-barsToShow);
    bars.innerHTML = '';
    let total = 0, tp = 0, tg = 0, tpo = 0;
    for(const bi of last){
      const s = perBarStats[bi];
      total += s.total; tp += s.perfect; tg += s.good; tpo += s.poor;
      const div = document.createElement('div');
      div.style.flex = '1 1 0'; div.style.height = '100%'; div.style.display = 'flex'; div.style.alignItems = 'flex-end';
      const ratio = s.total ? (s.perfect / s.total) : 0;
      const h = Math.max(6, Math.round((s.total ? (s.total/8) : 0) * 48));
      const inner = document.createElement('div'); inner.style.width = '100%'; inner.style.height = (Math.min(56, 6 + Math.round((tp/s.total||0))) + 'px');
      // color proportionally by perfect/good/poor (simple stacked look)
      const perfectPart = document.createElement('div'); perfectPart.style.height = (s.total? Math.round((s.perfect/s.total)*100):0) + '%'; perfectPart.style.background = 'linear-gradient(180deg,#7dd3fc,#7dd3fc)';
      const goodPart = document.createElement('div'); goodPart.style.height = (s.total? Math.round((s.good/s.total)*100):0) + '%'; goodPart.style.background = 'linear-gradient(180deg,#ffcc66,#ffad33)';
      const poorPart = document.createElement('div'); poorPart.style.height = (s.total? Math.round((s.poor/s.total)*100):0) + '%'; poorPart.style.background = 'linear-gradient(180deg,#ff7a5c,#ff4d33)';
      inner.style.display = 'flex'; inner.style.flexDirection = 'column-reverse'; inner.appendChild(perfectPart); inner.appendChild(goodPart); inner.appendChild(poorPart);
      inner.style.borderRadius = '4px'; inner.style.overflow = 'hidden'; inner.style.boxShadow = 'inset 0 0 0 1px rgba(0,0,0,0.12)';
      div.appendChild(inner);
      bars.appendChild(div);
    }
    if(total === 0){ summary.textContent = 'No notes scored yet.'; }
    else { summary.textContent = `Notes: ${total} — Perfect: ${tp} · Good: ${tg} · Poor: ${tpo}`; }
    const bc = document.getElementById('score-bars-count'); if(bc) bc.textContent = String(barsToShow);
  }

  // Simple practice plan generator
  function generatePracticePlan(){
    // build list of bars sorted by difficulty (poor ratio)
    const items = Object.keys(perBarStats).map(k => {
      const s = perBarStats[k];
      const poorRatio = s.total ? (s.poor / s.total) : 0;
      return { bar: parseInt(k,10), total: s.total, poorRatio, perfect: s.perfect, good: s.good, poor: s.poor };
    });
    if(items.length === 0){ return { meta: { generatedAt: new Date().toISOString() }, plan: [] }; }
    items.sort((a,b)=> b.poorRatio - a.poorRatio || b.total - a.total);
    const top = items.slice(0, Math.min(4, items.length));
    // create loops around each top bar (1 bar before/after if available)
    const loops = top.map(it => {
      const startBar = Math.max(0, it.bar - 1);
      const endBar = it.bar + 1;
      return {
        reason: `High error rate (poor ${Math.round(it.poorRatio*100)}%)`,
        barStart: startBar,
        barEnd: endBar,
        targetTempo: Math.max(40, Math.round(metronomeBpm * 0.75)),
        reps: 8
      };
    });
    const plan = {
      generatedAt: new Date().toISOString(),
      bpm: metronomeBpm,
      summary: `Top ${loops.length} problem areas`,
      loops
    };
    return plan;
  }

  function displayPlan(plan){
    const out = document.getElementById('plan-output'); if(!out) return;
    if(!plan || !plan.loops || plan.loops.length === 0){ out.textContent = 'No plan generated (not enough data).'; return; }
    let txt = `Plan (generated ${plan.generatedAt})\nTempo: ${plan.bpm} BPM\n\n`;
    plan.loops.forEach((l, i) => {
      txt += `Loop ${i+1}: bars ${l.barStart}–${l.barEnd} — ${l.reason}\n  Target tempo: ${l.targetTempo} BPM, reps: ${l.reps}\n\n`;
    });
    out.textContent = txt;
  }

  function downloadPlan(plan){
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `practice-plan-${Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  function formatTime(s){
    if(s === null || s === undefined) return '—';
    const total = Math.max(0, Math.floor(s));
    const m = Math.floor(total/60); const sec = total % 60;
    return `${m}:${sec.toString().padStart(2,'0')}`;
  }

  function updateLoopDisplay(){
    const info = document.getElementById('loop-info');
    if(!info) return;
    info.textContent = `A: ${formatTime(loopStart)}  B: ${formatTime(loopEnd)}${loopEnabled? '  (ON)': '  (Off)'} `;
    const toggle = document.getElementById('toggle-loop'); if(toggle) toggle.textContent = `Loop: ${loopEnabled? 'On':'Off'}`;
  }

  function nowSeconds(){
    if(audioCtx) return audioCtx.currentTime;
    return performance.now()/1000;
  }

  function setLoopA(){ loopStart = nowSeconds(); localStorage.setItem('loopA', String(loopStart)); updateLoopDisplay(); }
  function setLoopB(){ loopEnd = nowSeconds(); localStorage.setItem('loopB', String(loopEnd)); updateLoopDisplay(); }
  function toggleLoop(){ loopEnabled = !loopEnabled; localStorage.setItem('loopEnabled', loopEnabled? '1':'0'); updateLoopDisplay(); }


  // dynamic keyboard rendering (visible range + pan/fit controls)
  // default: docked, fit, full 88-key view
  let visibleStart = FULL_START; // show from A0
  let visibleOctaves = 'full'; // show full 88-key range
  let fitWidth = true;

  function getVisibleNotes(){
    if(visibleOctaves === 'full'){
      return { start: FULL_START, end: FULL_END };
    }
    const start = Math.max(FULL_START, Math.min(visibleStart, FULL_END - visibleOctaves*12 + 1));
    const end = Math.min(FULL_END, start + visibleOctaves*12 - 1);
    return { start, end };
  }

  function createKeyboard(container){
    container.innerHTML = '';
    const { start, end } = getVisibleNotes();
    const wrapper = document.createElement('div'); wrapper.id = 'keyboard';
    const keysRow = document.createElement('div'); keysRow.className = 'keys';
    for(let n = start; n <= end; n++){
      const k = document.createElement('div');
      k.className = 'key ' + (isBlack(n) ? 'black' : 'white');
      k.dataset.note = String(n);
      k.title = noteName(n);
      k.innerHTML = `<div style="pointer-events:none">${noteName(n)}</div>`;
      keysRow.appendChild(k);
    }
    wrapper.appendChild(keysRow);
    container.appendChild(wrapper);
    if(fitWidth){ fitKeysToWidth(container); }
  }

  function fitKeysToWidth(container){
    const keyboard = container.querySelector('#keyboard');
    if(!keyboard) return;
    const whiteKeys = Array.from(keyboard.querySelectorAll('.key.white'));
    if(whiteKeys.length === 0) return;
    const available = Math.max(200, container.clientWidth - 20);
    const keyWidth = Math.max(36, Math.floor(available / whiteKeys.length));
    const blackWidth = Math.round(keyWidth * 0.62);
    whiteKeys.forEach(w => { w.style.width = keyWidth + 'px'; });
    const blackKeys = keyboard.querySelectorAll('.key.black');
    blackKeys.forEach(b => { b.style.width = blackWidth + 'px'; b.style.marginLeft = -(blackWidth/2) + 'px'; });
  }

  function highlight(note){
    const el = document.querySelector(`#keyboard [data-note='${note}']`);
    if(el) el.classList.add('active');
  }
  function release(note){
    const el = document.querySelector(`#keyboard [data-note='${note}']`);
    if(el) el.classList.remove('active');
  }

  // MIDI handling
  let midiAccess = null;
  let currentInput = null;
  // Recording state
  let recording = false;
  let recordStart = 0;
  let recordedEvents = [];
  let recordTimer = null;

  function setStatus(text){
    const s = document.getElementById('midi-state'); if(s) s.textContent = text;
  }

  function onMIDIMessage(e){
    const data = e.data; const status = data[0] & 0xf0; const note = data[1]; const vel = data[2];
    // capture for recording (timestamp relative to recordStart)
    if(recording){
      const ts = (nowSeconds() - recordStart);
      recordedEvents.push({ time: ts, data: Array.from(data) });
    }
    if(status === 0x90 && vel > 0){ highlight(note); }
    else if(status === 0x80 || (status === 0x90 && vel === 0)){ release(note); }
  }

  function listInputs(select){
    select.innerHTML = '';
    const empty = document.createElement('option'); empty.value = ''; empty.textContent = '(Choose input)'; select.appendChild(empty);
    for(const input of midiAccess.inputs.values()){
      const opt = document.createElement('option'); opt.value = input.id; opt.textContent = input.name || input.manufacturer || input.id; select.appendChild(opt);
    }
  }

  function attachInputById(id){
    if(currentInput){ currentInput.onmidimessage = null; }
    currentInput = id ? midiAccess.inputs.get(id) : null;
    if(currentInput){ currentInput.onmidimessage = onMIDIMessage; setStatus('connected'); }
    else { setStatus('disconnected'); }
  }

  function initMIDI(){
    if(!navigator.requestMIDIAccess){ setStatus('unsupported'); return; }
    navigator.requestMIDIAccess({ sysex: false }).then(ma => {
      midiAccess = ma;
      const sel = document.getElementById('midi-inputs');
      listInputs(sel);
      sel.addEventListener('change', (ev)=> attachInputById(ev.target.value));
      // auto-select a Yamaha/CVP if available
      for(const input of midiAccess.inputs.values()){
        if(/yamaha|cvp|usb/i.test((input.name||'').toLowerCase())){ sel.value = input.id; attachInputById(input.id); break; }
      }
      midiAccess.onstatechange = ()=> { listInputs(sel); };
      setStatus('ready');
    }).catch(err => { setStatus('error'); console.warn('MIDI init error', err); });
  }

  function updateRecordTimer(){
    const el = document.getElementById('record-timer'); if(!el) return;
    if(!recording){ el.textContent = '00:00'; return; }
    const s = Math.floor(nowSeconds() - recordStart);
    const mm = String(Math.floor(s/60)).padStart(2,'0');
    const ss = String(s % 60).padStart(2,'0');
    el.textContent = `${mm}:${ss}`;
  }

  function startRecording(){
    recordedEvents = [];
    recordStart = nowSeconds();
    recording = true;
    updateRecordTimer();
    recordTimer = setInterval(updateRecordTimer, 500);
    const btn = document.getElementById('record-toggle'); if(btn) btn.textContent = 'Stop Recording';
  }

  function stopRecording(){
    const durationSeconds = Math.max(1, Math.round(nowSeconds() - recordStart));
    recording = false;
    if(recordTimer){ clearInterval(recordTimer); recordTimer = null; }
    const btn = document.getElementById('record-toggle'); if(btn) btn.textContent = 'Start Recording';
    updateRecordTimer();
    try{
      const meta = { recordedAt: new Date().toISOString(), source: (currentInput && currentInput.name) ? currentInput.name : 'unknown', bpm: metronomeBpm };
      const saved = { meta, events: recordedEvents };
      localStorage.setItem('lastRecording', JSON.stringify(saved));
      const total = Object.values(perBarStats).reduce((sum, bar) => sum + bar.total, 0);
      const strong = Object.values(perBarStats).reduce((sum, bar) => sum + bar.perfect + (bar.good * 0.7), 0);
      savePracticeHistory({
        recordedAt: meta.recordedAt,
        durationSeconds,
        notes: recordedEvents.filter(event => (event.data?.[0] & 0xf0) === 0x90 && event.data?.[2] > 0).length,
        accuracy: total ? Math.round((strong / total) * 100) : 0,
        bpm: metronomeBpm,
      });
    }catch(e){ console.warn('save recording error', e); }
  }

  function downloadRecording(){
    if(recordedEvents.length === 0){ alert('No recorded events'); return; }
    const meta = { recordedAt: new Date().toISOString(), source: (currentInput && currentInput.name) ? currentInput.name : 'unknown', bpm: metronomeBpm };
    const payload = { meta, events: recordedEvents };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `midi-recording-${Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  // bootstrap
  function panLeft(){
    visibleStart = Math.max(FULL_START, visibleStart - 12);
    refreshKeyboard();
  }
  function panRight(){
    visibleStart = Math.min(FULL_END - (typeof visibleOctaves === 'number' ? visibleOctaves*12 - 1 : 0), visibleStart + 12);
    refreshKeyboard();
  }

  function refreshKeyboard(){
    const cont = document.getElementById('keyboard-container');
    createKeyboard(cont);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    injectStyles();
    const cont = document.getElementById('keyboard-container');
    if(!cont){ console.warn('No keyboard container'); return; }
    // controls
    const panL = document.getElementById('pan-left');
    const panR = document.getElementById('pan-right');
    const rangeSel = document.getElementById('key-range');
    const fitBtn = document.getElementById('fit-width');
    const dockBtn = document.getElementById('dock-toggle');
    const tempoSlider = document.getElementById('tempo');
    const bpmValue = document.getElementById('bpm-value');
    const metroBtn = document.getElementById('metronome-toggle');
    panL.addEventListener('click', panLeft);
    panR.addEventListener('click', panRight);
    rangeSel.addEventListener('change', (e)=>{
      const v = e.target.value;
      if(v === 'full') visibleOctaves = 'full'; else visibleOctaves = parseInt(v,10);
      // adjust visibleStart so we stay in range
      visibleStart = Math.max(FULL_START, Math.min(visibleStart, FULL_END - (visibleOctaves==='full'?0:visibleOctaves*12) + 1));
      refreshKeyboard();
    });
    fitBtn.addEventListener('click', ()=>{ fitWidth = !fitWidth; fitBtn.textContent = fitWidth ? 'Fixed Size' : 'Fit Width'; refreshKeyboard(); });

    dockBtn.addEventListener('click', ()=>{
      const docked = document.body.classList.toggle('keyboard-docked');
      dockBtn.textContent = docked ? 'Close Keyboard' : 'Expand Keyboard';
      if(docked){ fitWidth = true; refreshKeyboard(); }
      else { document.body.style.paddingBottom = ''; fitWidth = false; refreshKeyboard(); }
    });

    // tempo / metronome UI
    if(tempoSlider && bpmValue){
      tempoSlider.addEventListener('input', (e)=>{
        const v = parseInt(e.target.value,10);
        metronomeBpm = v; bpmValue.textContent = String(v);
        if(metronomeRunning){ stopMetronome(); startMetronome(); }
      });
    }
    if(metroBtn){ metroBtn.addEventListener('click', ()=>{ if(metronomeRunning) stopMetronome(); else startMetronome(); }); }
    // loop controls
    const setA = document.getElementById('set-loop-a');
    const setB = document.getElementById('set-loop-b');
    const toggle = document.getElementById('toggle-loop');
    if(setA) setA.addEventListener('click', ()=>{ setLoopA(); });
    if(setB) setB.addEventListener('click', ()=>{ setLoopB(); });
    if(toggle) toggle.addEventListener('click', ()=>{ toggleLoop(); });

    // load persisted loop
    try{
      const a = localStorage.getItem('loopA'); const b = localStorage.getItem('loopB'); const le = localStorage.getItem('loopEnabled');
      if(a) loopStart = parseFloat(a);
      if(b) loopEnd = parseFloat(b);
      loopEnabled = le === '1';
    }catch(e){}
    updateLoopDisplay();

    // recording UI
    const recBtn = document.getElementById('record-toggle');
    const dlBtn = document.getElementById('download-recording');
    if(recBtn) recBtn.addEventListener('click', ()=>{ if(recording) stopRecording(); else startRecording(); });
    if(dlBtn) dlBtn.addEventListener('click', ()=>{ downloadRecording(); });

    // hide keyboard toggle
    const hideToggle = document.getElementById('hide-keyboard-toggle');
    if(hideToggle){
      try{ const saved = localStorage.getItem('hideKeyboard') === '1'; hideToggle.checked = saved; document.body.classList.toggle('keyboard-hidden', saved); }catch(e){}
      hideToggle.addEventListener('change', (e)=>{
        const val = e.target.checked; document.body.classList.toggle('keyboard-hidden', val); try{ localStorage.setItem('hideKeyboard', val? '1':'0'); }catch(e){}
      });
    }

    // practice plan UI
    const genBtn = document.getElementById('gen-plan');
    const dlPlan = document.getElementById('download-plan');
    if(genBtn) genBtn.addEventListener('click', ()=>{ const plan = generatePracticePlan(); displayPlan(plan); try{ localStorage.setItem('lastPlan', JSON.stringify(plan)); }catch(e){} });
    if(dlPlan) dlPlan.addEventListener('click', ()=>{ const p = localStorage.getItem('lastPlan'); if(!p){ alert('No plan to download — generate one first.'); return; } downloadPlan(JSON.parse(p)); });
    const clearPracticeHistory = document.getElementById('clear-practice-history');
    if(clearPracticeHistory) clearPracticeHistory.addEventListener('click', ()=>{
      if(window.confirm('Clear saved practice history from this browser?')){
        localStorage.removeItem(PRACTICE_HISTORY_KEY);
        renderPracticeHistory();
      }
    });
    renderPracticeHistory();

    // Start with the keyboard in-page so the rest of the practice desk stays visible.
    document.body.classList.remove('keyboard-docked');
    dockBtn.textContent = 'Expand Keyboard';
    fitWidth = true;
    fitBtn.textContent = 'Fixed Size';
    createKeyboard(cont);
    window.addEventListener('resize', ()=>{ if(fitWidth) fitKeysToWidth(cont); });
    initMIDI();
  });

})();
