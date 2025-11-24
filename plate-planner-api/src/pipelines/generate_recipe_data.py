"""
Generate recipe embeddings and metadata from RecipeNLG dataset.
"""
import ast
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

# Paths
RAW_DATA = Path("src/data/raw/RecipeNLG_dataset.csv")
OUTPUT_DIR = Path("src/data/processed/recipe_suggestion")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_DIR = Path("src/data/models/recipe_suggestion")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Limit for processing (set to None for full dataset, or e.g. 10000 for testing)
LIMIT = 50000  # Processing 50k recipes for reasonable speed

print(f"📥 Loading RecipeNLG dataset (limit={LIMIT})...")
df = pd.read_csv(RAW_DATA, nrows=LIMIT)
print(f"✅ Loaded {len(df)} recipes")

# Parse NER column (ingredients)
print("🔍 Parsing ingredients...")
df["NER"] = df["NER"].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
df["NER"] = df["NER"].apply(lambda lst: ",".join(lst) if isinstance(lst, list) else "")

# Create metadata
print("📝 Creating metadata...")
metadata = df[["title", "NER"]].copy()
metadata.to_csv(OUTPUT_DIR / "recipe_metadata.csv", index=False)
print(f"✅ Saved metadata to {OUTPUT_DIR / 'recipe_metadata.csv'}")

# Generate embeddings
print("🤖 Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("🧮 Generating embeddings...")
embeddings = model.encode(
    metadata["NER"].tolist(),
    show_progress_bar=True,
    batch_size=128,
    convert_to_numpy=True
)
embeddings = embeddings.astype("float32")

print(f"💾 Saving embeddings (shape={embeddings.shape})...")
np.save(OUTPUT_DIR / "recipe_embeddings.npy", embeddings)
print(f"✅ Saved embeddings to {OUTPUT_DIR / 'recipe_embeddings.npy'}")

# Create FAISS index
print("🔍 Creating FAISS index...")
faiss.normalize_L2(embeddings)
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, str(MODEL_DIR / "recipe_index.faiss"))
print(f"✅ Saved FAISS index with {index.ntotal} vectors to {MODEL_DIR / 'recipe_index.faiss'}")

print("\n✨ Recipe embedding generation complete!")
print(f"   - Processed: {len(df)} recipes")
print(f"   - Embedding dimension: {embeddings.shape[1]}")
print(f"   - Output files:")
print(f"     • {OUTPUT_DIR / 'recipe_metadata.csv'}")
print(f"     • {OUTPUT_DIR / 'recipe_embeddings.npy'}")
print(f"     • {MODEL_DIR / 'recipe_index.faiss'}")

