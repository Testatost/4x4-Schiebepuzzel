<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>15-Puzzle (4×4) – Solver + Log + Bild</title>
  <style>
    :root{
      --n: 4;
      --tile: 62px;
      --gap: 8px;
      --pad: 12px;
      --anim: 160ms;
      --panelW: 340px;

      --bg: #0b1220;
      --card: #111827;
      --board: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --tileBg: #e5e7eb;
      --danger: #ef4444;
      --ok: #22c55e;
    }

    *{ box-sizing: border-box; }
    body{
      margin:0;
      padding:18px;
      display:flex;
      justify-content:center;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }

    .app{ display:flex; gap:16px; align-items:flex-start; }
    .left{ width: 520px; }
    .title{ text-align:center; font-size:20px; font-weight:800; margin-bottom:14px; }

    .board{
      position: relative;
      width: calc(var(--pad)*2 + var(--tile)*var(--n) + var(--gap)*(var(--n) - 1));
      height: calc(var(--pad)*2 + var(--tile)*var(--n) + var(--gap)*(var(--n) - 1));
      background: var(--board);
      border-radius: 16px;
      margin: 0 auto 14px auto;
      overflow:hidden;
      user-select:none;
    }

    .tile{
      position:absolute;
      width: var(--tile);
      height: var(--tile);
      border-radius: 12px;
      border: none;
      font-size: 18px;
      font-weight: 800;
      cursor: pointer;
      background: var(--tileBg);
      display:flex;
      align-items:center;
      justify-content:center;
      transition:
        left var(--anim) cubic-bezier(.2,.8,.2,1),
        top  var(--anim) cubic-bezier(.2,.8,.2,1);
      overflow:hidden;
    }
    .tile:hover{ filter: brightness(1.05); }
    .tile:active{ filter: brightness(0.95); }
    .tile.img{ background: transparent; }
    .tile img{
      width:100%;
      height:100%;
      object-fit: cover;
      display:block;
      border-radius: 12px;
    }

    .controls{ display:flex; flex-direction:column; gap:10px; }
    .row{
      display:flex;
      gap:8px;
      justify-content:center;
      align-items:center;
      flex-wrap:wrap;
    }

    label{ color: var(--muted); font-size: 13px; }
    input[type="text"]{
      width: 320px;
      height: 32px;
      border-radius: 10px;
      border: 1px solid #1f2937;
      background: #0f172a;
      color: var(--text);
      padding: 0 10px;
      outline: none;
    }

    .small{
      width: 90px !important;
      text-align: center;
    }

    button.ctrl{
      width: 160px;
      height: 32px;
      border-radius: 10px;
      border: 1px solid #1f2937;
      background: #0f172a;
      color: var(--text);
      cursor: pointer;
    }
    button.ctrl:hover{ filter: brightness(1.08); }
    button.ctrl:disabled{ opacity: .45; cursor: not-allowed; }
    button.danger{ border-color: #3b0b0b; background: #2a0f14; color: #fecaca; }
    button.ok{ border-color: #083015; background: #0c1f12; color: #bbf7d0; }

    .status{
      text-align:center;
      margin-top: 10px;
      min-height: 22px;
    }
    .hint{
      text-align:center;
      color: var(--muted);
      font-size:12px;
      margin-top:4px;
    }

    .busy{
      margin: 8px auto 0 auto;
      width: 360px;
      height: 10px;
      border-radius: 999px;
      background: #0f172a;
      border: 1px solid #1f2937;
      overflow:hidden;
      display:none;
    }
    .busy > div{
      height:100%;
      width:35%;
      background:#334155;
      border-radius:999px;
      animation: move 0.9s linear infinite;
    }
    @keyframes move{
      from{ transform: translateX(-60%); }
      to  { transform: translateX(320%); }
    }

    .logpanel{
      width: var(--panelW);
      background: var(--card);
      border-radius: 12px;
      padding: 10px;
      display:none;
    }
    .logpanel.visible{ display:block; }

    .logtitle{ font-weight:800; margin-bottom:8px; }
    .log{
      background: #0b1220;
      border: 1px solid #1f2937;
      border-radius: 10px;
      padding: 8px;
      height: 560px;
      overflow:auto;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }
  </style>
</head>

<body>
  <div class="app">
    <div class="left">
      <div class="title">4×4 Schiebepuzzle (15-Puzzle)</div>

      <div class="board" id="board"></div>

      <div class="controls">
        <div class="row">
          <label for="input">Felder setzen:</label>
          <input id="input" type="text" />
        </div>

        <div class="row">
          <button class="ctrl" id="btnSet">Setzen</button>
          <button class="ctrl" id="btnShuffle">Mischen</button>
          <button class="ctrl" id="btnReset">Reset</button>
        </div>

        <div class="row">
          <label for="maxDepth">Max Tiefe:</label>
          <input id="maxDepth" class="small" type="text" value="60" />
          <button class="ctrl ok" id="btnSolve">Auto lösen (PDB+IDA*)</button>
          <button class="ctrl danger" id="btnStop" disabled>Stop</button>
        </div>

        <div class="row">
          <button class="ctrl" id="btnLog">Log anzeigen</button>
          <button class="ctrl" id="btnClearCache">PDB-Cache löschen</button>
        </div>

        <div class="row">
          <button class="ctrl" id="btnImgLoad">Bild laden</button>
          <button class="ctrl" id="btnImgClear" disabled>Bild löschen</button>
          <input id="file" type="file" accept="image/*" hidden />
        </div>
      </div>

      <div class="status" id="status"></div>
      <div class="busy" id="busy"><div></div></div>
      <div class="hint">
        Beim ersten Solve baut der Solver PDBs (kann dauern). Danach deutlich schneller. Max Tiefe limitiert die Suche.
      </div>
    </div>

    <div class="logpanel" id="logPanel">
      <div class="logtitle">Zug-Log</div>
      <div class="log" id="log"></div>
      <div class="row" style="justify-content:flex-start;margin-top:10px;">
        <button class="ctrl" id="btnLogClear">Log leeren</button>
      </div>
    </div>
  </div>

<script>
(() => {
  // -----------------------------
  // 4x4 Setup
  // -----------------------------
  const N = 4;
  const GOAL = [1,2,3,4, 5,6,7,8, 9,10,11,12, 13,14,15,0];
  const NEIGHBORS = Array.from({length:N*N}, (_,idx) => {
    const r = Math.floor(idx/N), c = idx % N;
    const out = [];
    if(r>0) out.push(idx-N);
    if(r<N-1) out.push(idx+N);
    if(c>0) out.push(idx-1);
    if(c<N-1) out.push(idx+1);
    return out;
  });

  function inversions(state){
    const arr = state.filter(x=>x!==0);
    let inv=0;
    for(let i=0;i<arr.length;i++){
      const ai = arr[i];
      for(let j=i+1;j<arr.length;j++){
        if(ai > arr[j]) inv++;
      }
    }
    return inv;
  }
  function blankRowFromBottom(state){
    const z = state.indexOf(0);
    const rowFromTop = Math.floor(z / N);
    return N - rowFromTop; // 1..4
  }
  function isSolvable4x4(state){
    const inv = inversions(state);
    const br = blankRowFromBottom(state);
    return (br%2===1 && inv%2===0) || (br%2===0 && inv%2===1);
  }
  function parseState(text){
    const t0 = (text ?? "").trim();
    if(!t0) return null;
    const parts = t0.replace(/[;,]/g," ").split(/\s+/).filter(Boolean);
    if(parts.length !== 16) return null;
    const vals = parts.map(p=>Number(p));
    if(vals.some(v=>!Number.isInteger(v))) return null;
    const s = vals.slice().sort((a,b)=>a-b).join(",");
    if(s !== "0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15") return null;
    return vals;
  }

  // -----------------------------
  // DOM
  // -----------------------------
  const boardEl = document.getElementById("board");
  const inputEl = document.getElementById("input");
  const maxDepthEl = document.getElementById("maxDepth");
  const statusEl = document.getElementById("status");
  const busyEl = document.getElementById("busy");

  const btnSet = document.getElementById("btnSet");
  const btnShuffle = document.getElementById("btnShuffle");
  const btnReset = document.getElementById("btnReset");
  const btnSolve = document.getElementById("btnSolve");
  const btnStop = document.getElementById("btnStop");

  const btnLog = document.getElementById("btnLog");
  const logPanel = document.getElementById("logPanel");
  const logEl = document.getElementById("log");
  const btnLogClear = document.getElementById("btnLogClear");

  const btnImgLoad = document.getElementById("btnImgLoad");
  const btnImgClear = document.getElementById("btnImgClear");
  const fileEl = document.getElementById("file");

  const btnClearCache = document.getElementById("btnClearCache");

  const TILE = 62, GAP = 8, PAD = 12;
  const ANIM_MS = 160;
  const PLAYBACK_GAP_MS = 40;

  let state = GOAL.slice();
  let initialState = state.slice();
  let animating = false;

  let autoPlaying = false;
  let pendingMoves = [];

  // image mode
  let imageMode = false;
  const tileImages = new Map(); // val -> dataURL

  // tiles DOM
  const tiles = new Map(); // val -> button

  // -----------------------------
  // Worker (PDB+IDA*)
  // -----------------------------
  const worker = new Worker("./solver-worker.js");
  let solving = false;

  function postWorker(type, payload = {}) {
    worker.postMessage({ type, ...payload });
  }

  worker.onmessage = (ev) => {
    const msg = ev.data || {};
    if(msg.type === "progress"){
      setStatus(msg.text || "");
      setBusy(true);
      return;
    }
    if(msg.type === "ready"){
      return;
    }
    if(msg.type === "cacheCleared"){
      log(`--- PDB Cache gelöscht ---`);
      return;
    }
    if(msg.type === "solved"){
      solving = false;
      setBusy(false);

      if(msg.status === "cancelled"){
        log("--- SOLVER: abgebrochen ---");
        setStatus("⏹️ Suche abgebrochen.");
        btnStop.disabled = true;
        setControlsEnabled(true);
        return;
      }
      if(msg.status !== "ok" || !Array.isArray(msg.moves)){
        log("--- SOLVER: keine Lösung / Fehler ---");
        setStatus("");
        btnStop.disabled = true;
        setControlsEnabled(true);
        alert("Keine Lösung gefunden oder Fehler. Tipp: erneut versuchen oder maxDepth erhöhen.");
        return;
      }

      const moves = msg.moves;
      if(moves.length === 0){
        log("--- SOLVER: schon gelöst ---");
        setStatus("✅ Zielzustand erreicht!");
        btnStop.disabled = true;
        setControlsEnabled(true);
        return;
      }

      log(`--- AUTO SOLVE: ${moves.length} Züge ---`);
      pendingMoves = moves.slice();
      autoPlaying = true;

      btnStop.disabled = false;
      setControlsEnabled(false);
      setStatus(`▶️ Auto-Lösung läuft … (noch ${pendingMoves.length} Züge)`);
      playNextMove();
      return;
    }
  };

  // -----------------------------
  // UI helpers
  // -----------------------------
  function setBusy(on){ busyEl.style.display = on ? "block" : "none"; }
  function setStatus(text){ statusEl.textContent = text || ""; }
  function log(msg){
    logEl.textContent += (logEl.textContent ? "\n" : "") + msg;
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setControlsEnabled(enabled){
    inputEl.disabled = !enabled;
    maxDepthEl.disabled = !enabled;
    btnSet.disabled = !enabled;
    btnShuffle.disabled = !enabled;
    btnReset.disabled = !enabled;
    btnSolve.disabled = !enabled;
    btnImgLoad.disabled = !enabled;
    btnImgClear.disabled = !(enabled && imageMode);
    btnClearCache.disabled = !enabled;

    for(const b of tiles.values()){
      b.style.pointerEvents = enabled ? "auto" : "none";
      b.disabled = !enabled;
    }

    btnLog.disabled = false;
    btnLogClear.disabled = false;
  }

  function cellPos(index){
    const r = Math.floor(index/N);
    const c = index % N;
    return { x: PAD + c*(TILE+GAP), y: PAD + r*(TILE+GAP) };
  }
  function idxToRC(idx){
    const r = Math.floor(idx/N), c = idx%N;
    return [r+1, c+1];
  }

  function setSolvedStatus(){
    if(state.join(",") === GOAL.join(",")) setStatus("✅ Zielzustand erreicht!");
  }

  function syncTilesToState(animate){
    setSolvedStatus();
    if(!animate){
      for(let idx=0; idx<16; idx++){
        const v = state[idx];
        if(v===0) continue;
        const {x,y} = cellPos(idx);
        const b = tiles.get(v);
        b.style.left = x + "px";
        b.style.top  = y + "px";
      }
      return;
    }

    animating = true;
    setControlsEnabled(false);

    for(let idx=0; idx<16; idx++){
      const v = state[idx];
      if(v===0) continue;
      const {x,y} = cellPos(idx);
      const b = tiles.get(v);
      b.style.left = x + "px";
      b.style.top  = y + "px";
    }

    setTimeout(() => {
      animating = false;
      if(!autoPlaying && !solving) setControlsEnabled(true);
      setSolvedStatus();
      if(autoPlaying) setTimeout(playNextMove, PLAYBACK_GAP_MS);
    }, ANIM_MS + 5);
  }

  function applyMoveByTileValue(tileValue, fromAuto){
    if(animating) return;
    const zeroIdx = state.indexOf(0);
    const tileIdx = state.indexOf(tileValue);
    if(!NEIGHBORS[zeroIdx].includes(tileIdx)) return;

    const fr = idxToRC(tileIdx);
    const to = idxToRC(zeroIdx);

    state[zeroIdx] = tileValue;
    state[tileIdx] = 0;

    log(`[${fromAuto ? "AUTO" : "USER"}] ${tileValue}  (${fr[0]},${fr[1]}) -> (${to[0]},${to[1]})`);
    syncTilesToState(true);
  }

  // -----------------------------
  // Build tiles
  // -----------------------------
  function buildTiles(){
    boardEl.innerHTML = "";
    tiles.clear();
    for(let v=1; v<=15; v++){
      const b = document.createElement("button");
      b.className = "tile";
      b.type = "button";
      b.textContent = String(v);
      b.style.transitionDuration = ANIM_MS + "ms";
      b.addEventListener("click", () => {
        if(solving || autoPlaying) return;
        applyMoveByTileValue(v, false);
      });
      boardEl.appendChild(b);
      tiles.set(v,b);
    }
  }

  function applyTileAppearance(){
    for(let v=1; v<=15; v++){
      const b = tiles.get(v);
      b.classList.toggle("img", imageMode && tileImages.has(v));
      b.innerHTML = "";
      if(imageMode && tileImages.has(v)){
        const img = document.createElement("img");
        img.src = tileImages.get(v);
        img.alt = "";
        b.appendChild(img);
      }else{
        b.textContent = String(v);
      }
    }
  }

  // -----------------------------
  // Shuffle
  // -----------------------------
  function shuffle(steps=250){
    state = GOAL.slice();
    let zeroIdx = state.indexOf(0);
    let last = null;

    for(let k=0;k<steps;k++){
      let nbs = NEIGHBORS[zeroIdx].slice();
      if(last !== null && nbs.includes(last) && nbs.length > 1){
        nbs = nbs.filter(x => x !== last);
      }
      const nxt = nbs[Math.floor(Math.random()*nbs.length)];
      [state[zeroIdx], state[nxt]] = [state[nxt], state[zeroIdx]];
      last = zeroIdx;
      zeroIdx = nxt;
    }

    initialState = state.slice();
    inputEl.value = state.join(" ");
    log(`--- SHUFFLE: [${state.join(" ")}] ---`);
    syncTilesToState(true);
  }

  // -----------------------------
  // Playback
  // -----------------------------
  function playNextMove(){
    if(!autoPlaying || animating) return;

    if(pendingMoves.length === 0){
      autoPlaying = false;
      btnStop.disabled = true;
      setControlsEnabled(true);
      setStatus(state.join(",") === GOAL.join(",") ? "✅ Auto-Lösung fertig!" : "⏹️ Auto-Lösung beendet.");
      return;
    }

    const nxt = pendingMoves.shift();
    setStatus(`▶️ Auto-Lösung läuft … (noch ${pendingMoves.length} Züge)`);
    applyMoveByTileValue(nxt, true);
  }

  // -----------------------------
  // Image slicing
  // -----------------------------
  function fileToDataURL(file){
    return new Promise((resolve,reject)=>{
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = reject;
      r.readAsDataURL(file);
    });
  }

  function sliceImageIntoTiles(dataUrl){
    return new Promise((resolve,reject)=>{
      const img = new Image();
      img.onload = () => {
        try{
          const side = Math.min(img.width, img.height);
          const x0 = Math.floor((img.width - side)/2);
          const y0 = Math.floor((img.height - side)/2);

          const inner = TILE*N + GAP*(N-1);

          const base = document.createElement("canvas");
          base.width = inner; base.height = inner;
          const ctx = base.getContext("2d");
          ctx.drawImage(img, x0, y0, side, side, 0, 0, inner, inner);

          tileImages.clear();
          for(let idx=0; idx<16; idx++){
            const val = GOAL[idx];
            if(val === 0) continue;
            const r = Math.floor(idx/N), c = idx%N;
            const sx = c*(TILE+GAP);
            const sy = r*(TILE+GAP);

            const tileC = document.createElement("canvas");
            tileC.width = TILE; tileC.height = TILE;
            tileC.getContext("2d").drawImage(base, sx, sy, TILE, TILE, 0, 0, TILE, TILE);
            tileImages.set(val, tileC.toDataURL("image/png"));
          }
          resolve();
        }catch(err){ reject(err); }
      };
      img.onerror = reject;
      img.src = dataUrl;
    });
  }

  // -----------------------------
  // Buttons
  // -----------------------------
  btnLog.addEventListener("click", () => {
    const vis = !logPanel.classList.contains("visible");
    logPanel.classList.toggle("visible", vis);
    btnLog.textContent = vis ? "Log verbergen" : "Log anzeigen";
  });
  btnLogClear.addEventListener("click", () => { logEl.textContent = ""; });

  btnSet.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;

    const vals = parseState(inputEl.value);
    if(!vals){
      alert("Ungültig: Bitte genau 16 Zahlen 0–15 angeben (jede genau einmal).");
      return;
    }
    if(!isSolvable4x4(vals)){
      const ok = confirm("Warnung: unlösbar\nDiese Ausgangslage ist (als 4×4) NICHT lösbar.\nTrotzdem setzen?");
      if(!ok) return;
    }

    state = vals.slice();
    initialState = vals.slice();
    log(`--- SET: [${state.join(" ")}] ---`);
    syncTilesToState(true);
  });

  btnReset.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;
    state = initialState.slice();
    log(`--- RESET: [${state.join(" ")}] ---`);
    syncTilesToState(true);
  });

  btnShuffle.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;
    shuffle(250);
  });

  btnSolve.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;
    if(!isSolvable4x4(state)){
      alert("Diese Ausgangslage ist unlösbar.");
      return;
    }

    // read maxDepth
    let md = Number(maxDepthEl.value || 60);
    if(!Number.isFinite(md) || md < 1) md = 60;
    md = Math.max(1, Math.min(200, Math.floor(md)));
    maxDepthEl.value = String(md);

    solving = true;
    btnStop.disabled = false;
    setControlsEnabled(false);
    setBusy(true);
    setStatus(`🧠 Starte Solver… (maxDepth=${md})`);
    log(`--- SOLVER: gestartet (maxDepth=${md}) ---`);

    postWorker("solve", { state: state.slice(), maxDepth: md });
  });

  btnStop.addEventListener("click", () => {
    if(solving){
      postWorker("cancel");
      btnStop.disabled = true;
      setStatus("⏹️ Stop… (breche Suche ab)");
      log("--- STOP: Suche wird abgebrochen ---");
      return;
    }
    if(autoPlaying){
      autoPlaying = false;
      pendingMoves = [];
      btnStop.disabled = true;
      if(!animating) setControlsEnabled(true);
      setStatus("⏹️ Auto-Lösung gestoppt.");
    }
  });

  btnImgLoad.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;
    fileEl.value = "";
    fileEl.click();
  });

  fileEl.addEventListener("change", async () => {
    if(!fileEl.files || !fileEl.files[0]) return;
    try{
      const dataUrl = await fileToDataURL(fileEl.files[0]);
      await sliceImageIntoTiles(dataUrl);
      imageMode = true;
      btnImgClear.disabled = false;
      applyTileAppearance();
      log(`--- BILD GELADEN: ${fileEl.files[0].name} ---`);
    }catch(e){
      console.error(e);
      alert("Konnte das Bild nicht laden/verarbeiten.");
    }
  });

  btnImgClear.addEventListener("click", () => {
    if(animating || autoPlaying || solving) return;
    imageMode = false;
    tileImages.clear();
    btnImgClear.disabled = true;
    applyTileAppearance();
    log("--- BILD GELÖSCHT: Standardoptik ---");
  });

  btnClearCache.addEventListener("click", () => {
    if(solving || autoPlaying || animating) return;
    const ok = confirm("PDB-Cache löschen? Danach muss beim nächsten Solve neu gebaut werden.");
    if(!ok) return;
    postWorker("clear_cache");
  });

  // Init
  buildTiles();
  applyTileAppearance();
  inputEl.value = GOAL.join(" ");
  syncTilesToState(false);
  setControlsEnabled(true);
  setBusy(false);

  postWorker("ping");
})();
</script>
</body>
</html>
