# Chapter 6. Evaluation Methodology

This chapter details the evaluation methodology used to assess Plate Planner’s two core capabilities: (1) Recipe Suggestion and (2) Ingredient Substitution. It includes the testbed setup, datasets, baseline approaches, parameters, and performance measures. We also report baseline experiment procedures and how to reproduce them.

## 6.1 Testbed Setup

- Runtime:
  - Python: 3.11
  - FastAPI: 0.115.x, Uvicorn (standard extras)
  - Neo4j: 5.13 (containerized)
  - FAISS (CPU): 1.11+
  - SentenceTransformers: 4.1.0 (model: `all-MiniLM-L6-v2`)
  - spaCy: `en_core_web_sm`
- Hardware:
  - CPU: Any modern 4+ core CPU (tests run on an Apple Silicon M-series and x86_64 Linux VM)
  - Memory: ≥ 8 GB recommended (≥ 16 GB preferred for larger datasets)
- Deployment:
  - Docker Compose orchestrates two services:
    - `neo4j` (ports 7474/7687)
    - `api` (port 8000)
  - Volumes: persist Neo4j data and mount the `src/data` directory for the API

## 6.2 Datasets

- Raw Dataset (optional): RecipeNLG (`src/data/raw/RecipeNLG_dataset.csv`) – if full pipeline is executed
- Processed Datasets (used by runtime):
  - `src/data/processed/recipe_suggestion/recipe_metadata.csv`: titles, tokenized ingredients (NER)
  - `src/data/processed/recipe_suggestion/recipe_embeddings.npy`: 384D float32 embeddings
  - `src/data/models/recipe_suggestion/recipe_index.faiss`: FAISS index for similarity search
  - Neo4j Graph CSVs:
    - `src/data/processed/ingredients.csv`
    - `src/data/processed/recipes.csv`
    - `src/data/processed/recipe_ingredients.csv`
  - Optional Substitution CSVs:
    - `src/data/processed/ingredient_substitution/substitution_edges_with_context.csv`

## 6.3 Baseline Approaches

We evaluate Plate Planner’s methods against simple and realistic baselines:

### 6.3.1 Recipe Suggestion
- **Baseline A (Overlap-only)**: Rank by the number of overlapping ingredients between user input and each recipe; ignore semantics.
- **Baseline B (Semantic-only)**: Rank by cosine similarity from SentenceTransformer embedding; ignore overlap.
- **Proposed (Hybrid)**: Weighted blend of semantic similarity and overlap with rerank_weight `w` (default = 0.6), i.e. `score = (1 - w) * semantic + w * overlap`.

### 6.3.2 Ingredient Substitution
- **Baseline C (Direct-only)**: Query `SUBSTITUTES_WITH` edges and rank by edge score.
- **Baseline D (Co-occurrence-only)**: Rank by frequency of co-appearance in recipes (normalized).
- **Proposed (Hybrid)**: Weighted blend `alpha * direct + (1 - alpha) * cooccurrence` (default `alpha = 0.9`).

## 6.4 Test Parameters

- Recipe Suggestion:
  - SentenceTransformer: `all-MiniLM-L6-v2`
  - Embedding size: 384
  - FAISS index: `IndexFlatIP` with L2-normalized vectors
  - Candidates `raw_k`: 50 (unless otherwise specified)
  - Results `top_n`: 5 (unless otherwise specified)
  - Minimum overlap: 2 ingredients (unless otherwise specified)
  - Rerank weight `w`: {0.3, 0.5, 0.6, 0.7, 0.8}
- Ingredient Substitution:
  - `alpha` for hybrid: {0.5, 0.7, 0.9, 0.95}
  - Top-k substitutes: 5, 10
  - Context: {None, "baking", "sauce", "salad"}

## 6.5 Performance Measures

- Latency:
  - p50, p90, p95 endpoint latencies measured via repeated calls
- Quality (Recipe Suggestion):
  - Overlap@k: average number of overlapping ingredients among top-k
  - Hit@k: fraction of queries returning at least one recipe with ≥ min overlap
  - (Optional) Recall@k against curated query→recipe target lists
- Quality (Substitution):
  - Direct-Match Rate: fraction where a context-specific edge exists
  - Top-k Coverage: fraction where an acceptable substitute appears in top-k
  - (Optional) Expert review scores for quality (1–5)

## 6.6 Baseline Experiment Procedure

1. Prepare data artifacts (embeddings, FAISS index, CSVs) per Section 7 tutorial.
2. Start services: `docker-compose up --build -d`.
3. For Recipe Suggestion experiments:
   - Execute batches of `/suggest_recipes` with different `rerank_weight` values.
   - Log latencies and quality metrics for each configuration (k ∈ {5, 10}).
   - Compare Baseline A, Baseline B, and Proposed Hybrid.
4. For Ingredient Substitution experiments:
   - Execute `/substitute` queries for a panel of ingredients with and without context.
   - Compare Baseline C, Baseline D, and Proposed Hybrid at alpha ∈ {0.5, 0.7, 0.9}.
5. Produce tables/plots of latency vs. quality across parameter sweeps.

## 6.7 Reproducibility Checklist

- Pin Python and package versions (pyproject.toml).
- Store random seeds where applicable (embedding batching, evaluation scripts).
- Persist experiment inputs/outputs in `src/data/results/*`.
- Provide raw CSVs and summary tables for grading.

---

# Chapter 7. System Design / Methodology – Solution Overview

This chapter presents Plate Planner’s architecture and implementation details, with tutorial-style steps for deployment and usage.

## 7.1 Architecture Overview

```
+-------------------+         REST API          +---------------------+
|   FastAPI/Uvicorn | <-----------------------> | Neo4j (Graph DB)    |
|                   |                           |  - Ingredients      |
|  Endpoints:       |                           |  - Recipes          |
|  - /              |                           |  - Edges:           |
|  - /docs          |                           |    HAS_INGREDIENT   |
|  - /suggest_...   |                           |    SUBSTITUTES_WITH |
|  - /substitute    |                           |    SIMILAR_TO       |
|  - /recipes/{t}   |                           +---------------------+
|                   |                     ^
|  Models: Pydantic |                     |
+-------------------+                     |
           ^                               |
           | ML Inference (at startup)     |
           |  - SentenceTransformer        |
           |  - FAISS index                |
           v                               |
+-------------------+                      |
|  Data Artifacts   | <---------------------+
|  - Embeddings.npy |
|  - Index.faiss    |
|  - Metadata.csv   |
+-------------------+
```

## 7.2 Components

- API Layer (`src/api/app.py`): FastAPI application, CORS, routes, models, error handling
- ML Suggestion Utils (`src/utils/recipesuggestionmodel.py`): model loading, FAISS search, reranking
- Neo4j Service (`src/services/neo4j_service.py`): substitution queries, recipe detail retrieval
- Database Bootstrap (`src/database/*.py`): graph loading, similarity edge building, exploration
- Config (`src/config/*.py`): environment variables, `DataPaths` for all file locations
- Pipelines (`src/pipelines/*.py`): data preprocessing, training utilities, feature extraction

## 7.3 Key Algorithms (Pseudo-code)

### 7.3.1 Recipe Suggestion (Hybrid)
```
function suggest_recipes(ingredients, top_n, w, raw_k, min_overlap):
    q = encode(" ".join(ingredients))
    normalize_L2(q)
    D, I = faiss_search(q, raw_k)
    input_set = set(ingredients)
    results = []
    for (dist, idx) in zip(D[0], I[0]):
        rec = metadata[idx]
        uniq = dedupe(rec.NER)
        overlap = input_set ∩ set(uniq)
        if |overlap| < min_overlap: continue
        semantic = clamp(dist, 0..1)
        overlap_s = |overlap| / max(|ingredients|, 1)
        score = (1 - w)*semantic + w*overlap_s
        results.append({title, overlap_subset, semantic, overlap_s, score})
    return top_n_by(results, score)
```

### 7.3.2 Ingredient Substitution (Hybrid)
```
function get_hybrid_subs(ingredient, context, top_k, alpha):
    direct = query_SUBSTITUTES_WITH(ingredient, context)
    cooc   = query_cooccurrence(ingredient)
    names = keys(direct) ∪ keys(cooc)
    merged = []
    for name in names:
        d = direct[name]?.score or 0
        c = cooc[name]?.score or 0
        s = alpha*d + (1 - alpha)*c
        merged.append({name, score=s, context_if_direct})
    return top_k_by(merged, score)
```

## 7.4 Implementation Details

- Packaging & Versions: `pyproject.toml` (pinned ranges), Poetry for dependency management
- Startup Flow (API container):
  1. Wait for Neo4j to be ready (netcat)
  2. Run bootstrap task (`task neo4j:bootstrap`) if needed
  3. Load SentenceTransformer, embeddings, FAISS index
  4. Start Uvicorn with FastAPI app
- DataPaths (`src/config/paths.py`): Single source of truth for file locations; avoids hardcoded paths across modules
- Error Handling: `HTTPException` with structured messages; logging with timestamps and exception traces

## 7.5 Tutorial: Deploy & Use

### 7.5.1 Prerequisites
- Docker and Docker Compose installed
- Disk space for Neo4j data volume and model artifacts

### 7.5.2 Start Services
```bash
docker-compose up --build -d
# API → http://localhost:8000
# Docs → http://localhost:8000/docs
# Neo4j Browser → http://localhost:7474  (neo4j / 12345678)
```

### 7.5.3 Bootstrap Graph (Optional)
```bash
# inside container or via Taskfile locally
task neo4j:bootstrap
```

### 7.5.4 Example Requests
- Recipe Suggestion
```bash
curl -X POST http://localhost:8000/suggest_recipes \
  -H 'Content-Type: application/json' \
  -d '{"ingredients": ["butter","sugar","flour"], "top_n": 5, "rerank_weight": 0.6}'
```

- Ingredient Substitution
```bash
curl "http://localhost:8000/substitute?ingredient=butter&context=baking&hybrid=true&top_k=5"
```

- Recipe Details
```bash
curl "http://localhost:8000/recipes/Marinated%20Flank%20Steak%20Recipe"
```

### 7.5.5 Rebuild Artifacts (If Needed)
- Recompute embeddings: run pipeline notebook/script with SentenceTransformer
- Rebuild FAISS index: load embeddings, write index using FAISS Python API
- Refresh CSVs for Neo4j: export processed `ingredients.csv`, `recipes.csv`, `recipe_ingredients.csv`

## 7.6 Reproducibility & Handoff

- Provide a zipped `src/data/models` and `src/data/processed` for graders (or instructions to regenerate)
- Include Taskfile commands and sample curl scripts in a `README_eval.md`
- Keep all code paths centralized via `DataPaths` so environments can vary without code changes

---

End of Chapters 6 and 7.
