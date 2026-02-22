"""FastAPI server for BirdNET detections."""

import asyncio
import json as _json
import logging
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [api] %(message)s")
logger = logging.getLogger(__name__)

config_path = Path(__file__).parent / "config.yml"
with open(config_path) as f:
    config = yaml.safe_load(f)

data_dir = Path(__file__).parent / config["data_dir"]

app = FastAPI(title="BirdNET API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db(str(data_dir))


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; accept client messages
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_loop():
    """Poll the DB every 10 s and push new detections to connected clients."""
    last_id = None
    while True:
        await asyncio.sleep(10)
        if manager.active:
            try:
                rows = database.get_recent(str(data_dir), 1)
                if rows and rows[0].get("id") != last_id:
                    last_id = rows[0]["id"]
                    await manager.broadcast({"type": "new_detection", "data": rows[0]})
            except Exception as exc:
                logger.warning("broadcast_loop error: %s", exc)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_loop())


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/recent")
def recent(limit: int = Query(10, ge=1, le=100)):
    return database.get_recent(str(data_dir), limit)


@app.get("/api/hourly")
def hourly(date: str = Query(None)):
    return database.get_by_hour(str(data_dir), date)


@app.get("/api/overview")
def overview():
    return database.get_overview(str(data_dir))


@app.get("/api/detections")
def detections(date: str = Query(None), species: str = Query(None),
               limit: int = Query(100, ge=1, le=1000)):
    return database.get_detections(str(data_dir), date, species, limit)


@app.get("/api/species")
def species():
    return database.get_species(str(data_dir))


@app.get("/api/spectrogram/{date}/{species}/{filename}")
def get_spectrogram(date: str, species: str, filename: str):
    file_path = data_dir / "detections" / date / species / filename
    if not file_path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    # Prevent path traversal
    if not file_path.resolve().is_relative_to(data_dir.resolve()):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return FileResponse(str(file_path), media_type="image/png")


@app.get("/api/audio/{date}/{species}/{filename}")
def get_audio(date: str, species: str, filename: str):
    file_path = data_dir / "detections" / date / species / filename
    if not file_path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    if not file_path.resolve().is_relative_to(data_dir.resolve()):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return FileResponse(str(file_path), media_type="audio/mpeg")


# ---------------------------------------------------------------------------
# WittyPi schedule endpoint
# ---------------------------------------------------------------------------

class ScheduleRequest(BaseModel):
    start_datetime: str   # ISO-8601 local datetime, e.g. "2024-03-01T05:00:00"
    end_datetime: str
    schedule_type: str    # "dawn_dusk" | "morning_afternoon" | "custom"
    on_time: str = None   # "HH:MM" — required for custom
    off_time: str = None  # "HH:MM" — required for custom


def _build_wpi_content(req: ScheduleRequest) -> str:
    """Generate WittyPi .wpi schedule file content."""
    try:
        start_dt = datetime.fromisoformat(req.start_datetime)
        end_dt = datetime.fromisoformat(req.end_datetime)
    except ValueError as exc:
        raise ValueError(f"Invalid datetime format: {exc}") from exc

    begin_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    if req.schedule_type == "dawn_dusk":
        begin_time = "05:00:00"
        cycle = "ON  H1\nOFF H12\nON  H1\nOFF H10"
    elif req.schedule_type == "morning_afternoon":
        begin_time = "08:00:00"
        cycle = "ON  H1\nOFF H7\nON  H1\nOFF H15"
    elif req.schedule_type == "custom":
        if not req.on_time or not req.off_time:
            raise ValueError("on_time and off_time are required for custom schedule")
        on_h, on_m = map(int, req.on_time.split(":"))
        off_h, off_m = map(int, req.off_time.split(":"))
        begin_time = f"{on_h:02d}:{on_m:02d}:00"
        on_dur = (off_h * 60 + off_m - on_h * 60 - on_m) % (24 * 60)
        off_dur = 24 * 60 - on_dur
        on_dur_h = max(1, round(on_dur / 60))
        off_dur_h = max(1, round(off_dur / 60))
        cycle = f"ON  H{on_dur_h}\nOFF H{off_dur_h}"
    else:
        raise ValueError(f"Unknown schedule_type: {req.schedule_type!r}")

    return (
        f"BEGIN {begin_date} {begin_time}\n"
        f"END   {end_date} 23:59:00\n"
        f"{cycle}\n"
    )


@app.post("/api/schedule")
def set_schedule(req: ScheduleRequest):
    try:
        wpi_content = _build_wpi_content(req)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    wittypi_cfg = config.get("wittypi", {})
    schedules_dir = Path(wittypi_cfg.get("schedules_dir", "/home/pi/wittypi/schedules"))
    run_script = wittypi_cfg.get("run_script", "/home/pi/wittypi/runScript.sh")

    try:
        schedules_dir.mkdir(parents=True, exist_ok=True)
        wpi_file = schedules_dir / "birdnet.wpi"
        wpi_file.write_text(wpi_content)
        logger.info("Wrote WittyPi schedule to %s", wpi_file)
    except OSError as exc:
        logger.error("Failed to write schedule file: %s", exc)
        return JSONResponse({"error": f"Failed to write schedule: {exc}"}, status_code=500)

    try:
        result = subprocess.run(
            ["sudo", run_script, "birdnet"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.error("runScript.sh stderr: %s", result.stderr)
            return JSONResponse(
                {"error": f"runScript.sh failed: {result.stderr.strip()}"},
                status_code=500
            )
        logger.info("runScript.sh stdout: %s", result.stdout)
    except FileNotFoundError:
        logger.warning("runScript.sh not found — schedule file written but not applied")
    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "runScript.sh timed out"}, status_code=500)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Setup-complete flag
# ---------------------------------------------------------------------------

@app.get("/api/setup-complete")
def setup_complete():
    """Return whether a WittyPi schedule has already been written."""
    wittypi_cfg = config.get("wittypi", {})
    schedules_dir = Path(wittypi_cfg.get("schedules_dir", "/home/pi/wittypi/schedules"))
    return {"complete": (schedules_dir / "birdnet.wpi").is_file()}


@app.post("/api/reset")
def reset_data():
    import shutil

    logger.info("=== /api/reset called ===")

    wittypi_cfg = config.get("wittypi", {})
    schedules_dir = Path(wittypi_cfg.get("schedules_dir", "/home/pi/wittypi/schedules"))
    wpi_file = schedules_dir / "birdnet.wpi"
    logger.info("data_dir=%s", data_dir)
    logger.info("schedules_dir=%s  exists=%s", schedules_dir, schedules_dir.exists())
    logger.info("wpi_file=%s  exists=%s", wpi_file, wpi_file.exists())

    errors = []

    for subdir in ["detections", "StreamData", "bird_images"]:
        target = data_dir / subdir
        logger.info("subdir %s  exists=%s", target, target.exists())
        if target.exists():
            try:
                shutil.rmtree(target)
                logger.info("deleted %s", target)
            except OSError as e:
                logger.error("failed to delete %s: %s", target, e)
                errors.append(str(e))
        try:
            target.mkdir(parents=True, exist_ok=True)
            logger.info("recreated %s", target)
        except OSError as e:
            logger.error("failed to recreate %s: %s", target, e)
            errors.append(str(e))

    db_file = data_dir / "birds.db"
    logger.info("db_file=%s  exists=%s", db_file, db_file.exists())
    if db_file.exists():
        try:
            db_file.unlink()
            logger.info("deleted %s", db_file)
        except OSError as e:
            logger.error("failed to delete %s: %s", db_file, e)
            errors.append(str(e))

    # Recreate the DB with an empty schema so live services don't hit "no such table"
    try:
        database.init_db(str(data_dir))
        logger.info("re-initialized empty database at %s", db_file)
    except Exception as e:
        logger.error("failed to reinitialize database: %s", e)
        errors.append(str(e))

    if wpi_file.exists():
        try:
            wpi_file.unlink()
            logger.info("deleted %s", wpi_file)
        except OSError as e:
            logger.error("failed to delete %s: %s", wpi_file, e)
            errors.append(str(e))

    if errors:
        logger.error("reset completed with errors: %s", errors)
        return JSONResponse({"error": "; ".join(errors)}, status_code=500)

    logger.info("reset completed successfully")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Bird image (cache-first, falls back to Wikipedia, then 404)
# ---------------------------------------------------------------------------

@app.get("/api/bird-image")
def get_bird_image(species: str = Query(...)):
    """Serve a cached bird photo; fetch from Wikipedia on first request."""
    safe_name = "".join(
        c if c.isalnum() or c in " -" else "_" for c in species
    ).replace(" ", "_")
    cache_dir = data_dir / "bird_images"
    cache_path = cache_dir / f"{safe_name}.jpg"

    if cache_path.is_file():
        return FileResponse(str(cache_path), media_type="image/jpeg")

    # Try Wikipedia thumbnail API
    try:
        params = urllib.parse.urlencode({
            "action": "query", "prop": "pageimages", "format": "json",
            "piprop": "thumbnail", "pithumbsize": "400",
            "titles": species, "origin": "*",
        })
        req = urllib.request.Request(
            f"https://en.wikipedia.org/w/api.php?{params}",
            headers={"User-Agent": "BirdNET-Pi/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = _json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        img_url = page.get("thumbnail", {}).get("source")

        if img_url:
            img_req = urllib.request.Request(
                img_url, headers={"User-Agent": "BirdNET-Pi/1.0"}
            )
            with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                img_data = img_resp.read()
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(img_data)
            logger.info("Cached bird image for %r → %s", species, cache_path.name)
            return FileResponse(str(cache_path), media_type="image/jpeg")
    except Exception as exc:
        logger.debug("Bird image fetch failed for %r: %s", species, exc)

    return JSONResponse({"error": "no image available"}, status_code=404)


def main():
    import uvicorn
    uvicorn.run(
        app,
        host=config["api"]["host"],
        port=config["api"]["port"],
        log_level="info",
    )


if __name__ == "__main__":
    main()
