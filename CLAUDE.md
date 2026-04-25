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

# Debug mode — runs recorder, analyzer, and API directly (no Docker, no frontend)
# Use this to debug the frontend from a separate device pointed at the Pi's API
./backend/debug.sh start
./backend/debug.sh stop
./backend/debug.sh restart
# Logs written to backend/logs/{recorder,analyzer,api}.log

# Production — full stack via Docker Compose (from repo root)
docker compose up -d
docker compose down

# Full Pi install (sets up venv and system packages)
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
| `api.py` | FastAPI; serves detections, species lists, spectrogram PNGs, audio clips, and system health (including WittyPi power via I2C) from `data/` |
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

`frontend/src/services/api.js` uses an origin-relative `/api` base URL (overridable via `VUE_APP_API_URL`). `App.vue` opens its WebSocket at `ws://${window.location.host}/ws`. Both rely on the frontend container's nginx (`frontend/nginx.conf`) to proxy `/api/` and `/ws` to `backend:7007` over the internal Docker network — the backend port is not published to the host. For local dev outside Docker (e.g. `npm run serve` against a remote Pi), set `VUE_APP_API_URL` to the backend URL.

`HealthIndicator.vue` is mounted in `App.vue` and renders on all routes as a fixed top-right element (z-index 40). It polls `GET /api/health` every 10s, showing a green/red dot with Online/Offline text. Clicking toggles an expanded panel with WittyPi power metrics (Vin, Vout, Iout). The `/api/health` endpoint reads WittyPi I2C registers via `smbus2`; when unavailable (local dev) it returns `"power": null`.

### UI Theme

Monochrome retro theme (cream/ink) with IBM Plex fonts and Bayer 4×4 canvas-based dithered shadows. Color tokens are defined in `frontend/src/tailwind.css` under `@theme` and consumed via `bg-[var(--color-*)]` / `text-[var(--color-*)]` Tailwind classes. Key tokens:

- `--color-background` `#f0ece3` — paper (page background, set on `body`)
- `--color-card` `#f0ece3` / `--color-card-alt` `#e8e4db` — card surfaces (distinguished by border)
- `--color-primary` `#0a0a0a` — ink (buttons, accents)
- `--color-text` `#0a0a0a` / `--color-text-secondary` `#333333` / `--color-text-muted` `#888888` — text hierarchy
- `--color-border` `#0a0a0a` — solid black borders

Utility classes in `@layer utilities` in `tailwind.css`:
- `.d-card` — card with 1.5px ink border, 2px radius, `position: relative`
- `.d-btn` / `.d-btn.outline` — IBM Plex Mono uppercase button with hover/active translate
- `.d-input` — IBM Plex Mono styled input field
- `.d-section-label` — uppercase muted section heading with bottom border

Dither shadow system (canvas-based Bayer 4×4 ordered dithering):
- `frontend/src/composables/useDither.js` — `renderDitherShadow()` and `renderDitherFill()` draw pixel-pattern shadows/fills onto `<canvas>` elements
- `frontend/src/components/DitherShadow.vue` — drop-in component, place inside any `.d-card`; renders a canvas at `top:4px; left:2px; z-index:-1` behind the card. Uses `ResizeObserver` to auto-resize.
- `frontend/src/components/DSelect.vue` — custom dropdown with dithered hover fills, replaces native `<select>`

**Important**: The page background must be on `body` (not `#app`) so that the `z-index: -1` shadow canvases remain visible above the body background but below card content.

Fonts are self-hosted as woff2 files in `frontend/public/fonts/` (IBM Plex Mono + IBM Plex Sans, weights 400/500/700), loaded via `@font-face` in `index.html`. No external CDN dependency.

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

# False-positive filter: species must be detected N times within window to be saved
min_detection_count: 2        # set to 1 to disable filtering
detection_window_seconds: 300  # rolling window in seconds
```

All model paths in `config.yml` are relative to the `backend/` directory (i.e. `Path(__file__).parent`).

### False-positive filter

`analyzer.py` includes a `DetectionTracker` that buffers detections per species. A species must be detected `min_detection_count` times within `detection_window_seconds` before any detections are saved to disk/DB. Once confirmed, subsequent detections for that species are saved immediately until the window expires. Set `min_detection_count: 1` to disable filtering entirely.

### Pi deployment

`install.sh` sets up the Python venv (`~/birdnet-venv`), installs system packages, and verifies the model files. No systemd services are created. Use `debug.sh` for direct process management or Docker Compose for production. On the Pi, `ai-edge-litert` may not be available — the interpreter import falls back to `tflite_runtime` then `tensorflow.lite`.

## Important Notes
- The first commit is to main and thereafter all commits are to master branch 