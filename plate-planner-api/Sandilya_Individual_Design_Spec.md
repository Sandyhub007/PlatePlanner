# Sandilya Chimalamarri – Individual Design Specification (Recipe Suggestion Subsystem)

## 1. Introduction
This document details the design, requirements, data structures, algorithms, tests, and research log for the Recipe Suggestion Subsystem of Plate Planner. It reflects only my contributions (ML embedding, FAISS similarity, reranking, and API integration for suggestions).

## 2. Scope & Functional Overview
- Convert user ingredient list to a sentence embedding
- Use FAISS to retrieve semantically similar recipes
- Rerank candidates using ingredient overlap
- Return top-N recipes with score breakdowns and overlapping ingredients

## 3. Requirements
### Functional
- Input: List of ingredients; parameters `top_n`, `rerank_weight`, `raw_k`, `min_overlap`
- Compute: embedding -> FAISS search -> overlap-based rerank
- Output: List of recipes with `title`, matching `ingredients`, `semantic_score`, `overlap_score`, `combined_score`, `rank`

### Non-Functional
- p95 latency < 100ms for ~10k recipes
- Model/index loaded once at startup
- Parameters tunable without code changes

## 4. Data Structures & Assets
- Embeddings (NumPy, float32): `src/data/processed/recipe_suggestion/recipe_embeddings.npy` (shape: [n, 384])
- FAISS index (FlatIP): `src/data/models/recipe_suggestion/recipe_index.faiss`
- Metadata CSV: `src/data/processed/recipe_suggestion/recipe_metadata.csv` (columns include `title`, `NER`)

## 5. Algorithm
### Core Steps
1) Encode ingredients with SentenceTransformer `all-MiniLM-L6-v2`
2) L2 normalize query for cosine via inner product
3) FAISS search `raw_k` candidates
4) Calculate overlap with user input
5) Compute scores:
   - `semantic_score = clamp(cosine_similarity, 0..1)`
   - `overlap_score = |overlap| / |input|`
   - `combined = (1 - rerank_weight) * semantic + rerank_weight * overlap`
6) Sort by `combined` and return top `N`

### Reference Implementation (excerpt)
```python
# src/utils/recipesuggestionmodel.py
model = SentenceTransformer(MODEL_NAME)
metadata_df = pd.read_csv(RECIPE_METADATA_PATH)
recipe_embeddings = np.load(EMBEDDINGS_PATH).astype("float32")
faiss.normalize_L2(recipe_embeddings)
index = faiss.read_index(str(FAISS_INDEX_PATH))

def suggest_recipes(ingredients, top_n=5, rerank_weight=0.6, raw_k=50, min_overlap=2):
    query_vec = model.encode([" ".join(ingredients)])
    faiss.normalize_L2(query_vec)
    distances, indices = index.search(query_vec, raw_k)
    input_set = set(ingredients)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        row = metadata_df.iloc[idx]
        unique_full_list = dedupe_ingredients(row["NER"])  # order-preserving
        overlap = input_set & set(unique_full_list)
        if len(overlap) < min_overlap:
            continue
        sem = max(0.0, min(1.0, float(dist)))
        over = len(overlap) / max(len(ingredients), 1)
        combined = (1 - rerank_weight) * sem + rerank_weight * over
        results.append({
            "title": row["title"],
            "ingredients": [i for i in unique_full_list if i in overlap],
            "semantic_score": sem,
            "overlap_score": over,
            "combined_score": max(0.0, min(1.0, combined)),
        })
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    for rank, r in enumerate(results[:top_n], start=1):
        r["rank"] = rank
    return results[:top_n]
```

## 6. Design Decisions & Rationale
- Model: `all-MiniLM-L6-v2` (384D) for speed vs quality
- Index: `IndexFlatIP` (simple, fast for ≤100k)
- Cosine via L2 norm + inner product for FAISS efficiency
- Rerank weight default `0.6` (60% overlap, 40% semantic) from empirical testing

## 7. Configuration & Integration
- Endpoint: `POST /suggest_recipes` (FastAPI)
- Request model validated via Pydantic
- Parameters exposed to client (`top_n`, `rerank_weight`)
- Assets loaded once at startup, with clear error messages on missing files

## 8. Testing Strategy
### Unit Tests
- Embedding generation shape/type
- FAISS search returns expected neighbor for seeded vectors
- Overlap scoring correctness
- Combined score math across edge cases
- Clamp behavior for semantic score

### Functional/Integration Tests
- E2E: `/suggest_recipes` returns ranked structured data
- Performance: p95 < 100ms on 10k recipes

### Example Test
```python
def test_overlap_threshold():
    q = ["egg", "flour", "sugar"]
    out = suggest_recipes(q, top_n=5, rerank_weight=0.6)
    assert all(len(set(r["ingredients"]) & set(q)) >= 2 for r in out)
```

## 9. Sample I/O
### Input
```json
{"ingredients": ["egg", "flour", "sugar"], "top_n": 5, "rerank_weight": 0.6}
```
### Output (truncated)
```json
[{"title": "Pancakes", "ingredients": ["egg", "flour", "sugar"], "semantic_score": 0.75, "overlap_score": 1.0, "combined_score": 0.85, "rank": 1}]
```

## 10. Research Log (Weeks)
- Weeks 1–2: Model selection experiments; embedding format alignment; scoring prototype
- Weeks 3–4: Embedding generation for corpus; FAISS index build; parameter tuning
- Weeks 5+: Unit tests, E2E testing, performance validation; API contract docs

## 11. Risks & Mitigations
- Missing assets → detectable at startup with explicit guidance
- Scale growth → migrate to IVF/HNSW; shard metadata
- Noisy NER → add normalization/blacklist improvements

## 12. Future Enhancements
- Personalized reranking per user preferences
- Lightweight reindexing pipeline for incremental updates
- GPU-accelerated FAISS for >1M vectors
