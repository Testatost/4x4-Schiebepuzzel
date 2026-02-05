/* eslint-disable no-restricted-globals */

// =====================================================
// 15-Puzzle Solver Worker
// - Additive Pattern Databases (cost-splitting via 0-1 BFS)
// - IDA* search with PDB heuristic
// - IndexedDB cache for PDBs
// =====================================================

const N = 4;
const GOAL = [1,2,3,4, 5,6,7,8, 9,10,11,12, 13,14,15,0];
const GOAL_POS = new Int16Array(16);
for (let i = 0; i < 16; i++) GOAL_POS[GOAL[i]] = i;

// Precompute neighbors
const NEIGHBORS = Array.from({ length: 16 }, (_, idx) => {
    const r = Math.floor(idx / N), c = idx % N;
    const out = [];
    if (r > 0) out.push(idx - N);
    if (r < N - 1) out.push(idx + N);
    if (c > 0) out.push(idx - 1);
    if (c < N - 1) out.push(idx + 1);
    return out;
});

// PATTERNS (additive): 4-4-4-3 split (fast + moderate memory)
// Each PDB includes BLANK + pattern tiles
const PATTERNS = [
    [1,2,3,4],
[5,6,7,8],
[9,10,11,12],
[13,14,15],
];

// IndexedDB config
const DB_NAME = "pdb15_cache";
const DB_VERSION = 1;
const STORE = "pdb";

// Cancel flags
let CANCELLED = false;

// ------------------------------
// Messaging
// ------------------------------
postMessage({ type: "ready" });

onmessage = async (ev) => {
    const msg = ev.data || {};
    try{
        if (msg.type === "ping") {
            postMessage({ type: "ready" });
            return;
        }
        if (msg.type === "cancel") {
            CANCELLED = true;
            return;
        }
        if (msg.type === "clear_cache") {
            await clearCache();
            postMessage({ type: "cacheCleared" });
            return;
        }
        if (msg.type === "solve") {
            CANCELLED = false;
            const start = msg.state;
            const moves = await solve(start);
            if (CANCELLED) {
                postMessage({ type: "solved", status: "cancelled", moves: null });
            } else if (!moves) {
                postMessage({ type: "solved", status: "fail", moves: null });
            } else {
                postMessage({ type: "solved", status: "ok", moves });
            }
        }
    }catch(err){
        postMessage({ type: "solved", status: "fail", moves: null, error: String(err?.message || err) });
    }
};

// ------------------------------
// Progress helper
// ------------------------------
let lastProgress = 0;
function progress(text){
    const now = performance.now();
    if (now - lastProgress > 120) {
        lastProgress = now;
        postMessage({ type: "progress", text });
    }
}

// ------------------------------
// IndexedDB helpers
// ------------------------------
function openDB(){
    return new Promise((resolve,reject)=>{
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onerror = () => reject(req.error);
        req.onupgradeneeded = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains(STORE)) {
                db.createObjectStore(STORE, { keyPath: "key" });
            }
        };
        req.onsuccess = () => resolve(req.result);
    });
}

async function dbGet(key){
    const db = await openDB();
    return new Promise((resolve,reject)=>{
        const tx = db.transaction(STORE, "readonly");
        const st = tx.objectStore(STORE);
        const req = st.get(key);
        req.onerror = () => reject(req.error);
        req.onsuccess = () => resolve(req.result || null);
    }).finally(()=>db.close());
}

async function dbPut(key, buffer){
    const db = await openDB();
    return new Promise((resolve,reject)=>{
        const tx = db.transaction(STORE, "readwrite");
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
        tx.objectStore(STORE).put({ key, buffer });
    }).finally(()=>db.close());
}

async function clearCache(){
    const db = await openDB();
    return new Promise((resolve,reject)=>{
        const tx = db.transaction(STORE, "readwrite");
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
        tx.objectStore(STORE).clear();
    }).finally(()=>db.close());
}

// ------------------------------
// Permutation ranking (partial)
// ------------------------------
function permCount(n, k){
    let out = 1;
    for(let i=0;i<k;i++) out *= (n - i);
    return out;
}

// Rank a partial permutation of length m (positions are integers 0..15, all distinct)
// identical to your Python idea: count unused < p, multiply by remaining permutations.
function rankPartialPerm(positions, n=16){
    const m = positions.length;
    const used = new Uint8Array(n);
    let rank = 0;
    for(let i=0;i<m;i++){
        const p = positions[i];
        let c = 0;
        for(let x=0;x<p;x++){
            if(!used[x]) c++;
        }
        used[p] = 1;
        const remainingN = n - (i + 1);
        const remainingK = m - (i + 1);
        rank += c * permCount(remainingN, remainingK);
    }
    return rank;
}

function patternKey(pattern){
    return "pdb_" + pattern.join("_");
}

// ------------------------------
// 0-1 BFS PDB Builder
// ------------------------------
function dequeCreate(cap=1<<20){
    // simple deque using arrays and head index
    return { a: new Array(cap), head: 0, tail: 0, cap };
}
function dequeLen(d){ return d.tail - d.head; }
function dequePushBack(d, x){
    d.a[d.tail % d.cap] = x;
    d.tail++;
    if (d.tail - d.head > d.cap - 4) {
        // grow
        const newCap = d.cap * 2;
        const na = new Array(newCap);
        const len = dequeLen(d);
        for(let i=0;i<len;i++) na[i] = d.a[(d.head + i) % d.cap];
        d.a = na; d.cap = newCap; d.head = 0; d.tail = len;
    }
}
function dequePushFront(d, x){
    d.head--;
    d.a[(d.head + d.cap) % d.cap] = x;
}
function dequePopFront(d){
    if (d.tail === d.head) return null;
    const x = d.a[d.head % d.cap];
    d.head++;
    return x;
}

function buildPDB(pattern){
    // pattern tiles length k; we include blank => m = 1 + k
    const m = 1 + pattern.length;
    const size = permCount(16, m);

    // distances in Uint16, 65535 = INF
    const dist = new Uint16Array(size);
    dist.fill(65535);

    // goal positions
    const blankGoal = GOAL_POS[0];
    const tileGoals = pattern.map(t => GOAL_POS[t]);
    const startPositions = [blankGoal, ...tileGoals];
    const startIdx = rankPartialPerm(startPositions, 16);

    dist[startIdx] = 0;

    const dq = dequeCreate();
    dequePushBack(dq, startPositions);

    const inPatternPos = new Int8Array(16);
    let visited = 0;
    const t0 = performance.now();

    while (dequeLen(dq) > 0) {
        if (CANCELLED) throw new Error("CANCELLED");

        const posList = dequePopFront(dq);
        const curIdx = rankPartialPerm(posList, 16);
        const curD = dist[curIdx];
        const blankPos = posList[0];

        inPatternPos.fill(-1);
        for (let i = 1; i < m; i++) inPatternPos[posList[i]] = i;

        for (const nb of NEIGHBORS[blankPos]) {
            let stepCost = 0;
            const newPos = posList.slice();

            const tileIndex = inPatternPos[nb];
            if (tileIndex !== -1) {
                // moved tile is in pattern => cost 1, swap blank with tileIndex
                const tmp = newPos[0];
                newPos[0] = newPos[tileIndex];
                newPos[tileIndex] = tmp;
                stepCost = 1;
            } else {
                // moved irrelevant tile => cost 0, only blank changes
                newPos[0] = nb;
                stepCost = 0;
            }

            const newIdx = rankPartialPerm(newPos, 16);
            const nd = curD + stepCost;
            if (nd < dist[newIdx]) {
                dist[newIdx] = nd;
                if (stepCost === 0) dequePushFront(dq, newPos);
                else dequePushBack(dq, newPos);
            }
        }

        visited++;
        if ((visited & 0x3FFFF) === 0) { // every ~262k
            const secs = ((performance.now() - t0) / 1000).toFixed(1);
            progress(`PDB ${pattern.join(",")} bauen… visited=${visited.toLocaleString()} | ~${secs}s`);
            // yield a bit (worker still can yield)
        }
    }

    progress(`PDB ${pattern.join(",")} fertig. size=${size.toLocaleString()}`);
    return dist;
}

async function loadOrBuildPDB(pattern){
    const key = patternKey(pattern);
    const m = 1 + pattern.length;
    const expectedSize = permCount(16, m);

    // Try load
    const rec = await dbGet(key);
    if (rec && rec.buffer) {
        try{
            const buf = rec.buffer;
            const arr = new Uint16Array(buf);
            if (arr.length === expectedSize) {
                progress(`PDB ${pattern.join(",")} Cache geladen.`);
                return arr;
            }
        }catch(_){}
    }

    progress(`PDB ${pattern.join(",")} Cache fehlt → baue neu…`);
    const dist = buildPDB(pattern);

    // Store as ArrayBuffer (copy)
    await dbPut(key, dist.buffer.slice(0));

    return dist;
}

// ------------------------------
// Heuristic using additive PDBs
// ------------------------------
let PDBS = null; // array of {pattern, dist}
async function ensurePDBs(){
    if (PDBS) return PDBS;
    PDBS = [];

    for (let i=0;i<PATTERNS.length;i++){
        progress(`Lade/Baue PDB ${i+1}/${PATTERNS.length}…`);
        const pattern = PATTERNS[i];
        const dist = await loadOrBuildPDB(pattern);
        PDBS.push({ pattern, dist });
    }
    progress("Alle PDBs bereit.");
    return PDBS;
}

function pdbHeuristic(stateArr){
    // pos_of[tile] = index
    const posOf = new Int8Array(16);
    for(let i=0;i<16;i++) posOf[stateArr[i]] = i;
    const blankPos = posOf[0];

    let h = 0;
    for(const { pattern, dist } of PDBS){
        const positions = [blankPos];
        for(const t of pattern) positions.push(posOf[t]);
        const idx = rankPartialPerm(positions, 16);
        const d = dist[idx];
        if (d !== 65535) h += d;
    }
    return h;
}

// ------------------------------
// IDA* with PDB heuristic
// ------------------------------
async function idaStarSolvePDB(start){
    const goalKey = GOAL.join(",");
    const startKey = start.join(",");
    if (startKey === goalKey) return [];

    let nodes = 0;
    let lastPing = performance.now();

    const startH = pdbHeuristic(start);
    let bound = startH;

    function swapInPlace(a,i,j){ const t=a[i]; a[i]=a[j]; a[j]=t; }

    // order moves by heuristic
    function orderedMoves(state, blankIdx, prevBlank){
        const cand = [];
        for(const nb of NEIGHBORS[blankIdx]){
            if (nb === prevBlank) continue;
            swapInPlace(state, blankIdx, nb);
            const h = pdbHeuristic(state);
            const movedTile = state[blankIdx]; // after swap
            cand.push([h, nb, movedTile]);
            swapInPlace(state, blankIdx, nb);
        }
        cand.sort((a,b)=>a[0]-b[0]);
        return cand;
    }

    async function search(state, g, bound, blankIdx, prevBlank, path){
        if (CANCELLED) throw new Error("CANCELLED");

        const h = pdbHeuristic(state);
        const f = g + h;
        if (f > bound) return { found:false, next:f };
        if (state.join(",") === goalKey) return { found:true, next:g };

        nodes++;
        const now = performance.now();
        if (now - lastPing > 200) {
            lastPing = now;
            progress(`Suche… bound=${bound} | Tiefe=${g} | Knoten=${nodes.toLocaleString()}`);
            // yield
            await new Promise(r=>setTimeout(r,0));
            if (CANCELLED) throw new Error("CANCELLED");
        }

        let minNext = Infinity;

        const cand = orderedMoves(state, blankIdx, prevBlank);
        for (const [, nb, moved] of cand){
            swapInPlace(state, blankIdx, nb);
            path.push(moved);

            const res = await search(state, g+1, bound, nb, blankIdx, path);
            if (res.found) return res;

            path.pop();
            swapInPlace(state, blankIdx, nb);

            if (res.next < minNext) minNext = res.next;
        }

        return { found:false, next:minNext };
    }

    while(true){
        if (CANCELLED) throw new Error("CANCELLED");
        progress(`IDA* Iteration… bound=${bound}`);
        const state = start.slice();
        const blankIdx = state.indexOf(0);
        const path = [];

        const res = await search(state, 0, bound, blankIdx, -1, path);
        if (res.found) {
            progress(`Lösung gefunden! Züge=${path.length}`);
            return path.slice();
        }
        if (!Number.isFinite(res.next)) return null;
        bound = res.next;
    }
}

// ------------------------------
// Solve pipeline
// ------------------------------
async function solve(start){
    await ensurePDBs();
    progress("Starte IDA* (PDB) …");
    try{
        return await idaStarSolvePDB(start);
    }catch(err){
        if (String(err?.message || err) === "CANCELLED") return null;
        throw err;
    }
}
