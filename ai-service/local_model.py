from dataclasses import dataclass
import torch

from transformers import (
    ViTImageProcessor,
    AutoModelForImageClassification,
)

MODEL_NAME = "umm-maybe/AI-image-detector"


@dataclass
class LocalModelBundle:
    model: object
    transform: object
    id2label: dict
    device: str


def load_local_model(model_path: str = ""):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = ViTImageProcessor.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )

    model = AutoModelForImageClassification.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )

    model.to(device)
    model.eval()

    return LocalModelBundle(
        model=model,
        transform=processor,
        id2label=model.config.id2label,
        device=device
    )