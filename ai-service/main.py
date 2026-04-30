import io
import os
from pathlib import Path
from threading import Lock, Thread

import torch
from facenet_pytorch import MTCNN
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from local_model import load_local_model


"""
Deepfake Detector AI Service
---------------------------
This service provides an ensemble model for deepfake detection using:
1. SigLIP (Local Model) - Specialized in deepfake patterns.
2. CLIP (OpenAI) - Zero-shot detection for AI-generated artifacts.
"""

app = FastAPI(title="Deepfake Detector AI Service")

BASE_DIR = Path(__file__).resolve().parent
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Configuration Environment Variables ---
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "local").strip().lower()
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "model.pth")

CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32").strip()
CLIP_LOCAL_FILES_ONLY = os.getenv("CLIP_LOCAL_FILES_ONLY", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CLIP_REAL_PROMPT = os.getenv(
    "CLIP_REAL_PROMPT",
    "a real authentic photograph of a human face",
).strip()
CLIP_FAKE_PROMPT = os.getenv(
    "CLIP_FAKE_PROMPT",
    "an AI-generated, synthetic, or deepfake image of a human face",
).strip()


def float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


WEIGHT_V2 = float_env("WEIGHT_V2", 0.45)
WEIGHT_CLIP = float_env("WEIGHT_CLIP", 0.55)
ALLOW_DEGRADED_ENSEMBLE = os.getenv(
    "ALLOW_DEGRADED_ENSEMBLE",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
WARMUP_CLIP_ON_STARTUP = os.getenv(
    "WARMUP_CLIP_ON_STARTUP",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}


def resolve_model_path(model_path: str) -> str:
    path = Path(model_path)
    if path.is_absolute():
        return str(path)
    return str((BASE_DIR / path).resolve())


def clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_pair(real_prob: float, fake_prob: float) -> tuple[float, float]:
    real_prob = clamp_probability(real_prob)
    fake_prob = clamp_probability(fake_prob)
    total = real_prob + fake_prob
    if total <= 0:
        return 0.5, 0.5
    return real_prob / total, fake_prob / total


def score_payload(real_prob: float, fake_prob: float, model_name: str, backend: str) -> dict:
    real_prob, fake_prob = normalize_pair(real_prob, fake_prob)
    prediction = "fake" if fake_prob > real_prob else "real"
    confidence = max(real_prob, fake_prob)
    return {
        "real": round(real_prob, 4),
        "fake": round(fake_prob, 4),
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "model": model_name,
        "backend": backend,
    }


deepfake_bundle = None
deepfake_loading = False
deepfake_load_error = None
_deepfake_lock = Lock()

clip_processor = None
clip_model = None
clip_loading = False
clip_load_error = None
_clip_lock = Lock()

mtcnn_detector = MTCNN(
    keep_all=False,
    select_largest=True,
)


def ensure_deepfake_model_loaded():
    global deepfake_bundle, deepfake_loading, deepfake_load_error

    if deepfake_bundle is not None:
        return

    with _deepfake_lock:
        if deepfake_bundle is not None:
            return

        deepfake_loading = True

        try:
            if MODEL_BACKEND != "local":
                raise RuntimeError(
                    f"Unsupported MODEL_BACKEND '{MODEL_BACKEND}'. Expected 'local'."
                )

            resolved_model_path = resolve_model_path(LOCAL_MODEL_PATH)
            print(f"Loading local deepfake model from {resolved_model_path}")
            deepfake_bundle = load_local_model(resolved_model_path)
            deepfake_load_error = None
            print("Local deepfake model loaded successfully")

        except Exception as exc:
            deepfake_load_error = str(exc)
            print(f"Local deepfake model load failed: {deepfake_load_error}")
            raise

        finally:
            deepfake_loading = False


def ensure_clip_model_loaded():
    global clip_model, clip_processor, clip_loading, clip_load_error

    if clip_model is not None and clip_processor is not None:
        return

    with _clip_lock:
        if clip_model is not None and clip_processor is not None:
            return

        clip_loading = True

        try:
            print(f"Loading CLIP detector from {CLIP_MODEL_NAME}")
            clip_processor = CLIPProcessor.from_pretrained(
                CLIP_MODEL_NAME,
                local_files_only=CLIP_LOCAL_FILES_ONLY,
            )
            clip_model = CLIPModel.from_pretrained(
                CLIP_MODEL_NAME,
                local_files_only=CLIP_LOCAL_FILES_ONLY,
            )
            clip_model.eval()
            clip_model.to(DEVICE)
            clip_load_error = None
            print("CLIP detector loaded successfully")

        except Exception as exc:
            clip_load_error = str(exc)
            print(f"CLIP detector load failed: {clip_load_error}")
            raise

        finally:
            clip_loading = False


def safe_warmup(loader, name: str):
    try:
        loader()
    except Exception:
        print(f"{name} warmup skipped because the model is not available yet")


def crop_largest_face(image: Image.Image) -> Image.Image:
    boxes, _ = mtcnn_detector.detect(image)

    if boxes is None or len(boxes) == 0:
        raise HTTPException(status_code=400, detail="No face detected")

    x1, y1, x2, y2 = boxes[0]
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(image.width, int(x2))
    y2 = min(image.height, int(y2))

    if x2 <= x1 or y2 <= y1:
        raise HTTPException(status_code=400, detail="Invalid face crop")

    return image.crop((x1, y1, x2, y2))

def run_deepfake_v2(face_image):
    ensure_deepfake_model_loaded()

    if deepfake_bundle is None:
        raise RuntimeError("Deepfake model not ready")

    inputs = deepfake_bundle.transform(
        images=face_image,
        return_tensors="pt"
    )
    inputs = {
        k: v.to(deepfake_bundle.device)
        for k, v in inputs.items()
    }

    with torch.no_grad():
        outputs = deepfake_bundle.model(**inputs)

    probs = torch.softmax(outputs.logits, dim=1)[0]
    
    fake_prob = float(probs[0].item())
    real_prob = float(probs[1].item())

    return score_payload(
        real_prob=real_prob,
        fake_prob=fake_prob,
        model_name="SigLIP",
        backend="local_deepfake_v2",
    )

def run_clip_detector(image: Image.Image) -> dict:
    ensure_clip_model_loaded()

    if clip_model is None or clip_processor is None:
        raise RuntimeError("CLIP detector not ready")

    inputs = clip_processor(
        text=[CLIP_REAL_PROMPT, CLIP_FAKE_PROMPT],
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {
        key: value.to(DEVICE) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = clip_model(**inputs)

    probs = torch.softmax(outputs.logits_per_image, dim=1)[0]
    real_prob = float(probs[0].item())
    fake_prob = float(probs[1].item())
    return score_payload(
        real_prob=real_prob,
        fake_prob=fake_prob,
        model_name=CLIP_MODEL_NAME,
        backend="clip_zero_shot",
    )


def unavailable_score(model_name: str, backend: str, error: str) -> dict:
    return {
        "real": None,
        "fake": None,
        "prediction": None,
        "confidence": None,
        "model": model_name,
        "backend": backend,
        "status": "unavailable",
        "error": error,
    }


def build_ensemble_result(score_v2: dict | None, score_clip: dict | None) -> dict:
    """
    Combines scores from both detectors using a weighted average.
    If only one is available, falls back to that one.
    """
    if score_v2 is not None and score_clip is not None:
        # Weighted Ensemble Calculation
        # SigLIP (v2) + CLIP (zero-shot)
        real_prob = (score_v2["real"] * WEIGHT_V2) + (score_clip["real"] * WEIGHT_CLIP)
        fake_prob = (score_v2["fake"] * WEIGHT_V2) + (score_clip["fake"] * WEIGHT_CLIP)

        # Normalize to ensure they sum to 1.0
        total = real_prob + fake_prob
        if total > 0:
            real_prob /= total
            fake_prob /= total
        else:
            real_prob, fake_prob = 0.5, 0.5

        prediction = "fake" if fake_prob > real_prob else "real"
        confidence = max(real_prob, fake_prob)
        mode = "weighted_ensemble"
        label = f"ensemble:weighted({WEIGHT_V2}v2 + {WEIGHT_CLIP}clip)"
        ensemble_fake_prob = fake_prob
    elif score_v2 is not None:
        prediction = score_v2["prediction"]
        confidence = score_v2["confidence"]
        real_prob = score_v2["real"]
        fake_prob = score_v2["fake"]
        mode = "fallback"
        label = "fallback:deepfake_v2"
        ensemble_fake_prob = fake_prob
    elif score_clip is not None:
        prediction = score_clip["prediction"]
        confidence = score_clip["confidence"]
        real_prob = score_clip["real"]
        fake_prob = score_clip["fake"]
        mode = "fallback"
        label = "fallback:clip_detector"
        ensemble_fake_prob = fake_prob
    else:
        raise HTTPException(
            status_code=503,
            detail="No detectors are currently available",
        )

    return {
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "real_prob": round(real_prob, 4),
        "fake_prob": round(fake_prob, 4),
        "label": label,
        "ensemble_details": {
            "mode": mode,
            "weights": {"v2": WEIGHT_V2, "clip": WEIGHT_CLIP},
            "deepfake_model_score": score_v2
            if score_v2 is not None
            else unavailable_score(
                model_name=Path(resolve_model_path(LOCAL_MODEL_PATH)).name,
                backend="local_deepfake_v2",
                error=deepfake_load_error or "Model unavailable",
            ),
            "ai_generator_model_score": score_clip
            if score_clip is not None
            else unavailable_score(
                model_name=CLIP_MODEL_NAME,
                backend="clip_zero_shot",
                error=clip_load_error or "Model unavailable",
            ),
            "ensemble_fake_probability": round(ensemble_fake_prob, 4),
        },
    }


@app.on_event("startup")
def startup_event():
    Thread(
        target=lambda: safe_warmup(ensure_deepfake_model_loaded, "deepfake model"),
        daemon=True,
    ).start()

    if WARMUP_CLIP_ON_STARTUP:
        Thread(
            target=lambda: safe_warmup(ensure_clip_model_loaded, "CLIP detector"),
            daemon=True,
        ).start()


@app.get("/")
def root():
    return {
        "message": "AI Service Running",
        "backend": MODEL_BACKEND,
        "ensemble_enabled": True,
    }


@app.get("/health")
def health():
    return {
        "status": "running",
        "device": DEVICE,
        "ensemble": {
            "weights": {
                "deepfake_v2": WEIGHT_V2,
                "clip_detector": WEIGHT_CLIP,
            },
            "allow_degraded": ALLOW_DEGRADED_ENSEMBLE,
        },
        "deepfake_model": {
            "backend": MODEL_BACKEND,
            "model_path": resolve_model_path(LOCAL_MODEL_PATH),
            "ready": deepfake_bundle is not None,
            "loading": deepfake_loading,
            "error": deepfake_load_error,
        },
        "clip_model": {
            "model_name": CLIP_MODEL_NAME,
            "local_files_only": CLIP_LOCAL_FILES_ONLY,
            "ready": clip_model is not None and clip_processor is not None,
            "loading": clip_loading,
            "error": clip_load_error,
        },
    }


@app.post("/detect-fake")
async def detect_fake(file: UploadFile = File(...)):
    """
    Main detection endpoint.
    Processes an uploaded image through:
    1. MTCNN Face detection and cropping.
    2. SigLIP deepfake classification.
    3. CLIP zero-shot classification.
    Returns an ensemble result (fallback mode).
    """
    try:
        content_type = file.content_type or ""
        if content_type and not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        face_image = crop_largest_face(image)

        score_v2 = None
        score_clip = None
        deepfake_error = None
        clip_error = None

        try:
            score_v2 = run_deepfake_v2(face_image)
        except Exception as exc:
            deepfake_error = str(exc)
            print(f"Deepfake v2 inference failed: {deepfake_error}")

        try:
            score_clip = run_clip_detector(image)
        except Exception as exc:
            clip_error = str(exc)
            print(f"CLIP detector inference failed: {clip_error}")

        if score_v2 is None and deepfake_error is not None:
            global deepfake_load_error
            deepfake_load_error = deepfake_error

        if score_clip is None and clip_error is not None:
            global clip_load_error
            clip_load_error = clip_error

        return build_ensemble_result(score_v2=score_v2, score_clip=score_clip)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
