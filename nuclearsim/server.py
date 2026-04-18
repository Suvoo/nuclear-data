"""FastAPI server that wraps pipeline.run_pipeline with a web API.

Endpoints:
  POST /api/generate            start a job, return job_id
  GET  /api/status/{job_id}     poll status + logs + result
  GET  /api/scenarios           list scenarios for the UI
  GET  /api/video/{job_id}      stream mp4
  GET  /api/frame/{job_id}/{name}   stream a frame jpg
  GET  /api/download/{job_id}   stream a zip of everything
"""

from __future__ import annotations

import io
import os
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import pipeline
from scenarios import SCENARIO_LABELS, SCENARIOS, resolve_scenario

app = FastAPI(title="NuclearSim API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Job state (in-memory)
# ---------------------------------------------------------------------------

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
MAX_CONCURRENT_JOBS = 2
VALID_LIGHTING = {"optimal", "dim", "failed"}


def _running_count() -> int:
    return sum(1 for j in JOBS.values() if j.get("status") == "running")


def _progress_for_log(line: str, current: int) -> int:
    """Rough progress based on the step markers already printed by pipeline."""
    if line.startswith("[1/4]"):
        return max(current, 10)
    if line.startswith("  downloaded video:"):
        return max(current, 40)
    if line.startswith("[2/4]"):
        return max(current, 50)
    if line.startswith("[3/4]"):
        return max(current, 60)
    if line.startswith("  frame "):
        # Try to parse "  frame X/Y" and interpolate between 60 and 90.
        try:
            part = line.strip().split()[1]  # "X/Y"
            x, y = part.split("/")
            xi, yi = int(x), int(y)
            if yi > 0:
                return max(current, 60 + int(30 * xi / yi))
        except Exception:
            pass
        return current
    if line.startswith("[4/4]"):
        return max(current, 95)
    if line.startswith("=== NUCLEARSIM COMPLETE"):
        return 100
    return current


def _flatten_dataset_for_ui(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the fields the frontend renders without dumping the whole COCO."""
    images = dataset.get("images", [])
    anns = dataset.get("annotations", [])
    ann_by_image = {a["image_id"]: a for a in anns}
    frames = []
    for img in images:
        ann = ann_by_image.get(img["id"], {})
        attrs = ann.get("attributes", {}) if ann else {}
        frames.append(
            {
                "id": img["id"],
                "file_name": img["file_name"],
                "frame_number": img.get("frame_number"),
                "category_id": ann.get("category_id"),
                "severity": attrs.get("severity", 1),
                "defect_type": attrs.get("primary_threat", "normal"),
                "defect_detected": attrs.get("defect_detected", False),
                "recommended_action": attrs.get("recommended_action", "continue"),
                "location_in_frame": attrs.get("location_in_frame", ""),
                "confidence": attrs.get("confidence", 0.0),
                "defects": attrs.get("defects", []),
                "reasoning": attrs.get("reasoning", ""),
                "action_protocol": attrs.get("action_protocol", {}),
            }
        )
    return {
        "info": dataset.get("info", {}),
        "summary": dataset.get("summary", {}),
        "dataset_quality": dataset.get("dataset_quality", {}),
        "sim_to_real_assessment": dataset.get("sim_to_real_assessment", {}),
        "frames": frames,
    }


def _run_job(job_id: str, scenario: str, severity: int, lighting: str) -> None:
    job = JOBS[job_id]

    def on_log(line: str) -> None:
        with JOBS_LOCK:
            job["logs"].append(line)
            job["progress"] = _progress_for_log(line, job.get("progress", 0))

    try:
        dataset = pipeline.run_pipeline(
            scenario, severity=severity, on_log=on_log, lighting=lighting
        )
        ui_payload = _flatten_dataset_for_ui(dataset)
        canonical = resolve_scenario(scenario)
        raw_dataset = {k: v for k, v in dataset.items() if not k.startswith("_")}
        result = {
            "scenario": canonical,
            "scenario_label": SCENARIO_LABELS.get(canonical, canonical),
            "severity": severity,
            "lighting": lighting,
            "video_url": f"/api/video/{job_id}",
            "download_url": f"/api/download/{job_id}",
            "dataset_url": f"/api/dataset/{job_id}",
            "frame_url_prefix": f"/api/frame/{job_id}",
            "raw_dataset": raw_dataset,
            **ui_payload,
        }
        with JOBS_LOCK:
            job["status"] = "complete"
            job["progress"] = 100
            job["result"] = result
            job["video_path"] = dataset.get("_video_path")
            job["frames_dir"] = dataset.get("_frames_dir")
            job["dataset_path"] = dataset.get("_dataset_path")
    except Exception as e:  # noqa: BLE001
        with JOBS_LOCK:
            job["status"] = "failed"
            job["error"] = str(e)
            job["logs"].append(f"ERROR: {e}")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    scenario: str
    severity: int = Field(ge=1, le=5)
    lighting: str = "optimal"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/scenarios")
def list_scenarios():
    items = []
    seen = set()
    ordered = [
        "pipe_crack",
        "flooded_basement",
        "gauge_anomaly",
        "weld_inspection",
        "radiation_hotspot",
        "corridor_multiple_hazards",
    ]
    for key in ordered:
        if key in SCENARIOS and key not in seen:
            s = SCENARIOS[key]
            items.append(
                {
                    "key": key,
                    "label": SCENARIO_LABELS.get(key, key),
                    "task": s["task"],
                    "complexity": s.get("complexity", "single"),
                    "environment": s.get("environment"),
                }
            )
            seen.add(key)
    return {"scenarios": items}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    scenario_key = resolve_scenario(req.scenario)
    if scenario_key not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}")
    if req.lighting not in VALID_LIGHTING:
        raise HTTPException(
            400, f"Lighting must be one of {sorted(VALID_LIGHTING)}"
        )
    with JOBS_LOCK:
        if _running_count() >= MAX_CONCURRENT_JOBS:
            raise HTTPException(429, "Too many concurrent jobs; try again shortly.")
        job_id = uuid.uuid4().hex[:12]
        JOBS[job_id] = {
            "id": job_id,
            "status": "running",
            "progress": 0,
            "logs": [],
            "result": None,
            "error": None,
            "created_at": time.time(),
            "scenario": scenario_key,
            "severity": req.severity,
            "lighting": req.lighting,
        }

    t = threading.Thread(
        target=_run_job,
        args=(job_id, scenario_key, req.severity, req.lighting),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "logs": job["logs"],
        "result": job["result"],
        "error": job["error"],
    }


@app.get("/api/video/{job_id}")
def get_video(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "complete":
        raise HTTPException(404, "video not ready")
    video_path = job.get("video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(404, "video missing")
    return FileResponse(video_path, media_type="video/mp4")


@app.get("/api/frame/{job_id}/{name}")
def get_frame(job_id: str, name: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "complete":
        raise HTTPException(404, "frames not ready")
    frames_dir = job.get("frames_dir")
    if not frames_dir:
        raise HTTPException(404, "frames dir missing")
    # Prevent path traversal.
    safe_name = Path(name).name
    p = Path(frames_dir) / safe_name
    if not p.exists():
        raise HTTPException(404, "frame not found")
    return FileResponse(p, media_type="image/jpeg")


@app.get("/api/dataset/{job_id}")
def get_dataset(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "complete":
        raise HTTPException(404, "dataset not ready")
    dataset_path = job.get("dataset_path")
    if not dataset_path or not Path(dataset_path).exists():
        raise HTTPException(404, "dataset missing")
    filename = Path(dataset_path).name
    return FileResponse(
        dataset_path,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/download/{job_id}")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "complete":
        raise HTTPException(404, "not ready")
    video_path = job.get("video_path")
    frames_dir = job.get("frames_dir")
    dataset_path = job.get("dataset_path")
    scenario = job.get("scenario", "scenario")
    severity = job.get("severity", "x")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if video_path and Path(video_path).exists():
            zf.write(video_path, arcname="clip.mp4")
        if dataset_path and Path(dataset_path).exists():
            zf.write(dataset_path, arcname="dataset.json")
        if frames_dir and Path(frames_dir).exists():
            for p in sorted(Path(frames_dir).glob("*.jpg")):
                zf.write(p, arcname=f"frames/{p.name}")
    buf.seek(0)

    filename = f"nuclearsim_{scenario}_sev{severity}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/health")
def health():
    return {"ok": True, "jobs": len(JOBS), "running": _running_count()}


# ---------------------------------------------------------------------------
# Static frontend (built Vite output mounted at /)
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
