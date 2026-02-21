"""FastAPI server for BirdNET detections."""

import logging
from pathlib import Path

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

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
