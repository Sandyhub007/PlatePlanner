# Plate Planner API - Design Specification

**Project Name:** Plate Planner API

**Design Spec Title:** Design Specification  
**Version:** 0.1  
**Date:** 2025-01-30

**Author:** Ranga Reddy Nukala (range@coding.com)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2025-01-30 | Initial design specification | Ranga Reddy Nukala |

---

## Introduction

Plate Planner is a graph-powered, ML-enhanced meal assistant that provides intelligent recipe recommendations and ingredient substitution suggestions. The system combines semantic similarity search using sentence embeddings with graph-based relationship queries in Neo4j to deliver context-aware meal planning assistance.

The core functionality includes:

1. **Recipe Suggestion**: Uses sentence embeddings (SentenceTransformers) combined with FAISS for efficient similarity search, enhanced by ingredient overlap scoring
2. **Ingredient Substitution**: Leverages Neo4j graph database with context-aware and similarity-based edges to suggest ingredient alternatives
3. **Graph Database**: Neo4j stores ingredients, recipes, and relationships (HAS_INGREDIENT, SUBSTITUTES_WITH, SIMILAR_TO)

The system is fully containerized using Docker Compose, making it easy to deploy and run in any environment.

---

## References

- **Architecture Diagram**: See README.md Section "Architecture Overview"
- **Repository**: https://github.com/irangareddy/plate-planner-api.git
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Neo4j Documentation**: https://neo4j.com/docs/
- **SentenceTransformers**: https://www.sbert.net/
- **FAISS**: https://github.com/facebookresearch/faiss

---

## Requirements

### Functional Requirements

1. **Recipe Suggestion (FR-001)**
   - Accept a list of ingredients as input
   - Return top N recipes ranked by semantic similarity and ingredient overlap
   - Support configurable reranking weight (0-1) to balance semantic similarity vs ingredient overlap
   - Return only ingredients that overlap with input ingredients

2. **Ingredient Substitution (FR-002)**
   - Accept an ingredient name and optional context (e.g., "baking", "cooking")
   - Support direct substitution lookup via SUBSTITUTES_WITH edges
   - Support hybrid substitution (direct + co-occurrence analysis)
   - Return top K substitutes with normalized similarity scores
   - Provide context information when available

3. **Recipe Details (FR-003)**
   - Fetch full recipe information by title
   - Return complete ingredient list, directions, source, and link
   - Support case-insensitive title matching

4. **Graph Bootstrap (FR-004)**
   - Load ingredients from CSV into Neo4j
   - Load recipes from CSV into Neo4j
   - Create HAS_INGREDIENT relationships
   - Build SIMILAR_TO edges based on semantic similarity
   - Add SUBSTITUTES_WITH edges from processed substitution data

5. **Health Check (FR-005)**
   - Provide health check endpoint to verify API is running

### Non-Functional Requirements

1. **Performance (NFR-001)**
   - Recipe suggestions should return results in < 500ms for typical queries
   - FAISS index enables sub-second similarity search for large recipe databases
   - Neo4j queries optimized with indexes on Ingredient.name and Recipe.recipe_id

2. **Scalability (NFR-002)**
   - Support datasets with 100K+ recipes
   - FAISS enables efficient similarity search for large vector databases
   - Docker containerization allows horizontal scaling

3. **Reliability (NFR-003)**
   - Error handling for missing data, invalid inputs
   - Graceful degradation when models/files are missing
   - Transaction support in Neo4j for data consistency

4. **Maintainability (NFR-004)**
   - All paths resolved via `config.paths.DataPaths` (no hardcoded paths)
   - Clear separation of concerns (API, services, utils, database)
   - Comprehensive logging for debugging

---

## Functional Overview

### Architecture

```
┌─────────────────┐         REST API          ┌──────────────────┐
│                 │     (FastAPI/Uvicorn)     │                  │
│   FastAPI API   │◄──────────────────────────►│   Neo4j Database │
│                 │                            │                  │
│  - /suggest_    │                            │  - Ingredients   │
│    recipes      │                            │  - Recipes       │
│  - /substitute  │                            │  - Relationships │
│  - /recipes/    │                            │    • HAS_INGRED  │
│    {title}      │                            │    • SUBSTITUTES │
│  - / (health)   │                            │    • SIMILAR_TO  │
└─────────────────┘                            └──────────────────┘
         │                                              ▲
         │                                              │
         │ ML Model Inference                           │
         │                                              │
         ▼                                              │
┌─────────────────┐                                    │
│  SentenceTrans  │                                    │
│  -former Model  │                                    │
│  + FAISS Index  │───────────────────────────────────┘
│                 │       (Stores embeddings)
└─────────────────┘
```

### Recipe Suggestion Flow

1. **Input**: User provides list of ingredients
2. **Embedding**: Ingredients list converted to sentence embedding using SentenceTransformer
3. **FAISS Search**: Query vector searched against pre-computed recipe embeddings
4. **Candidate Retrieval**: Top K (default 50) candidates retrieved based on semantic similarity
5. **Reranking**:
   - Calculate ingredient overlap score for each candidate
   - Combine semantic score and overlap score using weighted average (default: 0.6 weight on semantic)
   - Filter recipes with minimum overlap (default: 2 ingredients)
6. **Output**: Top N recipes with scores and overlapping ingredients

#### Detailed Algorithm (Pseudocode)

```
FUNCTION suggest_recipes(ingredients, top_n, rerank_weight, raw_k, min_overlap):
    // Step 1: Convert ingredients to embedding
    query_text = " ".join(ingredients)
    query_vec = SentenceTransformer.encode([query_text])
    query_vec = L2_normalize(query_vec)
    
    // Step 2: FAISS similarity search
    distances, indices = FAISS_INDEX.search(query_vec, raw_k)
    // distances[0] contains cosine similarities (after L2 normalization = inner product)
    
    // Step 3: Process candidates
    input_set = SET(ingredients)
    results = []
    
    FOR EACH (distance, index) IN zip(distances[0], indices[0]):
        recipe = METADATA_DF[index]
        recipe_ingredients = parse_NER(recipe["NER"])
        
        // Deduplicate recipe ingredients, preserving order
        unique_ingredients = deduplicate_preserve_order(recipe_ingredients)
        
        // Calculate overlap
        overlap_set = input_set INTERSECTION SET(unique_ingredients)
        
        // Filter by minimum overlap
        IF |overlap_set| < min_overlap:
            CONTINUE
        
        // Calculate scores
        semantic_score = clamp(distance, 0.0, 1.0)  // cosine similarity ∈ [-1,1] → [0,1]
        overlap_score = |overlap_set| / |ingredients|
        
        // Weighted combination (note: rerank_weight applies to overlap)
        combined_score = (1 - rerank_weight) * semantic_score + rerank_weight * overlap_score
        combined_score = clamp(combined_score, 0.0, 1.0)
        
        // Build result (only overlapping ingredients)
        results.APPEND({
            title: recipe["title"],
            ingredients: [ing for ing in unique_ingredients if ing in overlap_set],
            semantic_score: semantic_score,
            overlap_score: overlap_score,
            combined_score: combined_score
        })
    
    // Sort by combined score and return top_n
    results = SORT(results, BY combined_score DESC)
    FOR i IN range(min(top_n, |results|)):
        results[i]["rank"] = i + 1
    
    RETURN results[:top_n]
```

#### Score Calculation Details

- **Semantic Score**: Cosine similarity between ingredient list embedding and recipe embedding
  - Range: [-1, 1] → clamped to [0, 1]
  - Higher = more semantically similar
  
- **Overlap Score**: Ratio of overlapping ingredients to input ingredients
  - Formula: `|overlap_set| / |input_ingredients|`
  - Range: [0, 1]
  - Higher = more ingredient overlap
  
- **Combined Score**: Weighted blend of semantic and overlap scores
  - Formula: `(1 - rerank_weight) * semantic_score + rerank_weight * overlap_score`
  - Default rerank_weight = 0.6 (60% weight on overlap, 40% on semantic)
  - Range: [0, 1]

### Ingredient Substitution Flow

1. **Input**: Ingredient name, optional context, top_k, hybrid flag
2. **Normalization**: Ingredient name normalized using spaCy (lemmatization, lowercasing)
3. **Query Strategy**:
   - **Direct**: Query SUBSTITUTES_WITH edges in Neo4j
     - If context provided, filter by context
     - If no context matches, fall back to general substitutes
   - **Hybrid** (if enabled):
     - Combine direct substitutes with co-occurrence analysis
     - Co-occurrence: Find ingredients that frequently appear in same recipes
     - Merge and score results (default alpha=0.9 for direct, 0.1 for co-occurrence)
4. **Output**: Top K substitutes with scores, context, and source

#### Detailed Algorithm (Pseudocode)

```
FUNCTION normalize_ingredient(name):
    doc = spaCy.NLP(name)
    tokens = [token.lemma for token in doc if token.pos != DETERMINER]
    normalized = "_".join(tokens).lower().strip()
    RETURN normalized

FUNCTION get_direct_subs(ingredient, context, top_k):
    normalized_ing = normalize_ingredient(ingredient)
    
    IF context IS NOT NULL:
        // Try context-specific first
        result = NEO4J_QUERY("""
            MATCH (a:Ingredient {name: $ingredient})-[r:SUBSTITUTES_WITH]->(b)
            WHERE r.context = $context
            RETURN b.name, r.score
            ORDER BY r.score DESC
            LIMIT $top_k
        """, ingredient=normalized_ing, context=context, top_k=top_k)
        
        IF result.NOT_EMPTY:
            RETURN result, "matched"
    
    // Fallback to general substitutes
    result = NEO4J_QUERY("""
        MATCH (a:Ingredient {name: $ingredient})-[r:SUBSTITUTES_WITH]->(b)
        RETURN b.name, r.score, r.context
        ORDER BY r.score DESC
        LIMIT $top_k
    """, ingredient=normalized_ing, top_k=top_k)
    
    RETURN result, "fallback"

FUNCTION get_cooccurrence_subs(ingredient, top_k):
    normalized_ing = normalize_ingredient(ingredient)
    
    result = NEO4J_QUERY("""
        MATCH (r:Recipe)-[:HAS_INGREDIENT]->(i:Ingredient {name: $ingredient})
              <-[:HAS_INGREDIENT]-(r)-[:HAS_INGREDIENT]->(sub:Ingredient)
        WHERE sub.name <> $ingredient
        RETURN sub.name, COUNT(*) AS frequency
        ORDER BY frequency DESC
        LIMIT $top_k
    """, ingredient=normalized_ing, top_k=top_k)
    
    // Normalize frequency scores to [0,1] (divide by max expected frequency)
    normalized_result = []
    FOR EACH row IN result:
        normalized_result.APPEND({
            name: row.sub.name,
            score: row.frequency / 50.0,  // Normalization factor
            context: NULL,
            source: "cooccurrence"
        })
    
    RETURN normalized_result

FUNCTION get_hybrid_subs(ingredient, context, top_k, alpha=0.9):
    direct_subs = get_direct_subs(ingredient, context, top_k * 2)
    cooc_subs = get_cooccurrence_subs(ingredient, top_k * 2)
    
    // Merge dictionaries
    direct_dict = {sub.name: sub for sub in direct_subs}
    cooc_dict = {sub.name: sub for sub in cooc_subs}
    
    all_names = SET(direct_dict.keys()) UNION SET(cooc_dict.keys())
    merged = []
    
    FOR EACH name IN all_names:
        direct = direct_dict.get(name)
        cooc = cooc_dict.get(name)
        
        d_score = direct.score IF direct ELSE 0.0
        c_score = cooc.score IF cooc ELSE 0.0
        
        // Weighted combination
        hybrid_score = alpha * d_score + (1 - alpha) * c_score
        
        merged.APPEND({
            name: name,
            score: round(hybrid_score, 4),
            context: context IF direct ELSE NULL,
            source: "hybrid"
        })
    
    // Sort by score and return top_k
    merged = SORT(merged, BY score DESC)
    RETURN merged[:top_k]
```

#### Substitution Scoring Details

- **Direct Substitution Score**: Pre-computed similarity score stored in SUBSTITUTES_WITH edge
  - Range: [0, 1]
  - Higher = more direct/substitutable
  
- **Co-occurrence Score**: Normalized frequency count
  - Formula: `frequency / 50.0` (50 is normalization factor)
  - Range: [0, 1] (clamped)
  - Higher = more frequently appears together in recipes
  
- **Hybrid Score**: Weighted combination
  - Formula: `alpha * direct_score + (1 - alpha) * cooccurrence_score`
  - Default alpha = 0.9 (90% direct, 10% co-occurrence)
  - Range: [0, 1]

### Graph Database Schema

**Nodes**:
- `Ingredient`: {name: string (unique)}
- `Recipe`: {recipe_id: int (unique), title: string, directions: list, link: string, source: string}

**Relationships**:
- `(Recipe)-[:HAS_INGREDIENT]->(Ingredient)`
- `(Ingredient)-[:SUBSTITUTES_WITH {score: float, context: string}]->(Ingredient)`
- `(Ingredient)-[:SIMILAR_TO {score: float}]->(Ingredient)`

---

## Configuration/External Interfaces

### Environment Variables

The following environment variables can be configured (with defaults):

```bash
NEO4J_URI=bolt://localhost:7687          # Neo4j database connection URI
NEO4J_USER=neo4j                         # Neo4j username
NEO4J_PASSWORD=12345678                  # Neo4j password
```

### External Dependencies

1. **Neo4j Database**
   - Version: 5.13
   - Protocol: Bolt (7687) and HTTP (7474)
   - Authentication: Username/Password
   - Persistence: Docker volumes (neo4j_data, neo4j_logs)

2. **ML Models**
   - SentenceTransformer: `all-MiniLM-L6-v2` (384-dimensional embeddings)
   - spaCy: `en_core_web_sm` (for ingredient normalization)
   - FAISS Index: Pre-computed recipe embeddings index

3. **Data Files** (via DataPaths configuration)
   - Recipe metadata CSV: `src/data/processed/recipe_suggestion/recipe_metadata.csv`
   - Recipe embeddings: `src/data/processed/recipe_suggestion/recipe_embeddings.npy`
   - FAISS index: `src/data/models/recipe_suggestion/recipe_index.faiss`
   - Ingredients CSV: `src/data/processed/ingredients.csv`
   - Recipes CSV: `src/data/processed/recipes.csv`
   - Recipe-Ingredient relations: `src/data/processed/recipe_ingredients.csv`

### Docker Configuration

**docker-compose.yml**:
- Neo4j service: Ports 7474 (HTTP), 7687 (Bolt)
- API service: Port 8000
- Shared network: `plateplanner-net`
- Volumes: Data persistence for Neo4j, data directory mount for API

**Dockerfile**:
- Multi-stage build
- Base: Python 3.11-slim
- Poetry for dependency management
- Taskfile for task automation

### API Endpoints

**Base URL**: `http://localhost:8000`

1. **GET /** - Health check
   - Returns: `{"message": "Plate Planner API is running."}`

2. **POST /suggest_recipes** - Recipe suggestion
   - Request Body:
     ```json
     {
       "ingredients": ["butter", "sugar", "flour"],
       "top_n": 5,
       "rerank_weight": 0.6
     }
     ```
   - Response: List of RecipeResult objects with scores

3. **GET /substitute** - Ingredient substitution
   - Query Parameters:
     - `ingredient` (required): Ingredient name
     - `context` (optional): Usage context
     - `hybrid` (optional, default: false): Use hybrid lookup
     - `top_k` (optional, default: 5): Number of results
   - Response: SubstituteResponse with list of substitutes

4. **GET /recipes/{recipe_title}** - Recipe details
   - Path Parameter: `recipe_title` (case-insensitive)
   - Response: RecipeDetails with full recipe information

5. **GET /docs** - Interactive API documentation (Swagger UI)

---

## Debug

### Logging

The system uses Python's standard logging module with the following configuration:

**Logging Configuration**:
```python
level=logging.INFO
format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
datefmt="%Y-%m-%d %H:%M:%S"
logger="plate_planner"
```

**Key Log Events**:
- API startup/shutdown
- Model loading (SentenceTransformer, FAISS index)
- Recipe suggestion requests/responses
- Substitution lookup operations
- Neo4j connection status
- Error exceptions with stack traces

**Log Locations**:
- Application logs: Console output (stdout/stderr)
- Neo4j logs: Docker volume `neo4j_logs`

### Development Tools

1. **Taskfile.yml**: Provides repeatable development commands
   - `task install`: Install dependencies with Poetry
   - `task serve`: Run FastAPI with hot-reload
   - `task neo4j:bootstrap`: Bootstrap Neo4j graph
   - `task format`: Format code with Ruff
   - `task lint`: Run Ruff linter
   - `task test`: Run pytest tests

2. **API Documentation**: Available at `/docs` (Swagger UI) and `/redoc`

3. **Neo4j Browser**: Available at http://localhost:7474
   - Username: `neo4j`
   - Password: `12345678`
   - Enables interactive graph queries and visualization

### Common Debugging Scenarios

1. **Missing Model Files**:
   - Error: `FileNotFoundError: recipe_embeddings.npy`
   - Solution: Ensure data files are present or run data generation pipeline

2. **Neo4j Connection Issues**:
   - Error: `ServiceUnavailable: Failed to establish connection`
   - Solution: Verify Neo4j container is running, check NEO4J_URI environment variable

3. **Empty Results**:
   - Check if graph database has been bootstrapped
   - Verify ingredient names match exactly (case-sensitive in graph)
   - Check minimum overlap threshold in recipe suggestion

---

## Logging

### Application Logging

**Structured Logging**:
- Timestamp, log level, logger name, message
- Automatic exception logging with stack traces
- Request/response logging for API endpoints

**Log Levels**:
- `INFO`: Normal operations (model loading, request processing)
- `ERROR`: Exceptions and failures
- `WARNING`: Deprecation notices, configuration issues

### Neo4j Query Logging

Neo4j logs all queries, transactions, and connection events. Access via:
- Neo4j Browser logs
- Docker logs: `docker-compose logs neo4j`

### Performance Logging

Key metrics logged:
- Model loading time
- FAISS search execution time
- Neo4j query execution time
- API endpoint response times

---

## Counters

### Performance Metrics

The system tracks the following metrics:

1. **Recipe Suggestion Metrics**:
   - Number of candidates retrieved from FAISS
   - Number of recipes after overlap filtering
   - Average semantic similarity scores
   - Average ingredient overlap ratios

2. **Substitution Metrics**:
   - Number of direct substitutes found
   - Number of co-occurrence substitutes found (hybrid mode)
   - Average substitution scores

3. **Database Metrics**:
   - Number of ingredients in graph
   - Number of recipes in graph
   - Number of HAS_INGREDIENT relationships
   - Number of SUBSTITUTES_WITH relationships
   - Number of SIMILAR_TO relationships

### Monitoring

Currently, metrics are logged to console. For production, consider:
- Prometheus metrics exporter
- Application Performance Monitoring (APM) tools
- Neo4j metrics endpoint

---

## Implementation

### Technology Stack

- **Language**: Python 3.11
- **Web Framework**: FastAPI 0.115.x
- **ASGI Server**: Uvicorn (with standard extras)
- **Graph Database**: Neo4j 5.13 (via neo4j Python driver)
- **ML Libraries**:
  - SentenceTransformers 4.1.0 (Hugging Face)
  - FAISS-CPU 1.11.0 (Facebook Research)
  - spaCy 3.8.5+ (for NLP)
- **Data Processing**: Pandas, NumPy
- **Dependency Management**: Poetry
- **Task Automation**: Taskfile
- **Containerization**: Docker, Docker Compose

### Project Structure

```
src/
├── api/                    # FastAPI application and routes
│   └── app.py             # Main API application, endpoints
├── config/                 # Configuration management
│   ├── config.py          # Environment variables, Neo4j config
│   ├── paths.py           # DataPaths dataclass (centralized paths)
│   └── substitution_config.py
├── database/               # Neo4j graph operations
│   ├── load_into_neo4j.py        # Basic node/relationship loading
│   ├── bootstrap_graph.py        # Full graph bootstrap orchestration
│   ├── add_edges_from_csv.py     # SUBSTITUTES_WITH edge loading
│   ├── build_similar_to_edges.py # SIMILAR_TO edge construction
│   └── explore_util.py           # Graph exploration utilities
├── services/               # Business logic services
│   └── neo4j_service.py   # Neo4j query wrappers
├── utils/                  # Utility functions
│   ├── recipesuggestionmodel.py  # Recipe suggestion logic
│   ├── ingredient_normalizer.py  # Ingredient name normalization
│   └── ...
├── pipelines/              # Data processing pipelines
│   ├── parse_raw_recipes.py
│   ├── extract_cooking_verbs.py
│   ├── build_context_vectors.py
│   └── train_faiss_substitution_model.py
├── evaluation/             # Evaluation and analysis
│   ├── hybrid_substitution.py    # Hybrid substitution logic
│   ├── graph_diagnostics.py
│   └── ...
└── models/                 # Pydantic request/response models
    └── request_response_models.py
```

### Key Implementation Components

#### 1. Recipe Suggestion (`recipesuggestionmodel.py`)

**Core Logic**:
- Loads SentenceTransformer model (all-MiniLM-L6-v2)
- Loads pre-computed recipe embeddings and FAISS index
- Implements hybrid scoring: `combined_score = rerank_weight * semantic_score + (1 - rerank_weight) * overlap_score`

**Algorithm**:
1. Encode input ingredients as sentence embedding
2. FAISS similarity search (L2-normalized vectors, inner product)
3. Calculate ingredient overlap for each candidate
4. Rerank using weighted combination
5. Filter by minimum overlap threshold

#### 2. Ingredient Substitution (`hybrid_substitution.py`, `neo4j_service.py`)

**Direct Substitution**:
- Cypher query: `MATCH (a:Ingredient)-[r:SUBSTITUTES_WITH]->(b) RETURN ...`
- Filters by context when provided
- Falls back to general substitutes if context-specific not found

**Co-occurrence Analysis**:
- Finds ingredients frequently appearing in same recipes
- Cypher: `MATCH (r:Recipe)-[:HAS_INGREDIENT]->(i:Ingredient)<-[:HAS_INGREDIENT]-(r)-[:HAS_INGREDIENT]->(sub:Ingredient)`

**Hybrid Combination**:
- Merges direct and co-occurrence results
- Scores: `hybrid_score = alpha * direct_score + (1 - alpha) * cooccurrence_score`
- Default alpha: 0.9 (favoring direct substitutes)

#### 3. Graph Bootstrap (`bootstrap_graph.py`, `load_into_neo4j.py`)

**Steps**:
1. Create indexes/constraints on Ingredient.name and Recipe.recipe_id
2. Load ingredients from CSV (batch processing, BATCH_SIZE=500)
3. Load recipes from CSV
4. Create HAS_INGREDIENT relationships
5. Load SUBSTITUTES_WITH edges from CSV
6. Build SIMILAR_TO edges (semantic similarity-based)

**Optimization**:
- Batch processing for large datasets
- Transaction-based writes for consistency
- Progress bars with tqdm

#### 4. FastAPI Application (`app.py`)

**Features**:
- CORS middleware (configurable, currently allows all origins)
- Request/response models with Pydantic validation
- Async endpoints using asyncio.to_thread for CPU-bound operations
- Comprehensive error handling with HTTPException
- OpenAPI/Swagger documentation auto-generated

**Endpoints**:
- `/`: Health check
- `/suggest_recipes`: POST, recipe suggestion
- `/substitute`: GET, ingredient substitution
- `/recipes/{recipe_title}`: GET, recipe details
- `/docs`: Swagger UI
- `/redoc`: ReDoc documentation

### Integration Points

1. **FastAPI ↔ Neo4j**: Via neo4j driver (GraphDatabase.driver)
2. **FastAPI ↔ ML Models**: Via utils layer (recipesuggestionmodel, SentenceTransformer)
3. **Data Loading**: CSV files → Neo4j (via database/load_into_neo4j.py)
4. **Model Training**: Separate pipeline scripts in pipelines/

### Sub-Tasks / Code Organization

1. **API Layer** (`api/`)
   - FastAPI route definitions
   - Request/response model validation
   - Error handling

2. **Service Layer** (`services/`)
   - Neo4j query abstractions
   - Business logic for substitutions

3. **Database Layer** (`database/`)
   - Graph bootstrap scripts
   - Relationship building
   - Graph exploration

4. **Utils Layer** (`utils/`)
   - ML model loading and inference
   - Recipe suggestion algorithm
   - Ingredient normalization

5. **Pipelines** (`pipelines/`)
   - Data preprocessing
   - Model training (separate from runtime)
   - Feature extraction

6. **Evaluation** (`evaluation/`)
   - Hybrid substitution implementation
   - Graph diagnostics
   - Performance analysis

---

## Testing

### General Approach

Testing strategy includes:
1. **Unit Tests**: Individual function/component testing
2. **Integration Tests**: API endpoint testing with mock Neo4j
3. **System Tests**: End-to-end testing with real Neo4j instance

**Test Framework**: pytest with pytest-asyncio for async endpoint testing

**Test Structure**: Tests located in `tests/` directory

### Test Configuration

- **pytest.ini**: Configured in pyproject.toml
- **Async Support**: pytest-asyncio for FastAPI async endpoints
- **Coverage**: pytest-cov for coverage reports (configured in Taskfile)

### Test Data

- Use fixtures for sample ingredients, recipes
- Mock Neo4j responses where appropriate
- Use test database instance for integration tests

### Test Execution

```bash
task test              # Run all tests
task coverage          # Run tests with coverage report
poetry run pytest      # Direct pytest execution
```

---

## Unit Tests

### Current Test Files

- `tests/test_main.py`: Basic API endpoint tests

### Recommended Unit Tests

1. **Recipe Suggestion Tests** (`tests/test_recipe_suggestion.py`):
   ```python
   def test_ingredient_embedding_generation()
   def test_faiss_similarity_search()
   def test_overlap_score_calculation()
   def test_combined_scoring_algorithm()
   def test_minimum_overlap_filtering()
   def test_rerank_weight_parameter()
   def test_empty_ingredient_list()
   def test_no_overlapping_recipes()
   def test_semantic_score_clamping()
   def test_ingredient_deduplication()
   ```

2. **Substitution Tests** (`tests/test_substitution.py`):
   ```python
   def test_ingredient_normalization()
   def test_normalize_with_determiners()
   def test_direct_substitution_queries()
   def test_cooccurrence_analysis()
   def test_hybrid_score_combination()
   def test_context_filtering()
   def test_fallback_to_general_substitutes()
   def test_normalization_factor_for_cooccurrence()
   def test_alpha_parameter_impact()
   def test_empty_substitution_results()
   ```

3. **Neo4j Service Tests** (`tests/test_neo4j_service.py`):
   ```python
   def test_neo4j_connection()
   def test_query_execution()
   def test_transaction_handling()
   def test_recipe_details_query()
   def test_case_insensitive_title_matching()
   def test_missing_recipe_handling()
   def test_session_cleanup()
   ```

4. **API Endpoint Tests** (`tests/test_api.py`):
   ```python
   def test_health_check_endpoint()
   def test_post_suggest_recipes_valid_input()
   def test_post_suggest_recipes_invalid_input()
   def test_get_substitute_valid_ingredient()
   def test_get_substitute_with_context()
   def test_get_substitute_hybrid_mode()
   def test_get_recipes_title_exists()
   def test_get_recipes_title_not_found()
   def test_request_validation()
   def test_error_handling()
   def test_cors_headers()
   def test_response_schema_validation()
   ```

5. **Data Loading Tests** (`tests/test_data_loading.py`):
   ```python
   def test_csv_parsing()
   def test_batch_processing()
   def test_graph_node_creation()
   def test_relationship_creation()
   def test_index_creation()
   def test_constraint_enforcement()
   def test_duplicate_handling()
   def test_bootstrap_workflow()
   ```

6. **Integration Tests** (`tests/test_integration.py`):
   ```python
   def test_full_recipe_suggestion_flow()
   def test_full_substitution_flow()
   def test_api_with_real_neo4j()
   def test_concurrent_requests()
   def test_end_to_end_workflow()
   ```

### Test Data Fixtures

**Sample Ingredients**:
```python
SAMPLE_INGREDIENTS = [
    ["butter", "sugar", "flour"],
    ["chicken", "onion", "garlic"],
    ["pasta", "tomato", "cheese"]
]
```

**Sample Recipes** (Mock):
```python
SAMPLE_RECIPES = [
    {
        "recipe_id": 1,
        "title": "Chocolate Chip Cookies",
        "NER": "['butter', 'sugar', 'flour', 'chocolate', 'egg']"
    },
    {
        "recipe_id": 2,
        "title": "Pasta Carbonara",
        "NER": "['pasta', 'egg', 'cheese', 'bacon', 'pepper']"
    }
]
```

**Sample Substitution Data** (Mock):
```python
SAMPLE_SUBSTITUTES = [
    {
        "ingredient": "butter",
        "substitute": "margarine",
        "score": 0.85,
        "context": "baking"
    }
]
```

### Test Coverage Goals

- **Target Coverage**: 80%+
- **Critical Paths**: 100% (API endpoints, core algorithms)
- **Utility Functions**: 70%+

---

## Appendix

### Configuration Examples

**Environment Variables (.env file)**:
```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
```

**Docker Compose Override**:
```yaml
services:
  api:
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=your_secure_password
```

### Example API Requests

**Recipe Suggestion**:
```bash
curl -X POST "http://localhost:8000/suggest_recipes" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": ["butter", "sugar", "flour"],
    "top_n": 5,
    "rerank_weight": 0.6
  }'
```

**Ingredient Substitution**:
```bash
curl "http://localhost:8000/substitute?ingredient=butter&context=baking&hybrid=true&top_k=5"
```

**Recipe Details**:
```bash
curl "http://localhost:8000/recipes/Marinated%20Flank%20Steak%20Recipe"
```

### Data Pipeline Flow

1. **Raw Data** → `src/data/raw/RecipeNLG_dataset.csv`
2. **Preprocessing** → Parsing, cleaning, NER extraction
3. **Feature Extraction** → Sentence embeddings, context vectors
4. **Model Training** → FAISS index creation, Word2Vec models
5. **Graph Loading** → CSV → Neo4j nodes/relationships
6. **Edge Building** → SUBSTITUTES_WITH, SIMILAR_TO edges

### Performance Benchmarks

**Recipe Suggestion**:
- FAISS search (50 candidates): ~10-20ms
- Overlap calculation: ~5-10ms
- Python processing: ~5-10ms
- Total (including API overhead): ~50-100ms

**Substitution Lookup**:
- Ingredient normalization: ~1-2ms
- Direct query: ~5-10ms
- Co-occurrence query: ~10-15ms
- Hybrid score combination: ~1-2ms
- Total (direct mode): ~10-15ms
- Total (hybrid mode): ~20-30ms

**Recipe Details Lookup**:
- Neo4j query: ~5-10ms
- Data parsing: ~1-2ms
- Total: ~10-15ms

### Performance Optimization Strategies

1. **FAISS Index Optimization**:
   - Use appropriate index type (IndexFlatIP for small datasets, IVF for large)
   - Pre-normalize vectors (L2 normalization) for cosine similarity via inner product
   - Tune `nprobe` parameter for IVF indices
   - Consider GPU acceleration for very large indices

2. **Neo4j Query Optimization**:
   - Ensure indexes exist: `CREATE CONSTRAINT ON (i:Ingredient) ASSERT i.name IS UNIQUE`
   - Use parameterized queries (already implemented)
   - Limit result sets appropriately
   - Use PROFILE to analyze query plans
   - Consider query caching for frequent patterns

3. **Model Loading Optimization**:
   - Load models once at startup (already implemented)
   - Use model caching (SentenceTransformer caches automatically)
   - Consider model quantization for smaller memory footprint

4. **Python Performance**:
   - Use list comprehensions over loops where possible
   - Use sets for O(1) membership testing (already implemented)
   - Minimize data copying
   - Use asyncio for concurrent I/O operations (already implemented)

5. **Caching Strategies**:
   - Cache recipe embeddings (already done via file)
   - Cache frequent substitution queries (e.g., Redis)
   - Cache recipe metadata in memory
   - Cache Neo4j query results for popular ingredients

### Scalability Limits

- **FAISS**: Tested with 100K+ vectors, scales to millions
- **Neo4j**: Supports billions of nodes/relationships
- **Current Architecture**: 
  - Handles ~10K recipes comfortably
  - Can scale to 100K+ recipes with current setup
  - For larger datasets, consider sharding or distributed systems

### Deployment Notes

1. **Production Recommendations**:
   - Use environment-specific Neo4j credentials
   - Restrict CORS origins
   - Enable HTTPS
   - Use production-grade Neo4j instance (not embedded)
   - Monitor disk space for Neo4j data volume
   - Set appropriate Neo4j memory limits
   - Use secrets management (e.g., Kubernetes secrets, AWS Secrets Manager)
   - Enable request rate limiting
   - Implement API authentication/authorization
   - Set up health check monitoring

2. **Scaling Considerations**:
   - FAISS index can be shared across API instances (read-only)
   - Neo4j supports clustering for high availability
   - Consider Redis caching for frequent queries
   - Load balancing for FastAPI instances
   - Horizontal scaling: Multiple FastAPI instances behind load balancer
   - Vertical scaling: Increase Neo4j memory for larger graphs
   - Read replicas: Neo4j read replicas for query distribution

3. **Data Backup**:
   - Backup Neo4j data volume regularly
   - Version control data processing scripts
   - Maintain backup of FAISS index and embeddings
   - Automated backup schedule (daily/weekly)
   - Test backup restoration procedures

4. **Security Considerations**:
   - **Authentication**: Implement API key or OAuth2
   - **Authorization**: Role-based access control if needed
   - **Input Validation**: Already implemented via Pydantic models
   - **SQL Injection Prevention**: Use parameterized queries (Neo4j driver handles this)
   - **Rate Limiting**: Prevent abuse (e.g., using slowapi or nginx)
   - **CORS**: Restrict allowed origins in production
   - **Secrets**: Never commit credentials, use environment variables or secrets management

5. **Monitoring & Observability**:
   - **Application Metrics**: Response times, request rates, error rates
   - **Neo4j Metrics**: Query performance, memory usage, connection pool
   - **System Metrics**: CPU, memory, disk usage
   - **Logging**: Centralized logging (e.g., ELK stack, CloudWatch)
   - **Alerting**: Set up alerts for errors, high latency, resource exhaustion
   - **Tracing**: Consider distributed tracing for complex request flows

6. **Performance Tuning**:
   - **FAISS Index**: Tune index parameters (e.g., nprobe for IVF indices)
   - **Neo4j**: Configure query timeout, connection pool size
   - **Caching**: Cache frequently accessed recipes/substitutes
   - **Async Operations**: Already using asyncio for I/O-bound operations
   - **Batch Processing**: For bulk operations, use batch APIs

### Troubleshooting Guide

1. **Models not loading**: Check data paths in config.paths
2. **Neo4j connection failed**: Verify container is running, check URI/credentials
3. **Empty recipe results**: Verify graph has been bootstrapped, check ingredient overlap threshold
4. **Slow queries**: Check Neo4j indexes, optimize FAISS index parameters

---

**Document Status**: Draft  
**Last Updated**: 2025-01-30  
**Next Review**: 2025-02-15

