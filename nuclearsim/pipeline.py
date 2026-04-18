"""NuclearSim — synthetic training data generator for nuclear inspection robots.

Usage:
    python pipeline.py <scenario> [severity]
    python pipeline.py pipe_crack 4
    python pipeline.py corridor_multiple_hazards 3
    python pipeline.py list
"""

import base64
import json
import math
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv
from openai import OpenAI

from scenarios import (
    SCENARIOS,
    SEVERITY_DESCRIPTORS,
    SCENARIO_LABELS,
    resolve_scenario,
)

# ---------------------------------------------------------------------------
# Log callback (thread-local so each job gets its own sink)
# ---------------------------------------------------------------------------

_log_ctx = threading.local()


def set_log_callback(cb):
    """Install a per-thread log sink. Pass None to clear."""
    _log_ctx.cb = cb


def _log(msg: str) -> None:
    """Print to stdout and forward to the thread-local callback if any."""
    print(msg, flush=True)
    cb = getattr(_log_ctx, "cb", None)
    if cb is not None:
        try:
            cb(msg)
        except Exception:
            pass

ION_BASE_URL = "https://api.ionrouter.io/v1"
ION_VIDEO_MODEL = "wan2.2-t2v-general"
VISION_MODEL = "qwen3-vl-8b"

SEEDANCE_BASE_URL = os.environ.get(
    "SEEDANCE_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3"
)
SEEDANCE_MODEL = os.environ.get(
    "SEEDANCE_MODEL", "dreamina-seedance-2-0-fast-260128"
)

WIDTH = 832
HEIGHT = 480
NUM_FRAMES = 49
POLL_INTERVAL = 3
POLL_TIMEOUT = 300

OUTPUTS_DIR = Path(__file__).parent / "outputs"

CATEGORIES = [
    {"id": 0, "name": "normal"},
    {"id": 1, "name": "crack"},
    {"id": 2, "name": "corrosion"},
    {"id": 3, "name": "flood_hazard"},
    {"id": 4, "name": "gauge_anomaly"},
    {"id": 5, "name": "structural_damage"},
]
CATEGORY_ID = {c["name"]: c["id"] for c in CATEGORIES}

ACTION_PRIORITY = {
    "halt": 5,
    "alert_operator": 4,
    "flag": 3,
    "slow_down": 2,
    "continue": 1,
}

ACTION_PROTOCOLS = {
    "continue": {
        "description": "No action required. Robot continues patrol at normal speed.",
        "robot_behavior": "Maintain current velocity, log frame as clean.",
        "human_notification": None,
        "escalation_time": None,
    },
    "slow_down": {
        "description": "Potential anomaly. Reduce speed, increase sampling rate.",
        "robot_behavior": "Reduce velocity 50%, sample every 2 frames instead of 10.",
        "human_notification": None,
        "escalation_time": None,
    },
    "flag": {
        "description": "Anomaly confirmed. Log location, continue patrol, include in shift report.",
        "robot_behavior": "Record pose coordinates, increase local resolution, continue.",
        "human_notification": "End of shift report",
        "escalation_time": "24 hours",
    },
    "alert_operator": {
        "description": "Significant defect. Hold position and notify control room immediately.",
        "robot_behavior": "Halt movement, hold position, stream live feed to control room.",
        "human_notification": "Immediate — control room alert",
        "escalation_time": "Immediate",
    },
    "halt": {
        "description": "Critical hazard. Emergency stop. Human intervention required.",
        "robot_behavior": "Emergency stop, broadcast alarm, lock position for retrieval.",
        "human_notification": "Emergency — all personnel",
        "escalation_time": "Now",
    },
}

SEVERITY_LABELS = {
    1: "none",
    2: "minor",
    3: "moderate",
    4: "serious",
    5: "critical",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    here = Path(__file__).parent
    load_dotenv()
    load_dotenv(".env.local", override=False)
    load_dotenv(here / ".env", override=False)
    load_dotenv(here / ".env.local", override=False)
    load_dotenv(here.parent / ".env", override=False)
    load_dotenv(here.parent / ".env.local", override=False)

    provider = (os.getenv("VIDEO_PROVIDER") or "").strip().lower()
    seedance_key = os.getenv("SEEDANCE_API_KEY") or os.getenv("seedance_api_key")
    ion_key = os.getenv("ION_API_KEY")

    if not provider:
        provider = "seedance" if seedance_key else "ionrouter"

    if provider == "seedance":
        video_key = seedance_key
        if not video_key:
            print("Set SEEDANCE_API_KEY (or seedance_api_key) in .env.local")
            sys.exit(1)
    else:
        video_key = ion_key
        if not video_key:
            print("Set ION_API_KEY in .env")
            sys.exit(1)

    vision_key = ion_key or video_key
    if not ion_key:
        print("Warning: ION_API_KEY not set; vision annotation will likely fail.")

    client = OpenAI(api_key=vision_key, base_url=ION_BASE_URL)
    _log(f"  video provider: {provider}")
    return client, video_key, provider


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

LIGHTING_MODIFIERS = {
    "optimal": (
        "Steady, clean industrial lighting at full brightness. Well-lit scene, "
        "clear visibility, minimal shadow noise."
    ),
    "dim": (
        "Low-light conditions. The only illumination comes from partially "
        "failing emergency fluorescent tubes and the robot's mounted "
        "flashlight. Long shadows, high contrast, cold color temperature."
    ),
    "failed": (
        "Primary lighting has failed. Scene lit only by the robot's harsh "
        "forward flashlight beam cutting through darkness. Heavy shadows, "
        "deep blacks, occasional sparks from damaged electrical fixtures."
    ),
}


def build_video_prompt(
    scenario_key: str, severity: int, lighting: str = "optimal"
) -> str:
    scenario = SCENARIOS[scenario_key]
    descriptor = SEVERITY_DESCRIPTORS.get(scenario_key, {}).get(severity, "")
    lighting_mod = LIGHTING_MODIFIERS.get(lighting, "")
    parts = [scenario["prompt"], descriptor, lighting_mod]
    return " ".join(p for p in parts if p).strip()


def _poll_video(base_url: str, job_id: str, headers: dict) -> str:
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            raise RuntimeError(f"Polling timed out after {POLL_TIMEOUT}s")
        poll = requests.get(f"{base_url}/{job_id}", headers=headers, timeout=30)
        if poll.status_code >= 400:
            raise RuntimeError(
                f"Poll failed ({poll.status_code}): {poll.text[:300]}"
            )
        pdata = poll.json()
        status = pdata.get("status")
        if status == "succeeded":
            content = pdata.get("content") or {}
            output = pdata.get("output") or {}
            video_url = (
                content.get("video_url")
                or output.get("video_url")
                or pdata.get("video_url")
            )
            if not video_url:
                raise RuntimeError(f"No video_url in success response: {pdata}")
            return video_url
        if status in ("failed", "cancelled"):
            raise RuntimeError(f"Video generation {status}: {pdata}")
        _log(f"  ...status={status} ({int(time.time() - start)}s)")
        time.sleep(POLL_INTERVAL)


def _generate_video_ionrouter(prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": ION_VIDEO_MODEL,
        "prompt": prompt,
        "width": WIDTH,
        "height": HEIGHT,
        "num_frames": NUM_FRAMES,
    }
    resp = requests.post(
        f"{ION_BASE_URL}/video/generations", headers=headers, json=payload, timeout=30
    )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Video submit failed ({resp.status_code}): {resp.text[:300]}"
        )
    data = resp.json()
    job_id = data.get("id") or data.get("job_id")
    if not job_id:
        raise RuntimeError(f"No job id in submit response: {data}")
    _log(f"  submitted ionrouter job {job_id}; polling...")
    return _poll_video(f"{ION_BASE_URL}/video/generations", job_id, headers)


def _generate_video_seedance(prompt: str, api_key: str) -> str:  # noqa: E302
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    full_prompt = f"{prompt} --resolution 480p --ratio 16:9 --duration 5 --fps 24"
    payload = {
        "model": SEEDANCE_MODEL,
        "content": [{"type": "text", "text": full_prompt}],
    }
    url = f"{SEEDANCE_BASE_URL}/contents/generations/tasks"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Seedance submit failed ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    job_id = data.get("id") or data.get("task_id")
    if not job_id:
        raise RuntimeError(f"No task id in Seedance response: {data}")
    _log(f"  submitted seedance task {job_id}; polling...")
    return _poll_video(url, job_id, headers)


def generate_video(
    scenario_key: str,
    severity: int,
    api_key: str,
    provider: str,
    lighting: str = "optimal",
) -> tuple:
    prompt = build_video_prompt(scenario_key, severity, lighting=lighting)
    _log(f"  prompt: {prompt[:180]}{'...' if len(prompt) > 180 else ''}")

    if provider == "seedance":
        video_url = _generate_video_seedance(prompt, api_key)
    else:
        video_url = _generate_video_ionrouter(prompt, api_key)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    video_path = OUTPUTS_DIR / f"{scenario_key}_sev{severity}_clip.mp4"
    dl = requests.get(video_url, timeout=120)
    dl.raise_for_status()
    video_path.write_bytes(dl.content)
    _log(f"  downloaded video: {video_path} ({len(dl.content)} bytes)")
    return str(video_path), prompt


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------

def extract_frames(video_path: str, scenario_key: str, severity: int, every_n: int = 10):
    frames_dir = OUTPUTS_DIR / f"{scenario_key}_sev{severity}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    result = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % every_n == 0:
            ok2, buf = cv2.imencode(".jpg", frame)
            if not ok2:
                idx += 1
                continue
            jpg_bytes = buf.tobytes()
            frame_path = frames_dir / f"frame_{idx:03d}.jpg"
            frame_path.write_bytes(jpg_bytes)
            b64 = base64.b64encode(jpg_bytes).decode("ascii")
            result.append((idx, str(frame_path.name), b64))
        idx += 1
    cap.release()
    _log(f"  extracted {len(result)} frames (every {every_n}) from {idx} total")
    return result


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------

def _fallback_annotation(defect_type: str = "parse_error") -> dict:
    return {
        "defect_detected": False,
        "defect_type": defect_type,
        "severity": 1,
        "location_in_frame": "",
        "recommended_action": "continue",
        "confidence": 0.0,
        "defects": [],
        "primary_threat": defect_type,
        "reasoning": "Annotation parse failed; fallback applied.",
    }


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


_DEFECT_TYPES = (
    "normal, crack, corrosion, flood_hazard, gauge_anomaly, structural_damage"
)
_ACTIONS = "continue, slow_down, flag, alert_operator, halt"

_SEVERITY_RUBRIC = (
    "Severity scale (use exactly these definitions):\n"
    "  1 = normal / no defect visible.\n"
    "  2 = minor cosmetic issue; monitor only.\n"
    "  3 = moderate defect; flag for human review at end of shift.\n"
    "  4 = serious defect; alert the control room operator immediately.\n"
    "  5 = critical hazard; halt the robot and escalate to emergency response."
)

_ACTION_RUBRIC = (
    "Action scale (must be consistent with severity):\n"
    "  continue       -> severity 1.\n"
    "  slow_down      -> severity 2.\n"
    "  flag           -> severity 3.\n"
    "  alert_operator -> severity 4.\n"
    "  halt           -> severity 5."
)


def _single_prompt(scenario_key: str, severity_hint: int) -> str:
    scenario = SCENARIOS[scenario_key]
    return (
        "You are the onboard perception model for a nuclear-plant inspection "
        "robot. Your job is to look at one video frame and produce a "
        "structured defect annotation for a training dataset.\n\n"
        f"Context:\n"
        f"  scenario        : {scenario_key}\n"
        f"  environment     : {scenario['environment']}\n"
        f"  task            : {scenario['task']}\n"
        f"  intended severity (hint only, may differ from what you see): "
        f"{severity_hint}\n\n"
        f"Valid defect_type values: {_DEFECT_TYPES}.\n"
        f"Valid recommended_action values: {_ACTIONS}.\n\n"
        f"{_SEVERITY_RUBRIC}\n\n"
        f"{_ACTION_RUBRIC}\n\n"
        "Look carefully at the image. If nothing is wrong, report "
        "defect_type='normal' with severity=1 and action='continue'. Do not "
        "invent defects that are not visible. Be honest about confidence.\n\n"
        "Return ONLY a single JSON object. No markdown, no commentary, no "
        "code fences. The JSON must contain exactly these keys:\n"
        '  "defect_detected"    : boolean,\n'
        '  "defect_type"        : one of the valid defect types,\n'
        '  "severity"           : integer 1-5,\n'
        '  "location_in_frame"  : short natural-language location (e.g. '
        '"upper right, 2 o\'clock on pipe wall"),\n'
        '  "recommended_action" : one of the valid actions,\n'
        '  "confidence"         : float between 0.0 and 1.0.'
    )


def _compound_prompt(scenario_key: str, severity_hint: int) -> str:
    scenario = SCENARIOS[scenario_key]
    return (
        "You are the onboard perception model for a nuclear-plant inspection "
        "robot operating under IEC 61513 (the international standard for "
        "nuclear instrumentation, control, and safety prioritization). Your "
        "job is to look at one video frame that may contain MULTIPLE "
        "simultaneous hazards and produce a structured multi-defect "
        "annotation.\n\n"
        f"Context:\n"
        f"  scenario        : {scenario_key}\n"
        f"  environment     : {scenario['environment']}\n"
        f"  task            : {scenario['task']}\n"
        f"  intended severity (hint only): {severity_hint}\n\n"
        f"Valid defect_type values: {_DEFECT_TYPES}.\n"
        f"Valid recommended_action values: {_ACTIONS}.\n\n"
        f"{_SEVERITY_RUBRIC}\n\n"
        f"{_ACTION_RUBRIC}\n\n"
        "IEC 61513 priority ranking (highest priority first, use this to "
        "select primary_threat when multiple defects are present):\n"
        "  1. structural_damage (loss of structural integrity).\n"
        "  2. flood_hazard       (water near electrical / submerged hazards).\n"
        "  3. gauge_anomaly      (instrumentation out of safe range).\n"
        "  4. crack              (material defect, not yet failure).\n"
        "  5. corrosion          (long-term degradation).\n"
        "  6. normal             (no threat).\n\n"
        "Identify each distinct hazard visible in the frame. For each, "
        "record its type, severity, approximate location, and your "
        "confidence. Then pick the single primary_threat using the priority "
        "ranking above. The overall severity is the MAX severity across "
        "all detected defects. Choose recommended_action based on that "
        "overall severity per the action rubric above.\n\n"
        "Return ONLY a single JSON object. No markdown, no commentary, no "
        "code fences. The JSON must contain exactly these keys:\n"
        '  "defects"            : array of {"type": <defect_type>, '
        '"severity": <int 1-5>, "location": <string>, "confidence": '
        '<float 0-1>},\n'
        '  "primary_threat"     : one of the valid defect types (chosen by '
        "the IEC 61513 priority list above),\n"
        '  "severity"           : integer 1-5 (max across defects),\n'
        '  "recommended_action" : one of the valid actions,\n'
        '  "confidence"         : float 0.0-1.0 (overall),\n'
        '  "reasoning"          : one short sentence explaining why '
        "primary_threat was chosen, citing IEC 61513."
    )


def _normalize_single(obj: dict) -> dict:
    defect_type = str(obj.get("defect_type", "normal"))
    severity = int(obj.get("severity", 1) or 1)
    confidence = float(obj.get("confidence", 0.0) or 0.0)
    return {
        "defect_detected": bool(obj.get("defect_detected", defect_type != "normal")),
        "defect_type": defect_type,
        "severity": severity,
        "location_in_frame": str(obj.get("location_in_frame", "")),
        "recommended_action": str(obj.get("recommended_action", "continue")),
        "confidence": confidence,
        "defects": [
            {
                "type": defect_type,
                "severity": severity,
                "location": str(obj.get("location_in_frame", "")),
                "confidence": confidence,
            }
        ] if defect_type != "normal" else [],
        "primary_threat": defect_type,
        "reasoning": "",
    }


def _normalize_compound(obj: dict) -> dict:
    raw_defects = obj.get("defects") or []
    defects = []
    for d in raw_defects:
        if not isinstance(d, dict):
            continue
        defects.append(
            {
                "type": str(d.get("type", "normal")),
                "severity": int(d.get("severity", 1) or 1),
                "location": str(d.get("location", "")),
                "confidence": float(d.get("confidence", 0.0) or 0.0),
            }
        )
    primary = str(obj.get("primary_threat") or (defects[0]["type"] if defects else "normal"))
    severity = int(obj.get("severity") or (max((d["severity"] for d in defects), default=1)))
    confidence = float(obj.get("confidence", 0.0) or 0.0)
    primary_defect = next((d for d in defects if d["type"] == primary), None)
    return {
        "defect_detected": len(defects) > 0,
        "defect_type": primary,
        "severity": severity,
        "location_in_frame": primary_defect["location"] if primary_defect else "",
        "recommended_action": str(obj.get("recommended_action", "continue")),
        "confidence": confidence,
        "defects": defects,
        "primary_threat": primary,
        "reasoning": str(obj.get("reasoning", "")),
    }


def annotate_frame(
    client: OpenAI, frame_b64: str, scenario_key: str, severity_hint: int
) -> dict:
    scenario = SCENARIOS[scenario_key]
    is_compound = scenario.get("complexity") == "compound"
    prompt = (
        _compound_prompt(scenario_key, severity_hint)
        if is_compound
        else _single_prompt(scenario_key, severity_hint)
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
                },
            ],
        }
    ]

    def _call():
        return client.chat.completions.create(model=VISION_MODEL, messages=messages)

    try:
        resp = _call()
    except Exception as e:
        msg = str(e)
        if "429" in msg or "rate" in msg.lower():
            time.sleep(5)
            try:
                resp = _call()
            except Exception:
                return _fallback_annotation("rate_limited")
        else:
            return _fallback_annotation()

    try:
        text = resp.choices[0].message.content or ""
        text = _strip_json_fence(text)
        obj = json.loads(text)
    except Exception:
        return _fallback_annotation()

    try:
        return _normalize_compound(obj) if is_compound else _normalize_single(obj)
    except Exception:
        return _fallback_annotation()


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

def compute_quality_metrics(annotations: list) -> dict:
    """Assess dataset health: class balance, severity coverage, confidence."""
    total = len(annotations)
    if total == 0:
        return {"production_ready": False, "recommendations": ["No frames"]}

    # Class distribution uses the primary defect_type per frame.
    class_counts = {c["name"]: 0 for c in CATEGORIES}
    for a in annotations:
        t = a.get("defect_type", "normal")
        class_counts[t] = class_counts.get(t, 0) + 1

    non_zero_classes = [n for n, c in class_counts.items() if c > 0]

    # Normalized entropy as a simple balance proxy (1.0 = perfectly balanced
    # across classes that appear; 0.0 = single class).
    ps = [c / total for c in class_counts.values() if c > 0]
    entropy = -sum(p * math.log(p) for p in ps) if ps else 0.0
    max_entropy = math.log(len(ps)) if len(ps) > 1 else 1.0
    class_balance_score = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0

    severity_coverage = [0, 0, 0, 0, 0]
    for a in annotations:
        sev = int(a.get("severity", 1))
        if 1 <= sev <= 5:
            severity_coverage[sev - 1] += 1

    confidences = [float(a.get("confidence", 0.0)) for a in annotations]
    mean_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    low_conf_frames = sum(1 for c in confidences if c < 0.6)

    warnings = {}
    recommendations = []

    if class_balance_score < 0.5 and len(non_zero_classes) > 1:
        warnings["class_balance"] = (
            f"skewed distribution (score {class_balance_score}); "
            f"dominant: {max(class_counts, key=class_counts.get)}"
        )
        recommendations.append(
            "Generate additional clips targeting underrepresented defect classes."
        )
    if len(non_zero_classes) <= 1:
        warnings["class_balance"] = (
            f"only {len(non_zero_classes)} class present — dataset is single-class."
        )
        recommendations.append(
            "Add clips with different defect types to avoid a degenerate classifier."
        )

    uncovered_severities = [i + 1 for i, c in enumerate(severity_coverage) if c == 0]
    if uncovered_severities:
        warnings["severity_coverage"] = (
            f"severities {uncovered_severities} not represented."
        )
        for s in uncovered_severities:
            recommendations.append(
                f"Run a clip at severity {s} to cover the {SEVERITY_LABELS[s]} range."
            )

    if mean_conf < 0.6:
        warnings["confidence"] = (
            f"mean VLM confidence {mean_conf} is low — annotations unreliable."
        )
        recommendations.append(
            "Regenerate clip with a more distinctive severity descriptor or better lighting."
        )
    elif low_conf_frames > total * 0.3:
        warnings["confidence"] = (
            f"{low_conf_frames}/{total} frames have confidence < 0.6."
        )
        recommendations.append("Drop low-confidence frames before training.")

    production_ready = (
        class_balance_score >= 0.5
        and len(non_zero_classes) >= 2
        and not uncovered_severities
        and mean_conf >= 0.65
    )

    return {
        "class_counts": class_counts,
        "class_balance_score": class_balance_score,
        "severity_coverage": severity_coverage,
        "mean_confidence": mean_conf,
        "low_confidence_frames": low_conf_frames,
        "warnings": warnings or None,
        "production_ready": production_ready,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Sim-to-real assessment
# ---------------------------------------------------------------------------

SIM_TO_REAL_RISKS = {
    "pipe_interior_steel": [
        {
            "factor": "lighting_uniformity",
            "issue": "Generated flashlight is uniform; real crawler lights have hotspots and falloff.",
            "mitigation": "Add negative prompt 'uniform lighting'; add 'realistic flashlight falloff' positive.",
        },
        {
            "factor": "surface_texture",
            "issue": "Pipe walls may be too clean; real pipes show decades of grime, weld seams, paint chips.",
            "mitigation": "Augment prompt with 'dirty, aged, industrial grime, weld seams'.",
        },
        {
            "factor": "camera_motion",
            "issue": "Synthetic camera motion is smooth; real crawlers have vibration and jitter.",
            "mitigation": "Post-process frames with mild motion blur and random jitter.",
        },
    ],
    "basement_flooded": [
        {
            "factor": "water_clarity",
            "issue": "Generated water color and reflections are idealized; real floods have oil sheen and debris.",
            "mitigation": "Prompt for 'oil sheen, floating debris, murky particulates'.",
        },
        {
            "factor": "lighting_reflections",
            "issue": "Flickering light reflections are simplified.",
            "mitigation": "Apply random brightness +/- 20% per frame during training.",
        },
    ],
    "plant_corridor": [
        {
            "factor": "gauge_realism",
            "issue": "Gauge faces and numbering may render as plausible-but-wrong text (VLM may misread).",
            "mitigation": "Validate gauge readings against a rules-based OCR filter before training.",
        },
        {
            "factor": "lighting_uniformity",
            "issue": "Fluorescent lighting is too even; real corridors have shadow cycles.",
            "mitigation": "Augment with random gamma and local contrast variation.",
        },
    ],
    "plant_corridor_compound": [
        {
            "factor": "hazard_co_occurrence",
            "issue": "Synthetic compound hazards may be statistically unrealistic (too co-located, too simultaneous).",
            "mitigation": "Mix compound clips with single-hazard clips at 1:3 ratio during training.",
        },
        {
            "factor": "gauge_realism",
            "issue": "Gauge text may be hallucinated.",
            "mitigation": "Validate with rules-based OCR before training.",
        },
        {
            "factor": "camera_motion",
            "issue": "Motion is smooth; real robots jitter.",
            "mitigation": "Augment frames with motion blur and jitter.",
        },
    ],
}

GENERIC_AUGMENTATIONS = [
    "Add Gaussian noise (sigma 5-10) to frames before training.",
    "Random brightness/contrast variation ±20%.",
    "Mix with >=20% real inspection footage if available to close the sim-to-real gap.",
]


def assess_sim_to_real(scenario_key: str, severity: int, quality: dict) -> dict:
    scenario = SCENARIOS[scenario_key]
    env = scenario["environment"]
    risk_factors = SIM_TO_REAL_RISKS.get(env, [])

    # Realism heuristic: higher confidence and lower severity tend to be more
    # realistic (rare / extreme events are harder to synthesize faithfully).
    mean_conf = float(quality.get("mean_confidence", 0.5))
    severity_penalty = (severity - 1) * 0.05  # 0.0 at sev1, 0.2 at sev5
    compound_penalty = 0.1 if scenario.get("complexity") == "compound" else 0.0
    raw = mean_conf - severity_penalty - compound_penalty
    realism_score = round(max(0.0, min(1.0, raw)), 3)

    return {
        "overall_realism_score": realism_score,
        "severity": severity,
        "risk_factors": risk_factors,
        "recommended_augmentations": GENERIC_AUGMENTATIONS,
        "notes": (
            "Realism heuristic combines VLM confidence, severity penalty, "
            "and compound-scenario penalty; validate against held-out real "
            "footage when available."
        ),
    }


# ---------------------------------------------------------------------------
# COCO assembly
# ---------------------------------------------------------------------------

def build_coco_dataset(
    scenario_key: str,
    severity: int,
    video_path: str,
    video_prompt: str,
    frames_and_annotations: list,
) -> dict:
    scenario = SCENARIOS[scenario_key]
    now = datetime.now(timezone.utc).isoformat()

    images = []
    annotations = []
    defects_detected = 0
    max_severity = 1
    highest_action = "continue"
    highest_action_priority = 0

    flat_anns = [ann for _, _, ann in frames_and_annotations]

    for i, (frame_num, filename, ann) in enumerate(frames_and_annotations):
        images.append(
            {
                "id": i,
                "file_name": filename,
                "width": WIDTH,
                "height": HEIGHT,
                "frame_number": frame_num,
                "scenario": scenario_key,
                "environment": scenario["environment"],
                "intended_severity": severity,
            }
        )
        primary = ann.get("primary_threat") or ann.get("defect_type", "normal")
        cat_id = CATEGORY_ID.get(primary, 0)
        action = ann.get("recommended_action", "continue")
        annotations.append(
            {
                "id": i,
                "image_id": i,
                "category_id": cat_id,
                "bbox": [0, 0, WIDTH, HEIGHT],
                "area": WIDTH * HEIGHT,
                "iscrowd": 0,
                "attributes": {
                    "severity": int(ann.get("severity", 1)),
                    "location_in_frame": ann.get("location_in_frame", ""),
                    "recommended_action": action,
                    "action_protocol": ACTION_PROTOCOLS.get(action, ACTION_PROTOCOLS["continue"]),
                    "confidence": float(ann.get("confidence", 0.0)),
                    "defect_detected": bool(ann.get("defect_detected", False)),
                    "defects": ann.get("defects", []),
                    "primary_threat": primary,
                    "reasoning": ann.get("reasoning", ""),
                },
            }
        )
        if ann.get("defect_detected"):
            defects_detected += 1
        sev = int(ann.get("severity", 1))
        if sev > max_severity:
            max_severity = sev
        pri = ACTION_PRIORITY.get(action, 0)
        if pri > highest_action_priority:
            highest_action_priority = pri
            highest_action = action

    quality = compute_quality_metrics(flat_anns)
    s2r = assess_sim_to_real(scenario_key, severity, quality)

    dataset = {
        "info": {
            "description": "NuclearSim Synthetic Inspection Dataset",
            "version": "2.0",
            "scenario": scenario_key,
            "complexity": scenario.get("complexity", "single"),
            "intended_severity": severity,
            "severity_descriptor": SEVERITY_DESCRIPTORS.get(scenario_key, {}).get(severity, ""),
            "video_prompt": video_prompt,
            "generated_at": now,
        },
        "categories": CATEGORIES,
        "images": images,
        "annotations": annotations,
        "summary": {
            "total_frames": len(images),
            "defects_detected": defects_detected,
            "max_severity": max_severity,
            "highest_risk_action": highest_action,
            "highest_risk_protocol": ACTION_PROTOCOLS.get(
                highest_action, ACTION_PROTOCOLS["continue"]
            ),
        },
        "dataset_quality": quality,
        "sim_to_real_assessment": s2r,
    }

    out_path = OUTPUTS_DIR / f"{scenario_key}_sev{severity}_dataset.json"
    out_path.write_text(json.dumps(dataset, indent=2))
    _log(f"  wrote dataset: {out_path}")
    return dataset


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_pipeline(
    scenario_key: str,
    severity: int = 3,
    on_log=None,
    lighting: str = "optimal",
) -> dict:
    """Run the full pipeline. Returns the COCO dataset dict.

    If on_log is provided, every progress line is also delivered to it in
    addition to stdout. Raises on any pipeline failure.
    """
    if on_log is not None:
        set_log_callback(on_log)
    try:
        scenario_key = resolve_scenario(scenario_key)
        if scenario_key not in SCENARIOS:
            raise ValueError(
                f"Unknown scenario: {scenario_key}. "
                f"Available: {list(SCENARIOS.keys())}"
            )
        if severity not in (1, 2, 3, 4, 5):
            raise ValueError(f"Severity must be 1-5, got {severity}")

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        client, video_key, provider = load_config()

        _log(
            f"[1/4] Generating severity-{severity} video for "
            f"'{scenario_key}' (lighting={lighting})..."
        )
        video_path, video_prompt = generate_video(
            scenario_key, severity, video_key, provider, lighting=lighting
        )

        _log("[2/4] Extracting frames...")
        frames = extract_frames(video_path, scenario_key, severity, every_n=10)
        if not frames:
            raise RuntimeError("no frames extracted from video")

        is_compound = SCENARIOS[scenario_key].get("complexity") == "compound"
        mode = "compound multi-hazard" if is_compound else "single-defect"
        _log(
            f"[3/4] Annotating {len(frames)} frames with {VISION_MODEL} "
            f"({mode} mode)..."
        )
        annotated = []
        for i, (frame_num, filename, b64) in enumerate(frames):
            ann = annotate_frame(client, b64, scenario_key, severity)
            annotated.append((frame_num, filename, ann))
            if is_compound:
                defect_names = (
                    ",".join(d["type"] for d in ann.get("defects", [])) or "none"
                )
                _log(
                    f"  frame {i+1}/{len(frames)} (#{frame_num}): "
                    f"primary={ann.get('primary_threat')} "
                    f"defects=[{defect_names}] "
                    f"sev={ann['severity']} action={ann['recommended_action']}"
                )
            else:
                _log(
                    f"  frame {i+1}/{len(frames)} (#{frame_num}): "
                    f"{ann['defect_type']} sev={ann['severity']} "
                    f"action={ann['recommended_action']}"
                )

        _log("[4/4] Building COCO dataset + quality + sim-to-real...")
        dataset = build_coco_dataset(
            scenario_key, severity, video_path, video_prompt, annotated
        )
        dataset["_video_path"] = video_path
        dataset["_frames_dir"] = str(
            OUTPUTS_DIR / f"{scenario_key}_sev{severity}_frames"
        )
        dataset["_dataset_path"] = str(
            OUTPUTS_DIR / f"{scenario_key}_sev{severity}_dataset.json"
        )

        s = dataset["summary"]
        q = dataset["dataset_quality"]
        r = dataset["sim_to_real_assessment"]
        sev_max = s["max_severity"]
        proto = s["highest_risk_protocol"]

        _log("")
        _log("=== NUCLEARSIM COMPLETE ===")
        _log(f"Scenario:         {scenario_key} (severity {severity})")
        _log(f"Video:            {video_path}")
        _log(f"Frames analyzed:  {s['total_frames']}")
        _log(f"Defects found:    {s['defects_detected']}/{s['total_frames']} frames")
        _log(f"Max severity:     {sev_max} ({SEVERITY_LABELS.get(sev_max, '?')})")
        _log(f"Action needed:    {s['highest_risk_action']}")
        _log(f"  -> robot:       {proto['robot_behavior']}")
        _log(f"  -> notify:      {proto['human_notification'] or 'none'}")
        _log("")
        _log("--- Dataset QA ---")
        _log(f"Class balance:    {q['class_balance_score']} (1.0 = perfectly balanced)")
        _log(f"Mean confidence:  {q['mean_confidence']}")
        _log(f"Severity cover:   {q['severity_coverage']} (counts for sev 1..5)")
        _log(f"Production ready: {q['production_ready']}")
        if q.get("warnings"):
            for k, v in q["warnings"].items():
                _log(f"  ! {k}: {v}")
        if q.get("recommendations"):
            for rec in q["recommendations"][:3]:
                _log(f"  -> {rec}")
        _log("")
        _log("--- Sim-to-Real Assessment ---")
        _log(f"Realism score:    {r['overall_realism_score']} (1.0 = matches reality)")
        for rf in r["risk_factors"][:3]:
            _log(f"  ! {rf['factor']}: {rf['issue']}")

        return dataset
    finally:
        if on_log is not None:
            set_log_callback(None)


if __name__ == "__main__":
    args = sys.argv[1:]
    try:
        if not args:
            run_pipeline("pipe_crack", 3)
        elif args[0] == "list":
            print("Scenarios:")
            for k, v in SCENARIOS.items():
                print(f"  {k:30s} [{v.get('complexity','single')}] {v['task']}")
        else:
            scenario = args[0]
            severity = int(args[1]) if len(args) > 1 else 3
            run_pipeline(scenario, severity)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
