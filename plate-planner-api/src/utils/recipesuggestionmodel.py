from ast import literal_eval
import sqlite3
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config.paths import DataPaths

# -------------------------
# Constants
# -------------------------
faiss.omp_set_num_threads(1)
BASE_MODEL_NAME = "all-MiniLM-L6-v2"
FINETUNED_MODEL_PATH = "src/data/models/recipe_suggestion/finetuned-recipe-encoder"
paths = DataPaths()

# Optimized Paths (prefer fine-tuned index if available)
DB_PATH = "src/data/models/recipe_suggestion/recipes.db"
FINETUNED_INDEX_PATH = "src/data/models/recipe_suggestion/recipe_index_finetuned_opt.faiss"
BASE_INDEX_PATH = "src/data/models/recipe_suggestion/recipe_index_opt.faiss"

# Auto-select best available model and index
if os.path.isdir(FINETUNED_MODEL_PATH):
    MODEL_NAME = FINETUNED_MODEL_PATH
    print("🎯 Fine-tuned food-domain model detected!")
else:
    MODEL_NAME = BASE_MODEL_NAME

if os.path.exists(FINETUNED_INDEX_PATH):
    OPT_INDEX_PATH = FINETUNED_INDEX_PATH
    print("🎯 Fine-tuned FAISS index detected!")
else:
    OPT_INDEX_PATH = BASE_INDEX_PATH

# -------------------------
# Global Resources
# -------------------------
print(f"🔄 Loading recipe model: {MODEL_NAME}...")
try:
    model = SentenceTransformer(MODEL_NAME)
    # Load compressed index (mmap to save RAM)
    # Note: faiss.read_index defaults to loading into RAM.
    # For IVF-PQ (~90MB), this is fine.
    index = faiss.read_index(str(OPT_INDEX_PATH))
    print(f"✅ Loaded: {MODEL_NAME} + Index with {index.ntotal} vectors.")
except Exception as e:
    print(f"❌ Failed to load optimized resources: {e}")
    model = None
    index = None

# -------------------------
# Recipe Suggestion Logic (Optimized for Mobile/Memory)
# -------------------------
def suggest_recipes(
    ingredients: list[str],
    top_n: int = 5,
    rerank_weight: float = 0.6,
    raw_k: int = 500,
    min_overlap: int = 2,
    # Dietary filters (Not currently in DB, so ignored/false for now)
    is_vegan: bool = False,
    is_vegetarian: bool = False,
    is_gluten_free: bool = False,
    is_dairy_free: bool = False
) -> list[dict]:
    """Suggest recipes using Quantized Index + SQLite to minimize RAM usage."""
    if not index or not model:
        return []

    # 1) Semantic Search
    query = " ".join(ingredients)
    query_vec = model.encode([query])
    faiss.normalize_L2(query_vec)
    distances, indices = index.search(query_vec, raw_k)

    # 2) Fetch Metadata from SQLite
    # valid indices only
    found_indices = [int(i) for i in indices[0] if i >= 0]
    if not found_indices:
        return []

    # Batch query by ID
    ph = ",".join("?" * len(found_indices))
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"SELECT id, title, ingredients, directions, ner FROM recipes WHERE id IN ({ph})", found_indices)
            rows = cursor.fetchall()
    except Exception as e:
        print(f"SQL Error: {e}")
        return []

    # Map ID -> Row
    row_map = {row['id']: row for row in rows}

    # 3) Process results in ranked order
    results: list[dict] = []
    
    # Pre-compute input set (normalized)
    norm_inputs = set(x.lower().strip() for x in ingredients if x.strip())

    for dist_i, idx in enumerate(found_indices):
        if idx not in row_map:
            continue
            
        row = row_map[idx]
        
        # Parse NER (ingredients list)
        raw_ner = row['ner']
        if not raw_ner: continue
        
        try:
            # It's usually a string rep of a list "['a', 'b']"
            recipe_ings = literal_eval(raw_ner)
        except:
            # Fallback
            recipe_ings = [x.strip() for x in raw_ner.split(",") if x.strip()]

        # Dedupe recipe ingredients
        unique_full_list = []
        seen = set()
        for ing in recipe_ings:
            if ing not in seen:
                unique_full_list.append(ing)
                seen.add(ing)

        # Compute Overlap
        overlap_set = set()
        for r_ing in unique_full_list:
            r_ing_lower = r_ing.lower()
            # Simple substring match against any input
            for u_ing in norm_inputs:
                if u_ing in r_ing_lower:
                    overlap_set.add(r_ing)
                    break
        
        if len(overlap_set) < min_overlap:
            continue

        # Scores
        sem_score = float(distances[0][dist_i])
        sem_score = max(0.0, min(1.0, sem_score))
        
        overlap_score = len(overlap_set) / max(len(ingredients), 1)
        
        combined_score = (1 - rerank_weight)*sem_score + rerank_weight*overlap_score
        combined_score = max(0.0, min(1.0, combined_score))

        # Directions parsing (usually list string or list)
        directions = row['directions']
        # Convert to string if it's a list represenation
        try:
            d_list = literal_eval(directions) if directions.startswith("[") else [directions]
            final_directions = "\n".join(d_list) if isinstance(d_list, list) else str(d_list)
        except:
            final_directions = str(directions)

        results.append({
            "title": row['title'],
            "ingredients": list(overlap_set), # Matched ingredients
            "all_ingredients": unique_full_list,
            "directions": final_directions,
            "semantic_score": sem_score,
            "overlap_score": overlap_score,
            "combined_score": combined_score,
            "rank": 0, # assigned later
            "tags": { # Default placeholders until classification added to DB
                "vegan": False,
                "vegetarian": False,
                "gluten_free": False,
                "dairy_free": False
            }
        })

    # Sort & Rank
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    results = results[:top_n]
    
    for i, res in enumerate(results):
        res["rank"] = i + 1
        
    return results
