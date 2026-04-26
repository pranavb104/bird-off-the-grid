# Installation

This guide walks you through installing the BirdNET off-the-grid bird-sound detector on a Raspberry Pi from scratch — from `git clone` to a running detection pipeline with the dashboard reachable on your LAN.

There are two supported installation paths:

- **A. Docker (production / recommended)** — full stack via `docker compose`. Frontend on port 80, backend hidden behind nginx.
- **B. Native (debug / development)** — runs `recorder.py`, `analyzer.py`, and `api.py` directly in a Python venv. Useful when iterating on the frontend from a separate machine.

Pick one. They're mutually exclusive on the same Pi.

---

## 1. Hardware requirements

| Item | Recommended |
|---|---|
| Raspberry Pi | Pi 4 (4 GB+) or Pi 5 |
| Storage | 32 GB+ microSD (Class 10 / A2) |
| OS | Raspberry Pi OS (Bookworm, 64-bit) |
| USB microphone | Any ALSA-compatible USB mic |
| Power | 5 V / 3 A supply, **or** WittyPi 4 Mini HAT + battery + solar panel for off-grid operation |
| Network | Wi-Fi or Ethernet during install (the dashboard is served over LAN at runtime) |

Optional but assumed by this project: **WittyPi 4 Mini** HAT for power scheduling, RTC, and voltage/current telemetry over I2C. Without it, `/api/health` returns `"power": null` and the schedule endpoints have no effect.

---

## 2. Prepare the Raspberry Pi

### 2.1 Flash and boot

1. Flash **Raspberry Pi OS (64-bit, Bookworm)** with the Raspberry Pi Imager.
2. In the Imager's advanced options, set the hostname, enable SSH, set the username (default `pi`), and pre-configure Wi-Fi.
3. Boot the Pi and SSH in.

### 2.2 Update the system

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

### 2.3 Enable I2C (required for WittyPi)

```bash
sudo raspi-config
# → Interface Options → I2C → Enable → Finish → reboot
```

Verify after reboot:

```bash
ls /dev/i2c-1                    # should exist
sudo i2cdetect -y 1              # WittyPi 4 Mini appears at 0x08 and 0x69
```

### 2.4 Install the WittyPi 4 Mini software (skip if you don't have one)

Follow the vendor instructions from UUGear; the install script places everything under `/home/pi/wittypi/`. The backend expects:

- `/home/pi/wittypi/runScript.sh`
- `/home/pi/wittypi/utilities.sh`
- `/home/pi/wittypi/schedules/`

These paths are configurable in `backend/config.yml` under the `wittypi:` block.

### 2.5 Verify the USB microphone

Plug in the USB mic, then:

```bash
arecord -l
```

You should see something like:

```
card 1: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
```

The default in `backend/config.yml` is `audio.device: "plughw:1,0"` (card 1, device 0). If your mic shows up on a different card, edit `config.yml` accordingly. See `Testing_Audio.md` for a full mic verification walkthrough.

---

## 3. Clone the repository

```bash
cd ~
git clone <your-fork-or-this-repo-url> bird-off-the-grid
cd bird-off-the-grid
```

The first commit on this repo lives on `main`; ongoing work is on `master`. Make sure you're on the branch you want before installing.

---

## 4. Verify the BirdNET model files

The TFLite model and label files are committed under `backend/model/`:

```
backend/model/
├── BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite      # ~50 MB
├── BirdNET_GLOBAL_6K_V2.4_Labels_en.txt
└── BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt  # alias used by config.yml
```

If your clone is missing these (e.g. Git LFS not pulled), fetch them before continuing — `analyzer.py` exits hard at startup when the model file isn't found.

---

## 5. Configure the project

Open `backend/config.yml` and confirm:

```yaml
audio:
  device: "plughw:1,0"     # update to match `arecord -l`
  sample_rate: 48000
  record_duration: 15
  chunk_duration: 3

confidence_threshold: 0.8
min_detection_count: 2
detection_window_seconds: 300

api:
  host: "0.0.0.0"
  port: 7007

data_dir: "data"

wittypi:
  schedules_dir: "/home/pi/wittypi/schedules"
  run_script: "/home/pi/wittypi/runScript.sh"
```

Optionally set `latitude` / `longitude` for future location-based species filtering.

---

## Path A — Docker (production)

This is the standard deployment path. It runs the backend (recorder + analyzer + api under supervisord) and the frontend (nginx serving the built SPA + proxying `/api/*` and `/ws`) as two containers on an internal bridge network.

### A.1 Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
# Log out and back in for the group change to take effect
```

Verify:

```bash
docker --version
docker compose version
```

### A.2 Discover host GIDs (one-time)

`docker-compose.yml` adds the container user to `audio` (GID `29`) and `i2c` (GID `988`) groups so it can read `/dev/snd` and `/dev/i2c-1`. These GIDs are the defaults on Bookworm but can vary — verify on your Pi:

```bash
getent group audio    # e.g. audio:x:29:pi
getent group i2c      # e.g. i2c:x:988:pi
```

If the numbers differ, edit the `group_add:` block in `docker-compose.yml`.

### A.3 Create the data and WittyPi mount points

The compose file bind-mounts:

- `/home/pi/birdnet-data` → `/app/data` inside the backend container (detections + DB)
- `/home/pi/wittypi` → `/home/pi/wittypi` inside the backend container (schedules + scripts)

Make sure both exist:

```bash
mkdir -p /home/pi/birdnet-data
ls /home/pi/wittypi   # should exist if you installed WittyPi in step 2.4
```

### A.4 Build and start the stack

From the repo root:

```bash
docker compose up -d --build
```

First-time builds take ~10–15 minutes on a Pi 4 (the backend image installs `librosa`, `matplotlib`, etc., and the frontend image runs `npm ci && npm run build`).

Verify both containers are running:

```bash
docker compose ps
docker compose logs -f backend     # tail backend logs
docker compose logs -f frontend    # tail frontend logs
```

### A.5 Open the dashboard

From any device on the same LAN:

```
http://<pi-ip-or-hostname>/
```

Port 80 is the only published port. The backend is reachable only via the frontend nginx proxy — `/api/*` and `/ws` are forwarded internally to `backend:7007`.

Quick health check:

```bash
curl http://<pi-ip>/api/health
# → {"status":"ok","power":{"input_voltage":...,"output_voltage":...,"output_current":...}}
```

### A.6 Stopping / updating

```bash
docker compose down                   # stop
docker compose pull && docker compose up -d --build   # rebuild after a git pull
```

---

## Path B — Native install (debug / dev)

Use this when you want to iterate on the frontend from a separate machine, or when Docker is overkill. It does not start the frontend — the frontend runs locally on your dev box (`npm run serve`) pointed at the Pi's API.

### B.1 Run the install script

```bash
cd ~/bird-off-the-grid
./backend/install.sh
```

This script:

1. Installs system packages: `python3 python3-pip python3-venv ffmpeg libsndfile1 libasound2-dev alsa-utils`
2. Adds your user to the `audio` group (log out / back in to take effect)
3. Creates a Python venv at `~/birdnet-venv`
4. Installs `backend/requirements.txt` into that venv
5. Verifies the BirdNET model and label files exist
6. Creates `backend/data/StreamData/` and `backend/data/detections/`

Re-run it any time after changing `requirements.txt`.

### B.2 Notes on TFLite on Pi

`ai-edge-litert` may not have an arm64 wheel on Pi OS. If `pip install` fails for it, install `tflite-runtime` instead — `analyzer.py` falls through to it automatically:

```bash
source ~/birdnet-venv/bin/activate
pip install tflite-runtime
```

### B.3 Start the backend

```bash
./backend/debug.sh start
```

This runs `recorder.py`, `analyzer.py`, and `api.py` as background processes. Output goes to `backend/logs/{recorder,analyzer,api}.log`.

```bash
./backend/debug.sh stop      # stop all three
./backend/debug.sh restart   # stop + start
tail -f backend/logs/*.log
```

Sanity check:

```bash
curl http://<pi-ip>:7007/api/health
```

### B.4 Run the frontend (on your dev machine, not the Pi)

```bash
cd frontend
cp .env.example .env
# Edit .env so VUE_APP_API_URL and VUE_APP_WS_URL point at the Pi:
#   VUE_APP_API_URL=http://<pi-ip>:7007/api
#   VUE_APP_WS_URL=ws://<pi-ip>:7007/ws
npm install
npm run serve
```

Visit `http://localhost:8080`.

> Note: in the native debug path the API listens directly on `:7007` (no nginx proxy), so dev `.env` URLs include `:7007` and the explicit `/api` and `/ws` paths.

---

## 6. First-run setup in the dashboard

Whichever path you used, the first time you load the dashboard:

1. Go to `/` (the **Setup** view).
2. Click **Sync Time** — this calls `POST /api/sync-time` with your browser's clock, which sets the Pi system time and writes it to the WittyPi RTC.
3. Pick a schedule (`Dawn → Dusk`, `Morning → Afternoon`, or `Custom`) and submit. This writes `birdnet.wpi` and runs `runScript.sh`.
4. Navigate to `/dashboard` — detections will start appearing as the analyzer confirms species.

---

## 7. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `arecord: cannot open audio device plughw:1,0` | Wrong card number. Run `arecord -l` and update `audio.device` in `backend/config.yml`. |
| `analyzer` exits with `Model file NOT FOUND` | `backend/model/` is missing the `.tflite`. Re-pull the repo or fetch model files. |
| `/api/health` returns `"power": null` | `smbus2` not installed, I2C disabled, or no WittyPi attached. Check `i2cdetect -y 1`. |
| Permission denied on `/dev/snd` (Docker) | `audio` group GID mismatch. Run `getent group audio` and update `group_add` in `docker-compose.yml`. |
| Permission denied on `/dev/i2c-1` (Docker) | Same idea for the `i2c` group (GID `988` by default). |
| Frontend loads but says "Offline" | Backend not reachable. In Docker: `docker compose logs backend`. Native: `tail -f backend/logs/api.log`. |
| `ai-edge-litert` install fails on Pi | Expected — `pip install tflite-runtime` and re-run. The Dockerfile already handles this fallback automatically. |

For mic-specific verification, see `Testing_Audio.md`.
