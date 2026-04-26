# Testing Audio

This guide is a future-reference checklist for verifying the USB microphone on the Raspberry Pi works correctly with the BirdNET pipeline. Use it whenever:

- Setting up a new Pi.
- Swapping or moving the USB microphone.
- Detections suddenly drop to zero or all WAVs look silent in the analyzer log (`rms ≈ 0`).
- Running outside Docker (native debug mode) and ALSA permissions need re-checking.

The backend captures audio via `arecord` (called from `recorder.py`) at **48 kHz, mono, S16_LE, 15-second clips**. Every test below mirrors those settings so what you verify here is exactly what the pipeline records.

---

## 1. Confirm the OS sees the mic

Plug the USB mic into the Pi and run:

```bash
arecord -l
```

Expected output (card number and name will vary by mic):

```
**** List of CAPTURE Hardware Devices ****
card 1: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

Note the **card** and **device** numbers (e.g. `card 1, device 0` → `plughw:1,0`). This must match `audio.device` in `backend/config.yml`.

If `arecord -l` shows `no soundcards found`:

- Re-seat the USB cable (try a different USB port — prefer USB 2.0 for low-power mics).
- Check `dmesg | tail -30` for USB enumeration errors.
- Confirm `alsa-utils` is installed: `sudo apt install -y alsa-utils`.

---

## 2. Confirm permissions

The user running `arecord` (your shell user, or the container user under Docker) needs to be in the `audio` group:

```bash
groups            # should include 'audio'
getent group audio
```

If `audio` is missing, add it and re-login:

```bash
sudo usermod -aG audio "$USER"
# log out and back in (or reboot)
```

For Docker, the equivalent is `group_add: ["29"]` in `docker-compose.yml` (verify GID with `getent group audio`).

---

## 3. Quick sanity record (5 seconds)

The fastest way to prove the mic is wired up:

```bash
arecord -D plughw:1,0 -f S16_LE -c 1 -r 48000 -d 5 -t wav /tmp/test.wav
```

You should see something like:

```
Recording WAVE '/tmp/test.wav' : Signed 16 bit Little Endian, Rate 48000 Hz, Mono
```

…and the command exits cleanly after 5 seconds.

Common errors and fixes:

| Error | Fix |
|---|---|
| `cannot open audio device plughw:1,0` | Wrong card number. Re-check `arecord -l` and update `-D`. |
| `Permission denied` on `/dev/snd/*` | User not in `audio` group. See section 2. |
| `Device or resource busy` | Another process owns the mic. Kill it: `sudo fuser -v /dev/snd/*`. |
| Records, but file is 44 bytes (header only) | The mic is being detected but not capturing samples. Try a different USB port; check `dmesg`. |

---

## 4. Confirm the recording actually contains signal

Recording without errors is necessary but not sufficient — a broken mic can produce a silent WAV. Check actual signal level:

### 4.1 Inspect the file

```bash
ls -lh /tmp/test.wav    # 5 s mono @ 48 kHz s16le ≈ 480 KB
file /tmp/test.wav      # → RIFF (little-endian) data, WAVE audio, ...
```

### 4.2 Read RMS with Python (matches what `analyzer.py` logs)

If the venv from `install.sh` is set up:

```bash
source ~/birdnet-venv/bin/activate
python - <<'PY'
import librosa, numpy as np
y, sr = librosa.load("/tmp/test.wav", sr=48000, mono=True)
print(f"sr={sr} samples={len(y)} duration={len(y)/sr:.2f}s")
print(f"min={y.min():.4f} max={y.max():.4f} rms={np.sqrt(np.mean(y**2)):.4f}")
PY
```

Interpretation:

- `rms` < `1e-6` → effectively silent. The analyzer logs `Audio appears to be silent (near-zero RMS) — skipping inference` for this case.
- `rms` in the `0.001 – 0.05` range → typical room ambience or quiet outdoor recording.
- `max` clipping at `±1.0` → input gain too high, expect distortion.
- A flat constant (`min == max`) → mic disconnected mid-record, or a dead channel.

### 4.3 Listen to it

If you have speakers / headphones on the Pi:

```bash
aplay -D plughw:0,0 /tmp/test.wav    # adjust card for your output device
```

Otherwise, copy the WAV to your laptop:

```bash
# from your laptop:
scp pi@<pi-ip>:/tmp/test.wav .
```

…and play it locally. You should hear ambient room noise; whisper near the mic during a fresh recording to confirm the signal level changes.

---

## 5. Test the exact recorder command (15 s clip)

The recorder uses these flags. Run them by hand once to make sure a full 15-second clip captures cleanly with no underruns:

```bash
arecord \
  -D plughw:1,0 \
  -f S16_LE \
  -c 1 \
  -r 48000 \
  -d 15 \
  -t wav \
  /tmp/test_15s.wav
```

Then re-check RMS with the snippet in 4.2. A 15 s mono 48 kHz s16le WAV should be ~1.4 MB.

If you see warnings like `overrun!!! (at least X.XXX ms long)` — the Pi couldn't drain the ALSA buffer fast enough. This is rarely a problem for a 1-channel 48 kHz capture but can occur under heavy CPU load. Stop other heavy services and retry.

---

## 6. Test inside the Docker container (production path)

Once the stack is up via `docker compose up -d`, exec into the backend container and repeat the test. This proves the device passthrough, group GID, and ALSA all work end-to-end:

```bash
docker compose exec backend bash

# inside the container:
arecord -l
arecord -D plughw:1,0 -f S16_LE -c 1 -r 48000 -d 5 -t wav /tmp/test.wav
ls -lh /tmp/test.wav
exit
```

Failure modes specific to Docker:

| Symptom | Cause |
|---|---|
| `cannot open audio device` inside container, but works on host | `/dev/snd` not passed through. Check `devices:` in `docker-compose.yml`. |
| `Permission denied` inside container | `audio` GID mismatch. Run `getent group audio` on the host and update `group_add:` in `docker-compose.yml`. |
| Works in `exec` shell but `recorder.py` fails | `recorder.py` is started by `supervisord` early — check `docker compose logs backend` for the actual stderr. |

---

## 7. Verify the recorder is producing files

In production, the recorder writes 15-second WAVs to `data/StreamData/` and the analyzer deletes them after processing. To watch the pipeline live:

```bash
# Docker: WAVs land in the host bind-mount
watch -n 1 'ls -lh /home/pi/birdnet-data/StreamData/'

# Native debug:
watch -n 1 'ls -lh ~/bird-off-the-grid/backend/data/StreamData/'
```

You should see new `.wav` files appear roughly every 15 seconds, then disappear within a few seconds as the analyzer processes and unlinks them. If files keep accumulating, the analyzer is stuck — check its log.

To inspect a recording without disrupting the pipeline, copy one out before it's deleted:

```bash
cp /home/pi/birdnet-data/StreamData/<latest>.wav /tmp/sample.wav
```

…and run the RMS check from section 4.2 against `/tmp/sample.wav`.

---

## 8. Test BirdNET inference end-to-end

The repo ships with reference clips for the major species under `backend/test/`. To prove the model + audio chain works on the Pi (independent of the live mic):

```bash
source ~/birdnet-venv/bin/activate
python backend/test/test_model.py
```

This loads each `.mp3` / `.ogg` test clip, runs it through the same TFLite pipeline as `analyzer.py`, and prints whether the expected species was detected. A passing run confirms the model file, label file, TFLite backend, and `librosa` are all functional — narrowing any remaining problem to the mic itself.

---

## 9. Quick-reference checklist

When something's wrong with audio, walk this list top-to-bottom:

- [ ] `arecord -l` shows the mic.
- [ ] `audio.device` in `backend/config.yml` matches `arecord -l`.
- [ ] User (or container user) is in the `audio` group.
- [ ] `arecord -D <device> -f S16_LE -c 1 -r 48000 -d 5 -t wav /tmp/test.wav` succeeds.
- [ ] `/tmp/test.wav` has non-trivial RMS (> 1e-3 in a normal room).
- [ ] WAVs appear in `data/StreamData/` every ~15 s.
- [ ] WAVs are removed within seconds of appearing (analyzer is processing).
- [ ] `python backend/test/test_model.py` detects the expected reference species.

If all of the above pass and detections still aren't surfacing, the issue is downstream of audio — check `confidence_threshold` and `min_detection_count` in `config.yml`, or read `Technical_Architecture.md` for the full pipeline.
