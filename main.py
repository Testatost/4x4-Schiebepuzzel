import sys
import os
import random
import time
from collections import deque
from array import array
from typing import List, Optional, Tuple, Dict

from PySide6.QtCore import (
    Qt, QRect, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QTimer, QSize,
    QObject, QThread, Signal, Slot
)
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox, QFrame,
    QTextEdit, QSizePolicy, QFileDialog, QProgressBar
)

# -----------------------------
# 4x4 Puzzle (15-Puzzle) Setup
# -----------------------------

N = 4
GOAL = [
    1,  2,  3,  4,
    5,  6,  7,  8,
    9, 10, 11, 12,
   13, 14, 15,  0
]
GOAL_POS = {v: i for i, v in enumerate(GOAL)}

NEIGHBORS = [[] for _ in range(N * N)]
for idx in range(N * N):
    r, c = divmod(idx, N)
    if r > 0: NEIGHBORS[idx].append(idx - N)
    if r < N - 1: NEIGHBORS[idx].append(idx + N)
    if c > 0: NEIGHBORS[idx].append(idx - 1)
    if c < N - 1: NEIGHBORS[idx].append(idx + 1)


# -----------------------------
# Solvability + Parsing
# -----------------------------

def inversions(state: List[int]) -> int:
    arr = [x for x in state if x != 0]
    inv = 0
    for i in range(len(arr)):
        ai = arr[i]
        for j in range(i + 1, len(arr)):
            if ai > arr[j]:
                inv += 1
    return inv

def blank_row_from_bottom(state: List[int]) -> int:
    z = state.index(0)
    row_from_top = z // N
    return N - row_from_top

def is_solvable_4x4(state: List[int]) -> bool:
    inv = inversions(state)
    br = blank_row_from_bottom(state)
    return (br % 2 == 1 and inv % 2 == 0) or (br % 2 == 0 and inv % 2 == 1)

def parse_state(text: str) -> Optional[List[int]]:
    t = text.strip()
    if not t:
        return None
    for sep in [",", ";"]:
        t = t.replace(sep, " ")
    parts = [p for p in t.split() if p]
    if len(parts) != 16:
        return None
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        return None
    if sorted(vals) != list(range(16)):
        return None
    return vals


# -----------------------------
# Pattern Database (PDB)
# Additive via cost-splitting (0-1 BFS)
# -----------------------------

PATTERNS = [
    (1, 2, 3, 4, 5),
    (6, 7, 8, 9, 10),
    (11, 12, 13, 14, 15),
]

def perm_count(n: int, k: int) -> int:
    out = 1
    for i in range(k):
        out *= (n - i)
    return out

def rank_partial_perm(positions: List[int], n: int = 16) -> int:
    m = len(positions)
    used = [False] * n
    rank = 0
    for i in range(m):
        p = positions[i]
        c = 0
        for x in range(p):
            if not used[x]:
                c += 1
        used[p] = True
        remaining_n = n - (i + 1)
        remaining_k = m - (i + 1)
        rank += c * perm_count(remaining_n, remaining_k)
    return rank

def pdb_filename(pattern_tiles: Tuple[int, ...]) -> str:
    name = "pdb_" + "_".join(map(str, pattern_tiles)) + ".bin"
    return os.path.join("pdb_cache", name)

def build_pdb(pattern_tiles: Tuple[int, ...], progress_cb=None, cancel_cb=None) -> array:
    """
    Build PDB for given tiles via 0-1 BFS from goal abstract state.
    progress_cb(msg, a, b) optional
    cancel_cb() -> bool optional
    """
    m = 1 + len(pattern_tiles)
    size = perm_count(16, m)
    dist = array('H', [65535]) * size

    blank_goal = GOAL_POS[0]
    tile_goal_positions = [GOAL_POS[t] for t in pattern_tiles]
    start_positions = [blank_goal] + tile_goal_positions
    start_idx = rank_partial_perm(start_positions)

    dist[start_idx] = 0
    dq = deque([start_positions])

    # Light progress pacing
    last_ping = time.time()
    visited = 0

    while dq:
        if cancel_cb and cancel_cb():
            raise RuntimeError("CANCELLED")

        pos_list = dq.popleft()
        cur_idx = rank_partial_perm(pos_list)
        cur_d = dist[cur_idx]
        blank_pos = pos_list[0]

        # build map pos -> tile-index (1..)
        tile_pos_to_i = {}
        for i in range(1, m):
            tile_pos_to_i[pos_list[i]] = i

        for nb in NEIGHBORS[blank_pos]:
            if nb in tile_pos_to_i:
                i_tile = tile_pos_to_i[nb]
                new_pos = pos_list[:]
                new_pos[0], new_pos[i_tile] = new_pos[i_tile], new_pos[0]
                step_cost = 1
            else:
                new_pos = pos_list[:]
                new_pos[0] = nb
                step_cost = 0

            new_idx = rank_partial_perm(new_pos)
            nd = cur_d + step_cost
            if nd < dist[new_idx]:
                dist[new_idx] = nd
                if step_cost == 0:
                    dq.appendleft(new_pos)
                else:
                    dq.append(new_pos)

        visited += 1
        # Throttle progress emissions
        now = time.time()
        if progress_cb and (now - last_ping) > 0.25:
            last_ping = now
            progress_cb(f"PDB {pattern_tiles}: baue… ({visited:,} Zustände verarbeitet)", visited, size)

    if progress_cb:
        progress_cb(f"PDB {pattern_tiles}: fertig.", size, size)

    return dist

def load_or_build_pdb(pattern_tiles: Tuple[int, ...], progress_cb=None, cancel_cb=None) -> array:
    os.makedirs("pdb_cache", exist_ok=True)
    fn = pdb_filename(pattern_tiles)
    m = 1 + len(pattern_tiles)
    expected_size = perm_count(16, m)

    if os.path.exists(fn):
        try:
            if progress_cb:
                progress_cb(f"PDB {pattern_tiles}: lade Cache…", 0, expected_size)
            with open(fn, "rb") as f:
                a = array('H')
                a.fromfile(f, expected_size)
            if len(a) == expected_size:
                if progress_cb:
                    progress_cb(f"PDB {pattern_tiles}: Cache geladen.", expected_size, expected_size)
                return a
        except Exception:
            pass

    if progress_cb:
        progress_cb(f"PDB {pattern_tiles}: Cache fehlt/kaputt → baue neu…", 0, expected_size)

    a = build_pdb(pattern_tiles, progress_cb=progress_cb, cancel_cb=cancel_cb)
    with open(fn, "wb") as f:
        a.tofile(f)
    return a

PDBS: Dict[Tuple[int, ...], array] = {}

def ensure_pdbs_loaded(progress_cb=None, cancel_cb=None):
    for p in PATTERNS:
        if p not in PDBS:
            PDBS[p] = load_or_build_pdb(p, progress_cb=progress_cb, cancel_cb=cancel_cb)

def pdb_heuristic(state: Tuple[int, ...]) -> int:
    pos_of = [0] * 16
    for idx, v in enumerate(state):
        pos_of[v] = idx
    blank_pos = pos_of[0]

    h = 0
    for pattern_tiles, pdb in PDBS.items():
        positions = [blank_pos] + [pos_of[t] for t in pattern_tiles]
        idx = rank_partial_perm(positions)
        d = pdb[idx]
        if d != 65535:
            h += d
    return h


# -----------------------------
# IDA* with PDB (thread-friendly + cancel + progress)
# -----------------------------

class CancelFlag:
    def __init__(self):
        self._cancel = False
    def cancel(self):
        self._cancel = True
    def is_cancelled(self) -> bool:
        return self._cancel

def ida_star_solve_pdb(
    start: List[int],
    cancel: CancelFlag,
    progress_cb=None
) -> Optional[List[int]]:
    ensure_pdbs_loaded(progress_cb=progress_cb, cancel_cb=cancel.is_cancelled)

    start_t = tuple(start)
    goal_t = tuple(GOAL)
    if start_t == goal_t:
        return []

    # To show progress
    nodes = 0
    last_ping = time.time()

    def search(state: Tuple[int, ...], g: int, bound: int, blank_idx: int, prev_blank: int,
               path_moves: List[int]) -> Tuple[bool, int]:
        nonlocal nodes, last_ping

        if cancel.is_cancelled():
            raise RuntimeError("CANCELLED")

        h = pdb_heuristic(state)
        f = g + h
        if f > bound:
            return False, f
        if state == goal_t:
            return True, g

        nodes += 1
        now = time.time()
        if progress_cb and (now - last_ping) > 0.2:
            last_ping = now
            progress_cb(f"Suche… bound={bound} | Tiefe={g} | Knoten={nodes:,}", 0, 0)

        min_next = 10**9

        # Small ordering: try moves that reduce heuristic first (simple greedy ordering)
        # Compute candidate neighbor list with their resulting heuristic (cheap enough).
        cand = []
        for nb in NEIGHBORS[blank_idx]:
            if nb == prev_blank:
                continue
            moved_tile = state[nb]
            new_state = list(state)
            new_state[blank_idx], new_state[nb] = new_state[nb], new_state[blank_idx]
            new_t = tuple(new_state)
            cand.append((pdb_heuristic(new_t), nb, moved_tile, new_t))
        cand.sort(key=lambda x: x[0])

        for _, nb, moved_tile, new_t in cand:
            path_moves.append(moved_tile)
            found, t = search(new_t, g + 1, bound, nb, blank_idx, path_moves)
            if found:
                return True, t
            path_moves.pop()
            if t < min_next:
                min_next = t

        return False, min_next

    bound = pdb_heuristic(start_t)
    blank_idx = start_t.index(0)
    path: List[int] = []

    if progress_cb:
        progress_cb(f"Starte IDA*… initial bound={bound}", 0, 0)

    while True:
        if cancel.is_cancelled():
            raise RuntimeError("CANCELLED")

        if progress_cb:
            progress_cb(f"IDA* Iteration… bound={bound}", 0, 0)

        try:
            found, t = search(start_t, 0, bound, blank_idx, -1, path)
        except RuntimeError as e:
            if str(e) == "CANCELLED":
                raise
            raise

        if found:
            if progress_cb:
                progress_cb(f"Lösung gefunden! Züge={len(path)}", 0, 0)
            return path.copy()

        if t == 10**9:
            return None
        bound = t


# -----------------------------
# Worker Thread
# -----------------------------

class SolverWorker(QObject):
    progress = Signal(str)
    finished = Signal(object, str)  # moves (list or None), status string: "ok"|"cancelled"|"fail"

    def __init__(self, start_state: List[int]):
        super().__init__()
        self.start_state = start_state
        self.cancel_flag = CancelFlag()

    @Slot()
    def run(self):
        try:
            def pcb(msg, a=0, b=0):
                self.progress.emit(msg)

            moves = ida_star_solve_pdb(self.start_state, self.cancel_flag, progress_cb=pcb)
            if moves is None:
                self.finished.emit(None, "fail")
            else:
                self.finished.emit(moves, "ok")
        except RuntimeError as e:
            if str(e) == "CANCELLED":
                self.finished.emit(None, "cancelled")
            else:
                self.finished.emit(None, "fail")
        except Exception:
            self.finished.emit(None, "fail")

    def cancel(self):
        self.cancel_flag.cancel()


# -----------------------------
# GUI
# -----------------------------

class SlidingPuzzle(QWidget):
    TILE = 62
    GAP = 8
    PAD = 12
    ANIM_MS = 160
    PLAYBACK_GAP_MS = 40

    BASE_SIZE = QSize(420, 300)

    BTN_W = 110
    BTN_H = 32

    def __init__(self):
        super().__init__()
        self.setWindowTitle("4x4 Schiebe-Puzzel")

        self.resize(self.BASE_SIZE)
        self._base_size = QSize(self.BASE_SIZE)

        self.state: List[int] = GOAL.copy()
        self.initial_state: List[int] = self.state.copy()

        self.tiles: Dict[int, QPushButton] = {}
        self._animating = False
        self._auto_playing = False
        self._pending_moves: List[int] = []

        # solver thread state
        self._solver_thread: Optional[QThread] = None
        self._solver_worker: Optional[SolverWorker] = None
        self._solving = False

        self._image_mode = False
        self._base_image: Optional[QPixmap] = None
        self._tile_images: Dict[int, QPixmap] = {}

        self._build_ui()
        self._build_tiles()
        self._apply_tile_appearance()
        self._sync_tiles_to_state(animate=False)

        self.log_panel.setVisible(False)
        self.btn_log.setText("Log anzeigen")

        QTimer.singleShot(0, self._refresh_base_size)

    # ---------- UI ----------

    def _build_ui(self):
        outer = QHBoxLayout(self)

        left = QVBoxLayout()
        outer.addLayout(left, 1)

        title = QLabel("4×4 Schiebe-Puzzel")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 14, QFont.Bold))
        left.addWidget(title)

        self.board = QFrame()
        self.board.setObjectName("board")
        side = self.PAD * 2 + self.TILE * N + self.GAP * (N - 1)
        self.board.setFixedSize(side, side)
        self.board.setStyleSheet("QFrame#board { background: #1f2937; border-radius: 16px; }")
        left.addWidget(self.board, alignment=Qt.AlignCenter)

        controls = QVBoxLayout()
        left.addLayout(controls)

        # Ebene 0: Felder setzen
        r0 = QHBoxLayout()
        controls.addLayout(r0)
        r0.addStretch(1)
        r0.addWidget(QLabel("Felder setzen:"))
        self.input = QLineEdit(" ".join(map(str, GOAL)))
        self.input.setPlaceholderText("16 Zahlen 0–15, z.B. 1 2 3 ... 15 0")
        self.input.setMinimumWidth(230)
        r0.addWidget(self.input)
        r0.addStretch(1)

        # Ebene 1: Setzen + Mischen
        r1 = QHBoxLayout()
        controls.addLayout(r1)
        r1.addStretch(1)
        self.btn_set = QPushButton("Setzen")
        self.btn_set.clicked.connect(self.on_set_state)
        r1.addWidget(self.btn_set)

        self.btn_shuffle = QPushButton("Mischen")
        self.btn_shuffle.clicked.connect(self.on_shuffle)
        r1.addWidget(self.btn_shuffle)
        r1.addStretch(1)

        # Ebene 2: Auto lösen + Stop
        r2 = QHBoxLayout()
        controls.addLayout(r2)
        r2.addStretch(1)
        self.btn_solve = QPushButton("Auto lösen")
        self.btn_solve.clicked.connect(self.on_solve)
        r2.addWidget(self.btn_solve)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        r2.addWidget(self.btn_stop)
        r2.addStretch(1)

        # Ebene 3: Reset + Log
        r3 = QHBoxLayout()
        controls.addLayout(r3)
        r3.addStretch(1)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.on_reset)
        r3.addWidget(self.btn_reset)

        self.btn_log = QPushButton("Log anzeigen")
        self.btn_log.clicked.connect(self.toggle_log)
        r3.addWidget(self.btn_log)
        r3.addStretch(1)

        # Ebene 4: Bild laden + Bild löschen
        r4 = QHBoxLayout()
        controls.addLayout(r4)
        r4.addStretch(1)
        self.btn_img_load = QPushButton("Bild laden")
        self.btn_img_load.clicked.connect(self.on_load_image)
        r4.addWidget(self.btn_img_load)

        self.btn_img_clear = QPushButton("Bild löschen")
        self.btn_img_clear.clicked.connect(self.on_clear_image)
        self.btn_img_clear.setEnabled(False)
        r4.addWidget(self.btn_img_clear)
        r4.addStretch(1)

        self._set_buttons_equal_size([
            self.btn_set, self.btn_shuffle, self.btn_solve, self.btn_stop,
            self.btn_reset, self.btn_log, self.btn_img_load, self.btn_img_clear
        ])

        # Status + "Ladeanimation"
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        left.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        # Indeterminate / busy by default
        self.progress.setRange(0, 0)
        left.addWidget(self.progress)

        left.addStretch(1)

        # Log Panel
        self.log_panel = QFrame()
        self.log_panel.setObjectName("logpanel")
        self.log_panel.setStyleSheet("""
            QFrame#logpanel { background: #111827; border-radius: 12px; padding: 8px; }
            QLabel#logtitle { color: #e5e7eb; font-weight: 700; }
        """)
        self.log_panel.setFixedWidth(320)
        outer.addWidget(self.log_panel)

        lp = QVBoxLayout(self.log_panel)
        log_title = QLabel("Zug-Log")
        log_title.setObjectName("logtitle")
        lp.addWidget(log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #0b1220;
                color: #e5e7eb;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lp.addWidget(self.log_text, 1)

        self.btn_log_clear = QPushButton("Log leeren")
        self.btn_log_clear.clicked.connect(lambda: self.log_text.clear())
        self.btn_log_clear.setFixedSize(self.BTN_W, self.BTN_H)
        lp.addWidget(self.btn_log_clear)

    def _set_buttons_equal_size(self, buttons: List[QPushButton]):
        for b in buttons:
            b.setFixedSize(self.BTN_W, self.BTN_H)

    def _build_tiles(self):
        for val in range(1, 16):
            btn = QPushButton(str(val), self.board)
            btn.setObjectName("tile")
            btn.setFont(QFont("Arial", 14, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton#tile { background: #e5e7eb; border: none; border-radius: 12px; }
                QPushButton#tile:hover { background: #f3f4f6; }
                QPushButton#tile:pressed { background: #d1d5db; }
            """)
            btn.clicked.connect(lambda checked=False, v=val: self.on_tile_clicked(v))
            self.tiles[val] = btn

    # ---------- Helpers ----------

    def _refresh_base_size(self):
        was = self.log_panel.isVisible()
        self.log_panel.setVisible(False)
        self._base_size = QSize(self.BASE_SIZE)
        self.resize(self._base_size)
        self.log_panel.setVisible(was)

    def cell_rect(self, index: int) -> QRect:
        r, c = divmod(index, N)
        x = self.PAD + c * (self.TILE + self.GAP)
        y = self.PAD + r * (self.TILE + self.GAP)
        return QRect(x, y, self.TILE, self.TILE)

    def idx_to_rc(self, idx: int) -> Tuple[int, int]:
        r, c = divmod(idx, N)
        return (r + 1, c + 1)

    def _set_controls_enabled(self, enabled: bool):
        self.input.setEnabled(enabled)
        self.btn_set.setEnabled(enabled)
        self.btn_shuffle.setEnabled(enabled)
        self.btn_solve.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)
        self.btn_img_load.setEnabled(enabled)
        self.btn_img_clear.setEnabled(enabled and self._image_mode)

        for b in self.tiles.values():
            b.setEnabled(enabled)

        # Log toggle + clear can remain enabled
        self.btn_log.setEnabled(True)
        self.btn_log_clear.setEnabled(True)

    def _log(self, msg: str):
        self.log_text.append(msg)

    # ---------- Log / Window size ----------

    def toggle_log(self):
        vis = not self.log_panel.isVisible()
        if vis:
            self.log_panel.setVisible(True)
            self.btn_log.setText("Log verbergen")
            self.adjustSize()
        else:
            self.log_panel.setVisible(False)
            self.btn_log.setText("Log anzeigen")
            QTimer.singleShot(0, lambda: self.resize(self._base_size))

    # ---------- Image ----------

    def _board_inner_side(self) -> int:
        return self.TILE * N + self.GAP * (N - 1)

    def on_load_image(self):
        if self._animating or self._auto_playing or self._solving:
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Bild auswählen", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return

        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, "Fehler", "Konnte das Bild nicht laden.")
            return

        self._base_image = pm
        self._image_mode = True
        self.btn_img_clear.setEnabled(True)

        self._slice_image_into_tiles()
        self._apply_tile_appearance()
        self._log(f"--- BILD GELADEN: {path} ---")

    def on_clear_image(self):
        if self._animating or self._auto_playing or self._solving:
            return
        self._image_mode = False
        self._base_image = None
        self._tile_images.clear()
        self.btn_img_clear.setEnabled(False)

        self._apply_tile_appearance()
        self._log("--- BILD GELÖSCHT: Standardoptik ---")

    def _slice_image_into_tiles(self):
        if not self._base_image or self._base_image.isNull():
            return

        pm = self._base_image
        side = min(pm.width(), pm.height())
        x0 = (pm.width() - side) // 2
        y0 = (pm.height() - side) // 2
        sq = pm.copy(x0, y0, side, side)

        inner = self._board_inner_side()
        scaled = sq.scaled(inner, inner, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        self._tile_images.clear()
        for idx, val in enumerate(GOAL):
            if val == 0:
                continue
            r, c = divmod(idx, N)
            x = c * (self.TILE + self.GAP)
            y = r * (self.TILE + self.GAP)
            self._tile_images[val] = scaled.copy(x, y, self.TILE, self.TILE)

    def _apply_tile_appearance(self):
        for val, btn in self.tiles.items():
            if self._image_mode and val in self._tile_images:
                btn.setText("")
                btn.setIcon(QIcon(self._tile_images[val]))
                btn.setIconSize(QSize(self.TILE, self.TILE))
                btn.setStyleSheet("""
                    QPushButton#tile { background: transparent; border: none; border-radius: 12px; }
                    QPushButton#tile:hover { background: rgba(255,255,255,0.08); }
                    QPushButton#tile:pressed { background: rgba(0,0,0,0.10); }
                """)
            else:
                btn.setIcon(QIcon())
                btn.setText(str(val))
                btn.setStyleSheet("""
                    QPushButton#tile { background: #e5e7eb; border: none; border-radius: 12px; }
                    QPushButton#tile:hover { background: #f3f4f6; }
                    QPushButton#tile:pressed { background: #d1d5db; }
                """)

    # ---------- Rendering / Animation ----------

    def _sync_tiles_to_state(self, animate: bool):
        self.status.setText("✅ Zielzustand erreicht!" if self.state == GOAL else "")

        if not animate:
            for idx, val in enumerate(self.state):
                if val == 0:
                    continue
                self.tiles[val].setGeometry(self.cell_rect(idx))
            return

        self._animating = True
        self._set_controls_enabled(False)

        group = QParallelAnimationGroup(self)
        moved_any = False

        for idx, val in enumerate(self.state):
            if val == 0:
                continue
            btn = self.tiles[val]
            target = self.cell_rect(idx)
            if btn.geometry() == target:
                continue

            anim = QPropertyAnimation(btn, b"geometry")
            anim.setDuration(self.ANIM_MS)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(btn.geometry())
            anim.setEndValue(target)
            group.addAnimation(anim)
            moved_any = True

        def done():
            self._animating = False
            if not self._auto_playing and not self._solving:
                self._set_controls_enabled(True)
            self.status.setText("✅ Zielzustand erreicht!" if self.state == GOAL else "")

            if self._auto_playing:
                QTimer.singleShot(self.PLAYBACK_GAP_MS, self._play_next_move)

        if moved_any:
            group.finished.connect(done)
            group.start()
        else:
            done()

    # ---------- Moves ----------

    def _apply_move_by_tile_value(self, tile_value: int, from_auto: bool):
        if self._animating:
            return

        zero_idx = self.state.index(0)
        tile_idx = self.state.index(tile_value)
        if tile_idx not in NEIGHBORS[zero_idx]:
            return

        fr = self.idx_to_rc(tile_idx)
        to = self.idx_to_rc(zero_idx)
        self.state[zero_idx], self.state[tile_idx] = self.state[tile_idx], self.state[zero_idx]

        prefix = "AUTO" if from_auto else "USER"
        self._log(f"[{prefix}] {tile_value}  ({fr[0]},{fr[1]}) -> ({to[0]},{to[1]})")
        self._sync_tiles_to_state(animate=True)

    def on_tile_clicked(self, tile_value: int):
        if self._auto_playing or self._solving:
            return
        self._apply_move_by_tile_value(tile_value, from_auto=False)

    # ---------- Buttons ----------

    def on_set_state(self):
        if self._animating or self._auto_playing or self._solving:
            return

        vals = parse_state(self.input.text())
        if vals is None:
            QMessageBox.warning(self, "Ungültig", "Bitte genau 16 Zahlen 0–15 angeben (jede genau einmal).")
            return

        if not is_solvable_4x4(vals):
            res = QMessageBox.question(
                self, "Warnung: unlösbar",
                "Diese Ausgangslage ist (als 4×4) NICHT lösbar.\nTrotzdem setzen?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return

        self.state = vals
        self.initial_state = vals.copy()
        self._log(f"--- SET: {self.state} ---")
        self._sync_tiles_to_state(animate=True)

    def on_reset(self):
        if self._animating or self._auto_playing or self._solving:
            return
        self.state = self.initial_state.copy()
        self._log(f"--- RESET: {self.state} ---")
        self._sync_tiles_to_state(animate=True)

    def on_shuffle(self):
        if self._animating or self._auto_playing or self._solving:
            return

        self.state = GOAL.copy()
        zero_idx = self.state.index(0)
        last = None
        for _ in range(250):
            nbs = list(NEIGHBORS[zero_idx])
            if last is not None and last in nbs and len(nbs) > 1:
                nbs.remove(last)
            nxt = random.choice(nbs)
            self.state[zero_idx], self.state[nxt] = self.state[nxt], self.state[zero_idx]
            last = zero_idx
            zero_idx = nxt

        self.initial_state = self.state.copy()
        self.input.setText(" ".join(map(str, self.state)))
        self._log(f"--- SHUFFLE: {self.state} ---")
        self._sync_tiles_to_state(animate=True)

    # ----- Threaded solver -----

    def _start_solver_thread(self):
        self._solving = True
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # busy
        self.btn_stop.setEnabled(True)
        self.status.setText("🧠 Suche läuft… (du kannst Stop drücken)")
        self._log("--- SOLVER: gestartet ---")

        self._solver_thread = QThread(self)
        self._solver_worker = SolverWorker(self.state.copy())
        self._solver_worker.moveToThread(self._solver_thread)

        self._solver_thread.started.connect(self._solver_worker.run)
        self._solver_worker.progress.connect(self._on_solver_progress)
        self._solver_worker.finished.connect(self._on_solver_finished)

        # cleanup
        self._solver_worker.finished.connect(self._solver_thread.quit)
        self._solver_worker.finished.connect(self._solver_worker.deleteLater)
        self._solver_thread.finished.connect(self._solver_thread.deleteLater)

        self._solver_thread.start()

    @Slot(str)
    def _on_solver_progress(self, msg: str):
        self.status.setText(msg)

    @Slot(object, str)
    def _on_solver_finished(self, moves_obj, status: str):
        self.progress.setVisible(False)
        self._solving = False

        # thread objects get cleaned by signals already
        self._solver_thread = None
        self._solver_worker = None

        if status == "cancelled":
            self._log("--- SOLVER: abgebrochen ---")
            self.status.setText("⏹️ Suche abgebrochen.")
            self.btn_stop.setEnabled(False)
            if not self._animating and not self._auto_playing:
                self._set_controls_enabled(True)
            return

        if status != "ok" or moves_obj is None:
            self._log("--- SOLVER: keine Lösung / Fehler ---")
            QMessageBox.warning(
                self, "Keine Lösung",
                "Keine Lösung gefunden oder Fehler.\n"
                "Hinweis: Beim ersten Mal dauert das PDB-Erstellen; danach ist es schneller."
            )
            self.status.setText("")
            self.btn_stop.setEnabled(False)
            if not self._animating and not self._auto_playing:
                self._set_controls_enabled(True)
            return

        moves: List[int] = list(moves_obj)
        if len(moves) == 0:
            self._log("--- SOLVER: schon gelöst ---")
            self.status.setText("✅ Zielzustand erreicht!")
            self.btn_stop.setEnabled(False)
            self._set_controls_enabled(True)
            return

        self._log(f"--- AUTO SOLVE (PDB+IDA*): {len(moves)} Züge ---")
        self._pending_moves = moves
        self._auto_playing = True

        # Controls bleiben aus während Playback
        self.btn_stop.setEnabled(True)
        self._set_controls_enabled(False)
        self.status.setText(f"▶️ Auto-Lösung läuft … (noch {len(self._pending_moves)} Züge)")
        self._play_next_move()

    def on_solve(self):
        if self._animating or self._auto_playing or self._solving:
            return

        if not is_solvable_4x4(self.state):
            QMessageBox.warning(self, "Unlösbar", "Diese Ausgangslage ist unlösbar.")
            return

        # disable controls while solving
        self._set_controls_enabled(False)
        self.btn_stop.setEnabled(True)

        self._start_solver_thread()

    def _play_next_move(self):
        if not self._auto_playing or self._animating:
            return

        if not self._pending_moves:
            self._auto_playing = False
            self.btn_stop.setEnabled(False)
            self._set_controls_enabled(True)
            self.status.setText("✅ Auto-Lösung fertig!" if self.state == GOAL else "⏹️ Auto-Lösung beendet.")
            return

        nxt = self._pending_moves.pop(0)
        self.status.setText(f"▶️ Auto-Lösung läuft … (noch {len(self._pending_moves)} Züge)")
        self._apply_move_by_tile_value(nxt, from_auto=True)

    def on_stop(self):
        # If currently solving: cancel solver (real stop)
        if self._solving and self._solver_worker is not None:
            self._solver_worker.cancel()
            self.status.setText("⏹️ Stop… (breche Suche ab)")
            self._log("--- STOP: Suche wird abgebrochen ---")
            self.btn_stop.setEnabled(False)  # avoid spamming
            return

        # If currently playing: stop playback
        if self._auto_playing:
            self._auto_playing = False
            self._pending_moves = []
            self.btn_stop.setEnabled(False)
            if not self._animating:
                self._set_controls_enabled(True)
            self.status.setText("⏹️ Auto-Lösung gestoppt.")
            return

    # ---------- closeEvent: ensure thread stops cleanly ----------
    def closeEvent(self, event):
        try:
            if self._solving and self._solver_worker is not None:
                self._solver_worker.cancel()
            if self._solver_thread is not None:
                self._solver_thread.quit()
                self._solver_thread.wait(500)
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    w = SlidingPuzzle()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
