from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import torch
import io
from threading import Lock, Thread

from local_model import load_local_model
from facenet_pytorch import MTCNN


app = FastAPI(title="Deepfake Detector AI Service")

# -------------------------
# CONFIG
# -------------------------
MODEL_PATH = "model.pth"

# -------------------------
# GLOBALS
# -------------------------
local_bundle = None
model_loading = False
model_load_error = None
_model_lock = Lock()

# Face detector
mtcnn_detector = MTCNN(
    keep_all=False,
    select_largest=True
)


# -------------------------
# MODEL LOADER
# -------------------------
def ensure_model_loaded():
    global local_bundle, model_loading, model_load_error

    if local_bundle is not None:
        return

    with _model_lock:
        if local_bundle is not None:
            return

        model_loading = True

        try:
            print(f"Loading model from {MODEL_PATH}")
            local_bundle = load_local_model(MODEL_PATH)
            model_load_error = None
            print("Model loaded successfully!")

        except Exception as exc:
            model_load_error = str(exc)
            print(f"Model load failed: {model_load_error}")
            raise

        finally:
            model_loading = False


# -------------------------
# STARTUP
# -------------------------
@app.on_event("startup")
def startup_event():
    Thread(target=ensure_model_loaded, daemon=True).start()


# -------------------------
# HEALTH
# -------------------------
@app.get("/health")
def health():
    return {
        "status": "running",
        "model_ready": local_bundle is not None,
        "model_loading": model_loading,
        "model_error": model_load_error,
    }


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"message": "Deepfake AI Service Running"}
# -------------------------
# PREDICT
# -------------------------

@app.post("/detect-fake")
async def detect_fake(file: UploadFile = File(...)):
    try:
        ensure_model_loaded()

        if local_bundle is None:
            raise HTTPException(status_code=503, detail="Model not ready")

        ct = file.content_type or ""
        if ct and not ct.startswith("image/"):

            raise HTTPException(status_code=400, detail="File must be image")

        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        boxes, _ = mtcnn_detector.detect(image)

        if boxes is None or len(boxes) == 0:
            raise HTTPException(status_code=400, detail="No face detected")

        x1, y1, x2, y2 = [max(0, int(v)) for v in boxes[0]]
        image = image.crop((x1, y1, x2, y2))

        # Multi-crop inference
        scores = []
        width, height = image.size
        crops = [
            image,
            image.crop((10, 10, width - 10, height - 10)),
            image.crop((20, 20, width - 20, height - 20))
        ]

        for crop in crops:
            tensor = local_bundle.transform(crop).unsqueeze(0).to(local_bundle.device)
            with torch.no_grad():
                logits = local_bundle.model(tensor)
            s = torch.sigmoid(logits).item()
            scores.append(s)

        score = sum(scores) / len(scores)
        if score >= 0.97:
            prediction = "Possibly Real"
        elif score >= 0.85:
            prediction = "Needs Review"
        else:
            prediction = "Possibly Fake"
        return {
            "prediction": prediction,
            "confidence": round(float(score), 4)
        }
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))