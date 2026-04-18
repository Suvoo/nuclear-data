# NuclearSim

Synthetic training-data factory for nuclear inspection robots. Pick a scenario (e.g. "cracked pipe"), and the pipeline generates a fake video of it, slices it into frames, has a vision-language model label every frame, and packages everything into a COCO-format dataset you could use to train a real robot's perception model — complete with dataset-quality and sim-to-real scoring.

---

## End-to-end in one sentence

User picks scenario + severity + lighting → prompt is built → video API generates an MP4 → frames extracted → each frame sent to a vision model which returns strict JSON → JSON aggregated into a COCO dataset → dataset scored for quality and sim-to-real realism → everything zipped and shown in the browser.

---

## How it works, step by step

### 1. The prompt — why we build it

In `nuclearsim/pipeline.py → build_video_prompt()`:

```python
def build_video_prompt(scenario_key, severity, lighting="optimal"):
    scenario = SCENARIOS[scenario_key]
    descriptor = SEVERITY_DESCRIPTORS.get(scenario_key, {}).get(severity, "")
    lighting_mod = LIGHTING_MODIFIERS.get(lighting, "")
    parts = [scenario["prompt"], descriptor, lighting_mod]
    return " ".join(p for p in parts if p).strip()
```

A video-generation model only knows what to make if you describe it in words. We assemble three pieces into one prompt:

- **Scenario prompt** — the base scene (e.g. "inspection robot crawling inside a steel pipe…")
- **Severity descriptor** — how bad the defect should look (sev 1 = clean, sev 5 = catastrophic)
- **Lighting modifier** — `optimal` / `dim` / `failed` emergency lighting

That concatenated string is the "input spec" for the fake world we want.

### 2. Video generation — what actually comes back

`generate_video()` sends the prompt to either **IonRouter** or **Seedance** (two hosted video-gen APIs). Both are async:

1. Submit the job → get back a job ID.
2. Poll `/tasks/{id}` every 3 seconds until `status == "succeeded"`.
3. The response contains a `video_url`.
4. Download it and save as `outputs/{scenario}_sev{n}_clip.mp4`.

So what comes back is literally an **MP4 file** — a ~5-second 832×480 clip of the fake scene.

### 3. IonRouter — what it does

IonRouter is a **model router / gateway**. Instead of integrating OpenAI, Anthropic, Alibaba, etc. separately, you hit one API (`api.ionrouter.io/v1`) and pick the model via the `model` field. We use it for two things:

- `wan2.2-t2v-general` — text-to-video model (when provider = ionrouter)
- `qwen3-vl-8b` — vision-language model for frame annotation

Think of it as a universal adapter. Seedance is an optional alternative video provider we can route to directly.

### 4. Frames — chopping the video

`extract_frames()` uses OpenCV to step through the MP4 and save every 10th frame as a JPG, plus a base64 copy to hand to the vision model. From a ~49-frame clip that's ~5 frames — enough signal, cheap enough to annotate.

### 5. Why JSON format for annotations

For each frame we ask Qwen-VL: "look at this image, is there a defect?" The prompt (`_single_prompt` / `_compound_prompt`) ends with:

> Return ONLY a single JSON object. No markdown, no commentary, no code fences. The JSON must contain exactly these keys: `defect_detected`, `defect_type`, `severity`, `location_in_frame`, `recommended_action`, `confidence`.

Why JSON:

1. **Machine-readable** — we need to programmatically count defects, compute class balance, and build a COCO file. Free-form English ("looks like some rust maybe") is useless for that.
2. **Schema-enforced** — fields are fixed and values are constrained (severity 1–5, action must be one of 5 enums). Downstream code can trust the shape.
3. **Training-dataset compatibility** — COCO, the standard CV dataset format, *is* JSON. Our output slots right in.

After the model replies, `_strip_json_fence` + `json.loads` parse it, and `_normalize_single/_compound` coerce types and fill missing fields. If parsing fails we drop in a safe fallback instead of crashing.

### 6. Evaluation — two different scores

After all frames are annotated, we evaluate the dataset itself in two ways:

**(a) `compute_quality_metrics()` — is this dataset good enough to train on?**

- **Class balance score** — normalized entropy of defect-type distribution. 1.0 = perfectly balanced, 0.0 = single class (a degenerate classifier).
- **Severity coverage** — do we have examples across all 5 severity levels?
- **Mean VLM confidence** — did the annotator feel sure? <0.6 means unreliable labels.
- A dataset is flagged `production_ready` only if balance ≥ 0.5, ≥2 classes, all severities covered, and mean confidence ≥ 0.65.

**(b) `assess_sim_to_real()` — will a model trained on this fake data work on real footage?**

- **Realism score** = `mean_confidence − severity_penalty − compound_penalty`. Higher severity and multi-hazard scenes are harder to synthesize faithfully, so they lose points.
- **Risk factors** — per-environment known gaps (e.g. "synthetic pipe walls too clean; real ones have grime", "gauge numbers may be hallucinated").
- **Recommended augmentations** — Gaussian noise, brightness jitter, mixing in ≥20% real footage.

Both scores get baked into the final COCO `dataset.json` under `dataset_quality` and `sim_to_real_assessment`.

### 7. The web layer tying it together

- **`nuclearsim/server.py`** (FastAPI)
  - `POST /api/generate` — kicks off `run_pipeline` on a background thread, returns a `job_id`.
  - `GET /api/status/{job_id}` — frontend polls this every 1.5s for logs + progress.
  - `GET /api/video/{job_id}` / `/api/frame/...` / `/api/dataset/...` / `/api/download/...` — serve the MP4, individual frames, the JSON, or a zip of all three.
- **`nuclearsim/frontend/src/App.jsx`** (React + Vite)
  - Scenario dropdown, severity slider, lighting picker, Generate button.
  - Live terminal-style log while running.
  - Video player + frame grid + dataset summary when complete.

---

## Project layout

```
nuclearsim/
  pipeline.py        # prompt → video → frames → annotations → COCO dataset
  scenarios.py       # scenario definitions, severity descriptors, labels
  server.py          # FastAPI wrapper around the pipeline
  requirements.txt
  .env.example       # ION_API_KEY, SEEDANCE_API_KEY, VIDEO_PROVIDER
  outputs/           # generated mp4s, frames, dataset.json (gitignored)
  frontend/          # React + Vite UI
```

---

## Running locally

### Backend

```bash
cd nuclearsim
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then fill in ION_API_KEY (and optionally SEEDANCE_API_KEY)
python server.py             # starts on http://localhost:8000
```

Or run the pipeline directly from the CLI:

```bash
python pipeline.py list
python pipeline.py pipe_crack 4
python pipeline.py corridor_multiple_hazards 3
```

### Frontend

```bash
cd nuclearsim/frontend
npm install
npm run dev                  # http://localhost:5173
```

For production, `npm run build` outputs `frontend/dist/`, which `server.py` automatically mounts at `/`.

---

## Scenarios

Defined in `nuclearsim/scenarios.py`:

- `pipe_crack` — cracked pipe interior
- `flooded_basement` — water hazard in a basement
- `gauge_anomaly` — instrumentation reading out of range
- `weld_inspection` — weld-seam defects
- `radiation_hotspot` — elevated readings near a source
- `corridor_multiple_hazards` — compound multi-hazard scene (uses IEC 61513 priority ranking)

Severity is 1–5; lighting is `optimal` / `dim` / `failed`.

---

Built for Beta Hacks 2026.
