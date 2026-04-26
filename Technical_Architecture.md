# Technical Architecture

This document describes the end-to-end data flow of the BirdNET off-the-grid bird-sound detector — from the USB microphone on the Raspberry Pi through inference, persistence, and the Vue 3 dashboard. It also lists the major frameworks and libraries used at each layer.

---

## 1. High-level overview

The system is a single-host pipeline. A Raspberry Pi (powered by a battery + solar panel + WittyPi 4 Mini HAT for power sequencing) runs three Python services and an nginx-fronted Vue 3 frontend. All services run inside Docker on the Pi in production; the frontend container reverse-proxies API and WebSocket traffic to the backend container over an internal Docker bridge network.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Raspberry Pi (off-the-grid)                      │
│                                                                          │
│   USB mic ──► recorder.py ──► data/StreamData/*.wav ──► analyzer.py      │
│                                                              │           │
│                                                              ▼           │
│                                          TFLite inference (BirdNET 2.4)  │
│                                                              │           │
│                          ┌───────────────────────────────────┘           │
│                          ▼                                               │
│         data/detections/<date>/<species>/*.png + *.mp3                   │
│                          │                                               │
│                          ▼                                               │
│                    data/birds.db (SQLite)                                │
│                          │                                               │
│                          ▼                                               │
│                    api.py (FastAPI :7007)                                │
│                          │                                               │
│            ┌─────────────┴─────────────┐                                 │
│            ▼                           ▼                                 │
│      REST /api/*                    /ws (WebSocket)                      │
│            │                           │                                 │
│            └─────────────┬─────────────┘                                 │
│                          ▼                                               │
│                nginx :80 (frontend container)                            │
│                          │                                               │
│                          ▼                                               │
│                Vue 3 SPA (Dashboard, Setup, ScriptView)                  │
│                                                                          │
│   WittyPi 4 Mini ──I2C (/dev/i2c-1)──► api.py /api/health & /api/sync-time│
└──────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Browser on phone / laptop
                  (any device on the Pi's LAN)
```

---

## 2. Hardware layer

| Component | Purpose |
|---|---|
| Raspberry Pi (4 / 5) | Host for all services |
| WittyPi 4 Mini HAT | Power sequencing (scheduled on/off), real-time clock, voltage/current monitoring via I2C bus 1, address `0x08` |
| USB microphone | ALSA device, addressed as `plughw:1,0` by default (verify with `arecord -l`) |
| External battery + solar panel | Off-grid power source |

The WittyPi enforces a daily on/off schedule (set via `/api/schedule`) so the Pi only boots and runs during user-configured listening windows, conserving battery.

---

## 3. Audio capture — `backend/recorder.py`

The recorder is a thin loop around the ALSA `arecord` CLI. It reads `backend/config.yml` once at startup, then continuously shells out to `arecord` to produce 15-second mono WAVs at 48 kHz, S16_LE.

```
recorder.py loop:
    timestamp = now() → "YYYY-MM-DD-HH-MM-SS"
    arecord -D plughw:1,0 -f S16_LE -c 1 -r 48000 -d 15 -t wav \
            data/StreamData/<timestamp>.wav
    (on non-zero exit: log + sleep 5s, retry)
```

Key design choices:
- **Filename = timestamp.** The analyzer parses this back into a `datetime` so the per-chunk detection time is the actual capture time, not the time inference completes.
- **No buffering in Python.** `arecord` writes the WAV directly to disk; the recorder only orchestrates.
- **SIGINT/SIGTERM** flip a `shutdown` flag that breaks the loop cleanly so Docker / supervisord can stop it without leaving a half-written WAV.

Output: `data/StreamData/*.wav` — consumed and deleted by the analyzer.

---

## 4. Inference — `backend/analyzer.py`

The analyzer is the heart of the pipeline. It uses [`watchdog`](https://pypi.org/project/watchdog/) to observe `data/StreamData/`. When a new `.wav` arrives, it waits for the file size to stabilize (so it doesn't read a half-written file), loads it with `librosa` at 48 kHz mono, splits it into 3-second chunks, and runs each chunk through the BirdNET TFLite interpreter.

### TFLite backend selection

```python
try:    from ai_edge_litert.interpreter import Interpreter   # preferred
except: try:    from tflite_runtime.interpreter import Interpreter   # Pi fallback
        except: from tensorflow.lite.python.interpreter import Interpreter
```

`ai-edge-litert` may lack arm64 wheels on Pi OS; the Dockerfile therefore falls back to `tflite-runtime`. The analyzer picks whichever import succeeds at startup.

### Model I/O

| | Shape | Dtype | Meaning |
|---|---|---|---|
| Input | `[1, 144000]` | `float32` | 3 s of raw audio at 48 kHz |
| Output | `[1, 6522]` | `float32` | **Raw logits** — must pass through `_sigmoid` to get probabilities |

`_sigmoid(x) = 1 / (1 + exp(-clip(x, -15, 15)))` — the clip prevents overflow on extreme logits. Probabilities `≥ confidence_threshold` (default `0.8`) become candidate detections.

The label file `BirdNET_GLOBAL_6K_V2.4_Labels_en.txt` has 6522 lines formatted `Scientific name_Common Name`. The analyzer splits on the first `_` and stores both halves separately.

### Per-WAV flow

```
process_wav(path):
    1. wait for file size to stabilize (handles arecord still writing)
    2. librosa.load(path, sr=48000, mono=True)
    3. parse timestamp from filename
    4. split into 3 s chunks; pad/discard remainder by min_samples (1.5 s)
    5. for each chunk:
         a. interpreter.invoke()  → raw logits
         b. sigmoid → probabilities
         c. for every prob ≥ threshold:
              detection_tracker.track(...) → list of detections to persist
              for each: save_detection(...)  # PNG + MP3 + DB row
    6. unlink the WAV
```

### False-positive filter — `DetectionTracker`

A rolling time-window species counter (configured via `min_detection_count` and `detection_window_seconds`). A species must be detected **N** times within the window before any of its detections are saved. Once confirmed, subsequent detections for that species are saved immediately until the confirmation expires.

```
                         time →
species X detection 1 ─────► [pending, count=1]
species X detection 2 ─────► [pending, count=2 ≥ N=2]
                              │
                              ▼
                            CONFIRM and FLUSH all pending dets to disk + DB
species X detection 3 ─────► save immediately (still in window)
                            ⋯
                            (window_seconds elapses)
                            confirmation expires → cycle restarts
```

Set `min_detection_count: 1` in `config.yml` to disable filtering entirely.

### `save_detection`

For each confirmed detection the analyzer writes three artifacts:

1. **Spectrogram PNG** via `spectrogram.py` (matplotlib, dark theme) → `data/detections/<date>/<species>/<HH-MM-SS>_<conf>.png`
2. **MP3 clip** by writing a temp WAV with `soundfile`, then transcoding via `ffmpeg -q:a 6` → `<...>.mp3`
3. **SQLite row** via `database.insert_detection(...)` — relative paths only

---

## 5. Persistence — `backend/database.py`

Single SQLite database at `data/birds.db`. One table:

```sql
CREATE TABLE detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,    -- YYYY-MM-DD
    time            TEXT NOT NULL,    -- HH:MM:SS
    common_name     TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    confidence      REAL NOT NULL,    -- sigmoid probability
    file_path       TEXT NOT NULL,    -- relative PNG path
    audio_path      TEXT NOT NULL     -- relative MP3 path
);
CREATE INDEX idx_date    ON detections(date);
CREATE INDEX idx_species ON detections(scientific_name);
```

All writes go through `_execute_with_retry`, which retries up to 3 times with linear backoff on `OperationalError` / `DatabaseError`. This matters because `analyzer.py` and `api.py` both open the same SQLite file concurrently.

---

## 6. API server — `backend/api.py`

[FastAPI](https://fastapi.tiangolo.com/) on `0.0.0.0:7007`, served by `uvicorn`. CORS is wide open (`*`) because the frontend container's nginx is the only ingress in production.

### REST endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness + WittyPi power (Vin / Vout / Iout via I2C, or `null` when unavailable) |
| GET | `/api/recent?limit=N` | Latest N detections |
| GET | `/api/hourly?date=YYYY-MM-DD` | Detection counts grouped by hour |
| GET | `/api/overview` | Totals, unique species count, today/week counts, top 10 species |
| GET | `/api/detections?date=&species=&limit=` | Filtered list |
| GET | `/api/species` | All detected species with counts and last-seen date |
| GET | `/api/spectrogram/{date}/{species}/{filename}` | Serves PNG (path-traversal guarded) |
| GET | `/api/audio/{date}/{species}/{filename}` | Serves MP3 |
| GET | `/api/bird-image?species=` | Cache-first; on miss fetches Wikipedia thumbnail and caches to `data/bird_images/` |
| GET | `/api/setup-complete` | Whether `birdnet.wpi` schedule has been written |
| POST | `/api/sync-time` | Sets Pi system clock from browser ISO time, then `system_to_rtc` to WittyPi RTC |
| POST | `/api/schedule` | Writes `birdnet.wpi` + `schedule.wpi`, runs `runScript.sh` |
| POST | `/api/reset` | Wipes detections, StreamData, bird_images, DB, and schedule |

### WebSocket — `/ws`

A `ConnectionManager` tracks active sockets. A background `broadcast_loop` polls `database.get_recent(..., 1)` every 10 s; if the latest row's `id` differs from the last broadcast it pushes `{"type": "new_detection", "data": <row>}` to all connected clients.

### WittyPi I2C

`/api/health` reads six bytes at I2C address `0x08` (registers `0x01..0x06`) on bus 1 and returns:

```json
{ "status": "ok",
  "power": { "input_voltage": 12.34, "output_voltage": 5.10, "output_current": 0.62 } }
```

When `smbus2` isn't installed (local dev on macOS) or the I2C read fails, `power` is `null`.

### Process supervision

In Docker, `supervisord` runs `recorder`, `analyzer`, and `api` as three separate programs with autorestart. Locally, `backend/debug.sh start` does the same with plain `&` background processes and PID-file tracking.

---

## 7. Frontend — `frontend/`

Vue 3 (Options API) built with Vue CLI 5, styled with Tailwind v4 and IBM Plex fonts (self-hosted woff2). Vue Router with three routes:

| Route | Component | Purpose |
|---|---|---|
| `/` | `setupView.vue` | Initial setup: time sync + WittyPi schedule |
| `/scriptView` | `scriptView.vue` | Schedule editor |
| `/dashboard` | `Dashboard.vue` | Detections dashboard (Chart.js) |

### API client

`frontend/src/services/api.js` is an axios wrapper around an origin-relative `/api` base URL (overridable via `VUE_APP_API_URL` for local dev). `App.vue` opens the WebSocket at `ws://${window.location.host}/ws`.

In production both rely on the **frontend container's nginx** (`frontend/nginx.conf`) to reverse-proxy:

- `^~ /api/`  → `http://backend:7007`
- `/ws`       → `http://backend:7007` with `Upgrade: websocket` headers
- everything else → static SPA assets (long-cached, content-hashed filenames)

The backend port `7007` is **not** published to the host. Only port 80 (frontend nginx) is exposed.

### Health indicator

`HealthIndicator.vue` mounts in `App.vue` and renders fixed top-right on every route. Polls `GET /api/health` every 10 s and displays a green/red dot. Clicking expands a panel showing WittyPi voltage/current.

### Bird image resolution (Dashboard "latest observation" card)

```
1. Pixel-art lookup in services/birdImages.js          (common name → /birds/<slug>.<ext>)
2. GET /api/bird-image?species=<common name>           (Wikipedia thumbnail, cached on Pi)
3. /default_bird.svg  (on <img> error)
```

Pixel-art assets live in `frontend/public/birds/`. Regenerate the asset map with `python3 scripts/build_bird_images.py`. The `<img>` toggles `image-rendering: pixelated` when the URL starts with `/birds/`.

### Theme system

Monochrome cream/ink retro theme with canvas-based Bayer 4×4 ordered dithering for shadows and fills. `useDither.js` composable + `DitherShadow.vue` component render pixelated drop-shadows behind every `.d-card`. `DSelect.vue` is a custom dropdown that uses dithered hover fills instead of native `<select>`.

---

## 8. Containerization

```
                       docker-compose.yml
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│  birdnet-backend        │               │  birdnet-frontend       │
│  python:3.11-slim       │               │  node:20-alpine →       │
│  + ffmpeg, alsa, i2c    │               │      nginx:alpine       │
│  + supervisord          │               │                         │
│                         │               │  serves SPA + proxies   │
│  /dev/snd  (audio)      │               │  /api/* and /ws         │
│  /dev/i2c-1 (WittyPi)   │               │                         │
│  group_add: 29 (audio)  │               │  ports: 80:80           │
│             988 (i2c)   │               │                         │
│  cap_add: SYS_TIME      │◄──────────────┤  depends_on: backend    │
│                         │  birdnet-     │                         │
│  expose: 7007 (intern.) │  internal     │                         │
│                         │  bridge       │                         │
│  volumes:               │  network      │                         │
│   /home/pi/birdnet-data │               │                         │
│   /home/pi/wittypi      │               │                         │
│   /etc/localtime (ro)   │               │                         │
└─────────────────────────┘               └─────────────────────────┘
```

Why these specific Docker bits matter:
- **`/dev/snd`** — exposes ALSA so `arecord` inside the container can read the USB mic.
- **`/dev/i2c-1`** + **`group_add: 988`** — lets `smbus2` talk to the WittyPi without root.
- **`group_add: 29`** — Pi OS audio group GID; the container user joins it so ALSA permissions work.
- **`cap_add: SYS_TIME`** — required for `date -s` inside `/api/sync-time`.
- **`/home/pi/birdnet-data:/app/data`** — persists detections + DB across container restarts.
- **`/home/pi/wittypi`** mount — `api.py` shells out to `runScript.sh` and `utilities.sh` from the host's WittyPi install.
- The backend port `7007` is `expose`d (intra-network only), not `ports`-published; only the frontend nginx on `:80` is reachable from the host.

---

## 9. Frameworks & libraries summary

| Layer | Tech |
|---|---|
| Audio capture | ALSA `arecord` (subprocess), Python 3.11 |
| Audio loading | `librosa`, `soundfile` |
| Inference | `ai-edge-litert` (preferred) → `tflite-runtime` (Pi fallback) → `tensorflow.lite` |
| Spectrograms | `matplotlib` |
| File watching | `watchdog` |
| Database | `sqlite3` (stdlib) |
| HTTP API | `FastAPI` + `uvicorn[standard]` |
| WebSocket | `FastAPI` `WebSocket` |
| Config | `pyyaml` |
| WittyPi I2C | `smbus2` |
| Process supervision | `supervisord` (Docker) / plain shell (`debug.sh`) |
| Frontend framework | Vue 3 (Options API) |
| Routing | `vue-router` 4 |
| HTTP client | `axios` |
| Charts | `chart.js` + `chartjs-chart-matrix` |
| Icons | `@fortawesome/vue-fontawesome` |
| Styling | Tailwind v4, custom canvas-based Bayer dithering |
| Web server (prod) | `nginx:alpine` (reverse proxy + static SPA) |
| Build (frontend) | Vue CLI 5 (Webpack) on `node:20-alpine` |
| Container runtime | Docker + Docker Compose |
