import numpy as np
import faiss
from pathlib import Path
import gc

# Paths
INPUT_EMBEDDINGS = Path("src/data/processed/recipe_suggestion/recipe_embeddings.npy")
OUTPUT_INDEX = Path("src/data/models/recipe_suggestion/recipe_index.faiss")

def create_index():
    if not INPUT_EMBEDDINGS.exists():
        print(f"❌ Error: Embeddings file not found at {INPUT_EMBEDDINGS}")
        return

    print(f"📥 Loading embeddings from {INPUT_EMBEDDINGS}...")
    # mmap_mode='r' allows us to read the file without loading it all into RAM at once if needed,
    # but for FAISS we usually need it in RAM. 
    # However, since we aren't loading the CSV, we have plenty of RAM now.
    embeddings = np.load(INPUT_EMBEDDINGS)
    print(f"✅ Loaded embeddings structure: {embeddings.shape}")
    print(f"   - Memory usage: {embeddings.nbytes / 1024**3:.2f} GB")

    print("🔍 Normalizing vectors (L2)...")
    faiss.normalize_L2(embeddings)

    print("🏗️  Building FAISS index (IndexFlatIP)...")
    # Inner Product (IP) on normalized vectors is equivalent to Cosine Similarity
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    
    print(f"💾 Saving index to {OUTPUT_INDEX}...")
    faiss.write_index(index, str(OUTPUT_INDEX))
    print("✅ Index saved successfully!")

if __name__ == "__main__":
    create_index()
