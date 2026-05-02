import os
import shutil
import kagglehub
from pathlib import Path

def setup_test_data(sample_size=100):
    print("🚀 Downloading CIFAKE dataset from Kaggle...")
    # This will prompt for Kaggle credentials if not set
    try:
        path = kagglehub.dataset_download("birdy654/cifake-real-and-ai-generated-synthetic-images")
    except Exception as e:
        print(f"❌ Error downloading dataset: {e}")
        print("💡 Make sure you have kagglehub installed: pip install kagglehub")
        return

    print(f"✅ Dataset downloaded to: {path}")
    
    src_path = Path(path) / "test"
    dest_path = Path("test-data")
    
    # Categories to copy
    categories = {"REAL": "real", "FAKE": "fake"}
    
    for src_cat, dest_cat in categories.items():
        src_dir = src_path / src_cat
        dest_dir = dest_path / dest_cat
        
        # Ensure dest exists
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 Copying {sample_size} images from {src_cat} to {dest_cat}...")
        
        # Get list of images
        images = list(src_dir.glob("*.jpg")) + list(src_dir.glob("*.png"))
        
        # Copy a sample
        for i, img_path in enumerate(images[:sample_size]):
            shutil.copy(img_path, dest_dir / img_path.name)
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{sample_size}")

    print(f"\n✨ Done! Your 'test-data' folder is ready with {sample_size * 2} images.")
    print("👉 Run: python evaluate_confusion_matrix.py test-data --api-url http://localhost/ai/detect-fake")

if __name__ == "__main__":
    # Ensure kagglehub is installed
    try:
        import kagglehub
    except ImportError:
        print("Installing kagglehub...")
        os.system("pip install kagglehub")
        import kagglehub
        
    setup_test_data(sample_size=50) # 50 real + 50 fake = 100 total images
