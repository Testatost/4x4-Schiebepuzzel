# 4×4 Sliding Puzzle (15-Puzzle) – PySide6 + PDB Solver (QThread)

Ein 4×4 Schiebe-Puzzle (15-Puzzle) mit PySide6-GUI, Animationen, Log, Bildmodus und einem schnellen Solver:
**IDA\*** mit **Pattern Databases (PDB)** + Cache auf Datei, ausgeführt in einem **QThread**.  
Dadurch bleibt die GUI flüssig und der Solver kann „echt“ abgebrochen werden.

---

## Features

- ✅ 4×4 Schiebe-Puzzle (0 = leeres Feld)
- 🎞️ Schiebe-Animationen
- 🧩 Startzustand frei eingeben („Felder setzen“)
- 🔀 Mischen (über gültige Züge → immer lösbar)
- 🤖 Auto lösen:
  - **IDA\*** + **Pattern Database Heuristik** (additiv per cost-splitting)
  - **PDB Cache** wird in `pdb_cache/` gespeichert (nur beim ersten Mal wird gerechnet)
  - läuft in einem **QThread** → GUI bleibt responsiv
- 🛑 Echter Stop:
  - stoppt die Solver-Suche (Cancel-Flag)
  - stoppt auch die Wiedergabe (falls Lösung gerade abgespielt wird)
- 🧾 Log-Bereich mit Zugliste
- 🖼️ Bild laden: Kacheln werden aus einem Bild geschnitten
- 🧼 Bild löschen: zurück zur Standardoptik
- ⏳ Lade-/Arbeitsanzeige:
  - ProgressBar im „busy“ Modus + Status-Text (zeigt was gerade passiert)

---

## Requirements

- Python **3.10+** empfohlen
- PySide6

---

## Installation

```bash
cd <dein-ordner>

python -m venv .venv

# Aktivieren
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install PySide6
