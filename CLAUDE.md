# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

BirdNET is an off-the-grid Raspberry Pi bird-sound detector. The pi is powered by an external battery and solar panel setup along with a wittyPi 4 mini as a HAT to sequence startup-shutdown sequence to ensure the Pi runs at specific times. A USB microphone feeds continuous 15s WAV recordings into a TFLite inference pipeline that classifies bird species and stores detections in SQLite. A Vue 3 frontend dashboard displays results via a FastAPI backend. 

## Commands

### Backend (Python 3.9, venv at `~/birdnet-venv` on Pi / `backend/venv` locally)

```bash
# Activate venv (local dev)
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run test suite (from backend/) only to check if the tf model is able to classify birds properly
python test/test_model.py

# Run individual services manually
python backend/recorder.py    # captures WAV files → data/StreamData/
python backend/analyzer.py    # watches StreamData/, runs inference
python backend/api.py         # FastAPI on port 7007

# Start/stop all three services together (Pi)
./backend/run.sh start
./backend/run.sh stop
./backend/run.sh restart

# Full Pi install (sets up venv, systemd services, PulseAudio)
./backend/install.sh
```

### Frontend (Vue 3 / Vue CLI)

```bash
cd frontend
npm install
npm run serve    # dev server with hot-reload
npm run build    # production build
npm run lint     # ESLint
```

## Architecture

### Data flow

```
USB mic → recorder.py (arecord)
        → data/StreamData/<timestamp>.wav   (15s clips)
        → analyzer.py (watchdog)
        → TFLite inference (3s chunks)
        → data/detections/<date>/<species>/ (.png spectrogram + .mp3 clip)
        → data/birds.db (SQLite)
        → api.py (FastAPI :7007)
        → frontend Dashboard
```

### Backend modules

| File | Role |
|---|---|
| `recorder.py` | Shells out to `arecord` in a loop; writes timestamped WAVs to `data/StreamData/` |
| `analyzer.py` | `watchdog` observer on `StreamData/`; splits each WAV into 3s chunks, runs TFLite inference, applies sigmoid to logits, saves detections above threshold via `database.py` and `spectrogram.py`; deletes processed WAVs |
| `api.py` | FastAPI; serves detections, species lists, spectrogram PNGs, and audio clips from `data/` |
| `database.py` | SQLite wrapper (`data/birds.db`); all writes go through `_execute_with_retry` for busy-lock resilience |
| `spectrogram.py` | Matplotlib spectrogram PNG generator (dark theme, used at save time) |
| `config.yml` | Single source of truth for all paths, thresholds, audio device, and port |

### Model

- **Model file**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite`
- **Labels file**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt` (6522 scientific names, one per line, no common names)
- **Input**: `[1, 144000]` float32 — raw audio at 48 kHz for 3 s
- **Output**: `[1, 6522]` raw logits — **sigmoid must be applied** before comparing to `confidence_threshold` (done in `analyzer._sigmoid`)
- The label format is scientific name only (e.g. `Parus major`). The `common_name` DB column will mirror the scientific name until a lookup table is added.

### Frontend

Vue 3 (Options API) with Vue Router. Three routes/views:
- `/` → `setupView.vue` — connection/status display
- `/scriptView` → `scriptView.vue`
- `/dashboard` → `Dashboard.vue` — main detections dashboard using Chart.js

`frontend/src/services/api.js` hardcodes the Pi's IP (`192.168.1.203`) and port `7100`. Update this when the Pi's address changes. The app also opens a WebSocket to `ws://192.168.1.203:7100/ws` from `App.vue`.

### Key configuration (`backend/config.yml`)

```yaml
audio:
  device: "plughw:1,0"   # USB mic — verify with: arecord -l
  sample_rate: 48000
  chunk_duration: 3       # seconds per inference chunk

model:
  path: "model/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite"
  labels: "model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt"

confidence_threshold: 0.7   # sigmoid probability (0–1)
```

All model paths in `config.yml` are relative to the `backend/` directory (i.e. `Path(__file__).parent`).

### Pi deployment

`install.sh` creates three systemd services: `birdnet-recorder`, `birdnet-analyzer`, `birdnet-api`. The venv is at `~/birdnet-venv` (not inside the repo). On the Pi, `ai-edge-litert` may not be available — the interpreter import falls back to `tflite_runtime` then `tensorflow.lite`.
