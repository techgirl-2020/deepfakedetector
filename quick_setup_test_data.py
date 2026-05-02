import os
import shutil
from pathlib import Path

def quick_setup():
    print("⚡ Attempting quick setup using already extracted files...")
    
    # Path where kagglehub is extracting
    cache_base = Path(os.path.expanduser("~")) / ".cache" / "kagglehub" / "datasets" / "birdy654" / "cifake-real-and-ai-generated-synthetic-images"
    
    # Find the archive folder (it might be named '3' or something else)
    archive_folders = list(cache_base.glob("**/test"))
    if not archive_folders:
        print("❌ Could not find extracted 'test' folder yet. Please wait another minute and try again.")
        return

    src_path = archive_folders[0]
    dest_path = Path("test-data")
    
    # Categories to copy
    categories = {"REAL": "real", "FAKE": "fake"}
    sample_size = 50
    
    for src_cat, dest_cat in categories.items():
        src_dir = src_path / src_cat
        dest_dir = dest_path / dest_cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        images = list(src_dir.glob("*.jpg")) + list(src_dir.glob("*.png"))
        count = min(len(images), sample_size)
        
        if count == 0:
            print(f"⚠️ No images found in {src_cat} yet. Extraction is still working...")
            continue
            
        print(f"📦 Copying {count} images to {dest_cat}...")
        for img_path in images[:count]:
            shutil.copy(img_path, dest_dir / img_path.name)

    print(f"\n✨ Quick setup complete! You have images in 'test-data'.")
    print("👉 You can now run: python evaluate_confusion_matrix.py test-data --api-url http://localhost/ai/detect-fake")

if __name__ == "__main__":
    quick_setup()
