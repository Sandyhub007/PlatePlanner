import sqlite3
import pandas as pd
import numpy as np
import faiss
from pathlib import Path
import time

# Paths
RAW_DATA = Path("src/data/raw/RecipeNLG_dataset.csv")
PROCESSED_DIR = Path("src/data/processed/recipe_suggestion")
MODEL_DIR = Path("src/data/models/recipe_suggestion")

EMBEDDINGS_PATH = PROCESSED_DIR / "recipe_embeddings.npy"
METADATA_PATH = PROCESSED_DIR / "recipe_metadata.csv"

# Output Paths
DB_PATH = MODEL_DIR / "recipes.db"
OPT_INDEX_PATH = MODEL_DIR / "recipe_index_opt.faiss"

def optimize_pipeline():
    print("🚀 Starting Mobile Optimization Pipeline...")
    
    # --- Step 1: Create SQLite Database ---
    if DB_PATH.exists():
        DB_PATH.unlink()
        
    print(f"📦 Converting CSV metadata to SQLite ({DB_PATH})...")
    
    # We load CSV in chunks to avoid memory spike
    chunk_size = 100_000
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY,
            title TEXT,
            ingredients TEXT,
            directions TEXT,
            ner TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON recipes(title)")
    conn.commit()

    # Read original Raw Data (to get directions back if they were dropped in metadata, 
    # but generate_recipe_data.py saved 'recipe_metadata.csv' which might only have title/NER.
    # Let's check what generate_recipe_data.py saved.
    # It saved df[["title", "NER"]].
    # WE NEED DIRECTIONS! 
    # So we must read the RAW CSV again to get full data.
    
    print("   Reading raw dataset in chunks...")
    try:
        # Assuming the raw CSV has columns: [id, title, ingredients, directions, link, source, NER]
        # RecipeNLG usually has: 'Unnamed: 0', 'title', 'ingredients', 'directions', 'link', 'source', 'NER'
        # We'll map the index as 'id'.
        
        chunk_iter = pd.read_csv(RAW_DATA, chunksize=chunk_size)
        total_rows = 0
        
        for i, chunk in enumerate(chunk_iter):
            # Rename columns if needed or just select
            # We want: title, ingredients, directions, NER
            # And use the index as ID to match FAISS index (0...N)
            
            # Reset index relative to the full dataset? 
            # pd.read_csv(nrows=None) read it sequentially.
            # We need to ensure the ID matches the embedding index (0 to 2,231,142).
            # The chunk index will be chunk-relative unless we handle it.
            # Actually, we can insert explicit IDs.
            
            data_to_insert = []
            for idx, row in chunk.iterrows():
                # Global ID is the dataframe index. 
                # Note: chunk.iterrows() index should be global if read_csv handles it? 
                # Pandas chunk iterator preserves original index if implied? No, likely ranges.
                # Let's rely on counter.
                
                # Careful: The embeddings were generated from 'recipe_metadata.csv' which was generated from `pd.read_csv(RAW_DATA, nrows=None)`.
                # So the order MUST BE EXACTLY THE SAME.
                # iterate row by row is slow.
                
                # Vectorized insert prep:
                pass
            
            # Prepare DataFrame for SQL
            # We need explicit ID column starting from total_rows
            chunk['id'] = range(total_rows, total_rows + len(chunk))
            
            # Select columns. Handle missing columns gracefully
            cols = ['id', 'title', 'ingredients', 'directions', 'NER']
            # map valid columns
            valid_cols = [c for c in cols if c in chunk.columns]
            
            # Rename NER to ner for consistency if needed, but SQL columns defined above lower case
            # Let's map dataframe columns to DB columns
            rename_map = {'NER': 'ner'}
            chunk_renamed = chunk.rename(columns=rename_map)
            
            # Filter to schema
            final_cols = ['id', 'title', 'ingredients', 'directions', 'ner']
            # Ensure columns exist
            for c in final_cols:
                if c not in chunk_renamed.columns:
                    chunk_renamed[c] = ""
            
            chunk_renamed[final_cols].to_sql('recipes', conn, if_exists='append', index=False)
            
            total_rows += len(chunk)
            print(f"   - Processed {total_rows} rows...")
            
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return

    conn.close()
    print("✅ SQLite Database created.")

    # --- Step 2: Create Compressed FAISS Index ---
    print(f"🧠 Training Compressed Index (IVF-PQ) from {EMBEDDINGS_PATH}...")
    
    # Load embeddings (mmap to save RAM, but we need some in RAM for training)
    embeddings = np.load(EMBEDDINGS_PATH, mmap_mode='r')
    d = embeddings.shape[1]
    nb = embeddings.shape[0]
    
    # Configuration for quantization
    # nlist: Number of clusters (Voronoi cells). 4*sqrt(N) is standard. for 2M => ~5600. Let's use 4096 (2^12)
    nlist = 4096
    # m: Number of sub-quantizers. Must divide d=384. 
    # d/m should be 8, 4, etc. 384 / 32 = 12 bytes? No.
    # standard m=8 or m=16. 
    # Let's use m=32 (resulting code size 32 bytes per vector).
    m = 32 # 384/32 = 12 dimensions per sub-vector
    
    quantizer = faiss.IndexFlatL2(d)
    index = faiss.IndexIVFPQ(quantizer, d, nlist, m, 8) # 8 bits per code
    
    # Train
    # We need a subset of vectors to train. 100k is usually enough.
    print("   Training index (this uses 100k vectors)...")
    train_size = min(100_000, nb)
    # Load training set into RAM
    x_train = embeddings[:train_size].copy()
    faiss.normalize_L2(x_train) # IMPORTANT: Original was IP (cosine), so we must normalize for L2 to behave like IP/Cosine
    
    index.train(x_train)
    print("   Training complete.")
    
    # Add vectors
    print("   Adding vectors to index...")
    batch_size = 50_000
    for i in range(0, nb, batch_size):
        end = min(i + batch_size, nb)
        batch = embeddings[i:end].copy()
        faiss.normalize_L2(batch)
        index.add(batch)
        print(f"   - Added {end}/{nb} vectors")
        
    print(f"💾 Saving Compressed Index to {OPT_INDEX_PATH}...")
    faiss.write_index(index, str(OPT_INDEX_PATH))
    print("✅ Optimization Complete!")

if __name__ == "__main__":
    optimize_pipeline()
