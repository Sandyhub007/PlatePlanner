import os
import faiss
import sqlite3
import numpy as np
from ast import literal_eval
from sentence_transformers import SentenceTransformer
from src.config.paths import DataPaths

# -------------------------
# Constants
# -------------------------
faiss.omp_set_num_threads(1)
BASE_MODEL_NAME = "all-MiniLM-L6-v2"
FINETUNED_MODEL_PATH = "src/data/models/recipe_suggestion/finetuned-recipe-encoder"
paths = DataPaths()

DB_PATH = "src/data/models/recipe_suggestion/recipes.db"
FINETUNED_INDEX_PATH = "src/data/models/recipe_suggestion/recipe_index_finetuned_opt.faiss"
BASE_INDEX_PATH = "src/data/models/recipe_suggestion/recipe_index_opt.faiss"

# Auto-select best available model and index
if os.path.isdir(FINETUNED_MODEL_PATH):
    MODEL_NAME = FINETUNED_MODEL_PATH
    print("🎯 [RetrievalService] Fine-tuned food-domain model detected!")
else:
    MODEL_NAME = BASE_MODEL_NAME

if os.path.exists(FINETUNED_INDEX_PATH):
    OPT_INDEX_PATH = FINETUNED_INDEX_PATH
    print("🎯 [RetrievalService] Fine-tuned FAISS index detected!")
else:
    OPT_INDEX_PATH = BASE_INDEX_PATH

class RetrievalService:
    """
    Stage 1: Semantic Search (Retrieval)
    Casts a wide net using FAISS and SentenceTransformers to find fuzzy metadata matches.
    """
    def __init__(self):
        self.model = None
        self.index = None
        self._load_resources()

    def _load_resources(self):
        print(f"🔄 [RetrievalService] Loading recipe model: {MODEL_NAME}...")
        try:
            self.model = SentenceTransformer(MODEL_NAME)
            self.index = faiss.read_index(str(OPT_INDEX_PATH))
            print(f"✅ [RetrievalService] Loaded: {MODEL_NAME} + Index with {self.index.ntotal} vectors.")
        except Exception as e:
            print(f"❌ [RetrievalService] Failed to load optimized resources: {e}")

    def get_candidates(self, query: str, k: int = 200) -> list[dict]:
        """
        Takes a natural language query and returns the top K unstructured candidates.
        """
        if not self.index or not self.model:
            return []

        # 1) Semantic Search via FAISS
        query_vec = self.model.encode([query])
        faiss.normalize_L2(query_vec)
        distances, indices = self.index.search(query_vec, k)

        found_indices = [int(i) for i in indices[0] if i >= 0]
        if not found_indices:
            return []

        # 2) Fetch Metadata from SQLite
        ph = ",".join("?" * len(found_indices))
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    f"SELECT id, title, ingredients, directions, ner FROM recipes WHERE id IN ({ph})", 
                    found_indices
                )
                rows = cursor.fetchall()
        except Exception as e:
            print(f"SQL Error: {e}")
            return []

        row_map = {row['id']: row for row in rows}
        candidates = []

        # 3) Build Candidates List (keeping FAISS ordering)
        for dist_i, idx in enumerate(found_indices):
            if idx not in row_map:
                continue
            
            row = row_map[idx]
            raw_ner = row['ner']
            
            try:
                recipe_ings = literal_eval(raw_ner) if raw_ner else []
            except:
                recipe_ings = [x.strip() for x in raw_ner.split(",")] if raw_ner else []

            # Dedupe ingredients
            unique_ings = list(dict.fromkeys(recipe_ings))
            
            directions = row['directions']
            try:
                d_list = literal_eval(directions) if directions.startswith("[") else [directions]
                final_directions = "\n".join(d_list) if isinstance(d_list, list) else str(d_list)
            except:
                final_directions = str(directions)

            candidates.append({
                "recipe_id": row['id'],
                "title": row['title'],
                "ingredients": unique_ings,
                "directions": final_directions,
                "semantic_score": float(distances[0][dist_i])
            })

        return candidates

# Singleton instance for the service
retrieval_service = RetrievalService()
