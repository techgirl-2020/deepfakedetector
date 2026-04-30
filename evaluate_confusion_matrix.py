import argparse
import csv
import mimetypes
from pathlib import Path

import requests


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
LABELS = ("real", "fake")


def iter_images(data_dir):
    for label in LABELS:
        label_dir = data_dir / label
        if not label_dir.exists():
            raise SystemExit(f"Missing folder: {label_dir}")

        for path in sorted(label_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                yield label, path


def predict(api_url, image_path):
    content_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    with image_path.open("rb") as image_file:
        response = requests.post(
            api_url,
            files={"file": (image_path.name, image_file, content_type)},
            timeout=120,
        )

    response.raise_for_status()
    payload = response.json()
    prediction = (payload.get("prediction") or payload.get("result") or "").lower()
    if prediction not in LABELS:
        raise ValueError(f"Unexpected prediction for {image_path}: {payload}")
    return prediction, payload


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the running deepfake API on real/fake folders."
    )
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Folder containing real/ and fake/ image subfolders.",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost/ai/detect-fake",
        help="Prediction endpoint to call.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional path to save per-image predictions.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    rows = []
    matrix = {
        "real": {"real": 0, "fake": 0},
        "fake": {"real": 0, "fake": 0},
    }

    images = list(iter_images(data_dir))
    if not images:
        raise SystemExit(f"No images found under {data_dir}")

    for index, (true_label, image_path) in enumerate(images, start=1):
        try:
            predicted_label, payload = predict(args.api_url, image_path)
            matrix[true_label][predicted_label] += 1
            rows.append(
                {
                    "path": str(image_path),
                    "true_label": true_label,
                    "predicted_label": predicted_label,
                    "confidence": payload.get("confidence"),
                    "real_prob": payload.get("real_prob"),
                    "fake_prob": payload.get("fake_prob"),
                    "correct": true_label == predicted_label,
                }
            )
            print(
                f"[{index}/{len(images)}] {image_path.name}: "
                f"true={true_label} predicted={predicted_label}"
            )
        except Exception as exc:
            rows.append(
                {
                    "path": str(image_path),
                    "true_label": true_label,
                    "predicted_label": "error",
                    "confidence": "",
                    "real_prob": "",
                    "fake_prob": "",
                    "correct": False,
                    "error": str(exc),
                }
            )
            print(f"[{index}/{len(images)}] {image_path.name}: ERROR {exc}")

    total = sum(matrix[actual][predicted] for actual in LABELS for predicted in LABELS)
    correct = matrix["real"]["real"] + matrix["fake"]["fake"]
    accuracy = safe_divide(correct, total)

    print("\nConfusion matrix")
    print("Rows=true, columns=predicted")
    print("             predicted_real  predicted_fake")
    print(f"true_real    {matrix['real']['real']:14d}  {matrix['real']['fake']:14d}")
    print(f"true_fake    {matrix['fake']['real']:14d}  {matrix['fake']['fake']:14d}")
    print(f"\nAccuracy: {accuracy:.4f} ({correct}/{total})")

    print("\nPer-class metrics")
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in LABELS if actual != label)
        fn = sum(matrix[label][predicted] for predicted in LABELS if predicted != label)
        precision = safe_divide(tp, tp + fp)
        recall = safe_divide(tp, tp + fn)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        support = sum(matrix[label].values())
        print(
            f"{label:>4}: precision={precision:.4f} "
            f"recall={recall:.4f} f1={f1:.4f} support={support}"
        )

    if args.csv:
        fieldnames = [
            "path",
            "true_label",
            "predicted_label",
            "confidence",
            "real_prob",
            "fake_prob",
            "correct",
            "error",
        ]
        with args.csv.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved predictions to {args.csv}")


if __name__ == "__main__":
    main()
