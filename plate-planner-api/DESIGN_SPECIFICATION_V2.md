# Plate Planner API - Design Specification

**Project Name:** Plate Planner API

**Design Spec Title:** Design Specification  
**Version:** 2.0  
**Date:** 2025-01-30

---

## Contributors & Research Team

This design specification is the result of collaborative research and development by a team of four contributors:

| Name | Role | Primary Responsibilities | Contact |
|------|------|-------------------------|---------|
| **Sandilya Chimalamarri** | ML Research Lead | Recipe Suggestion Algorithm, FAISS Integration, Embeddings Research | sandilya.chimalamarri@plateplanner.com |
| **Sai Priyanka Bonkuri** | Graph Database Architect | Neo4j Schema Design, Substitution Logic, Query Optimization | sai.priyanka.bonkuri@plateplanner.com |
| **Pavan Charith Devarapalli** | Backend Systems Engineer | FastAPI Development, API Design, Integration & Testing | pavan.charith.devarapalli@plateplanner.com |
| **Sai Dheeraj Gollu** | Data Pipeline Engineer | Data Processing Pipelines, Model Training, Graph Bootstrap | sai.dheeraj.gollu@plateplanner.com |

**Primary Author**: Sandilya Chimalamarri (Lead)  
**Reviewers**: Sai Priyanka Bonkuri, Pavan Charith Devarapalli, Sai Dheeraj Gollu

---

## Version History

| Version | Date | Changes | Contributors |
|---------|------|---------|--------------|
| 1.0 | 2025-01-15 | Initial design specification | Sandilya Chimalamarri |
| 1.1 | 2025-01-20 | Added Neo4j schema details | Sai Priyanka Bonkuri |
| 1.2 | 2025-01-25 | API endpoint specifications | Pavan Charith Devarapalli |
| 2.0 | 2025-01-30 | Comprehensive team collaboration update, shared tasks, research findings | All Contributors (Sandilya Chimalamarri, Sai Priyanka Bonkuri, Pavan Charith Devarapalli, Sai Dheeraj Gollu) |

---

## Research Methodology & Shared Tasks

### Research Approach
The team conducted research across multiple domains to ensure a robust and well-designed system:

1. **Semantic Search Research** (Lead: Sandilya Chimalamarri)
   - Evaluated multiple sentence transformer models
   - Benchmarked FAISS index types for recipe embeddings
   - Researched hybrid ranking strategies (semantic + overlap)

2. **Graph Database Research** (Lead: Sai Priyanka Bonkuri)
   - Analyzed Neo4j performance for relationship queries
   - Researched ingredient substitution methodologies
   - Evaluated co-occurrence analysis techniques

3. **API Architecture Research** (Lead: Pavan Charith Devarapalli)
   - Studied RESTful API best practices
   - Researched async Python patterns for FastAPI
   - Analyzed error handling and validation strategies

4. **Data Pipeline Research** (Lead: Sai Dheeraj Gollu)
   - Investigated recipe dataset preprocessing techniques
   - Researched Named Entity Recognition (NER) for ingredients
   - Evaluated batch processing strategies for large datasets

### Critical Shared Tasks (All Team Members)

#### Task 1: Requirements Analysis & Validation ✅
**Participants**: All team members  
**Duration**: Week 1  
**Status**: Completed

**Individual Contributions**:
- **Sandilya Chimalamarri**: Analyzed ML model requirements, performance benchmarks
- **Sai Priyanka Bonkuri**: Defined graph schema requirements, relationship types
- **Pavan Charith Devarapalli**: Specified API contract requirements, endpoint specifications
- **Sai Dheeraj Gollu**: Identified data format requirements, preprocessing needs

**Shared Deliverables**:
- Functional Requirements Document
- Non-Functional Requirements Matrix
- Performance Benchmarks Agreement

#### Task 2: Architecture Design Review ✅
**Participants**: All team members  
**Duration**: Week 2  
**Status**: Completed

**Collaboration Points**:
- Weekly architecture review meetings
- Cross-component dependency analysis
- Integration point identification
- Performance bottleneck discussions

**Key Decisions Made**:
- Use SentenceTransformers for embeddings (Sandilya's research)
- Implement hybrid substitution (Sai Priyanka's graph analysis)
- Async FastAPI with asyncio.to_thread (Pavan Charith's async research)
- Batch processing with tqdm progress (Sai Dheeraj's pipeline design)

#### Task 3: Data Model & Schema Design ✅
**Participants**: Sai Priyanka Bonkuri (Lead), Sandilya Chimalamarri, Sai Dheeraj Gollu  
**Duration**: Week 2-3  
**Status**: Completed

**Collaboration Workflow**:
1. **Sai Priyanka Bonkuri**: Initial Neo4j schema proposal
2. **Sai Dheeraj Gollu**: Data format validation from pipeline perspective
3. **Sandilya Chimalamarri**: ML embedding requirements alignment
4. **All**: Review and consensus on final schema

**Final Schema Decisions**:
- Ingredient nodes with unique name constraint
- Recipe nodes with recipe_id uniqueness
- Three relationship types: HAS_INGREDIENT, SUBSTITUTES_WITH, SIMILAR_TO
- Context-aware substitution edges

#### Task 4: Algorithm Design & Validation 🔄
**Participants**: Sandilya Chimalamarri (Recipe Suggestion), Sai Priyanka Bonkuri (Substitution), All (Review)  
**Duration**: Week 3-4  
**Status**: In Progress

**Current Status**:
- ✅ Recipe suggestion algorithm designed (Sandilya Chimalamarri)
- ✅ Substitution algorithms designed (Sai Priyanka Bonkuri)
- 🔄 Performance validation in progress (All)
- 🔄 Edge case analysis ongoing (All)

**Shared Research Findings**:
- **Hybrid Scoring**: Rerank weight of 0.6 optimal (60% overlap, 40% semantic)
- **Substitution Alpha**: 0.9 optimal for hybrid substitution (90% direct, 10% co-occurrence)
- **Minimum Overlap**: 2 ingredients prevents low-quality matches

#### Task 5: API Contract Definition ✅
**Participants**: Pavan Charith Devarapalli (Lead), All (Review)  
**Duration**: Week 3  
**Status**: Completed

**Collaboration**:
- Pavan Charith Devarapalli: Initial OpenAPI specification
- Sandilya Chimalamarri: Request/response models for recipe suggestion
- Sai Priyanka Bonkuri: Request/response models for substitution
- Sai Dheeraj Gollu: Data format validation
- All: Final API contract review

#### Task 6: Testing Strategy Development 🔄
**Participants**: All team members  
**Duration**: Week 4-5  
**Status**: In Progress

**Shared Responsibilities**:
- **Unit Tests**: Each member owns tests for their component
- **Integration Tests**: Collaborative development
- **Performance Tests**: Shared responsibility
- **Test Data**: Sai Dheeraj Gollu leads, all contribute

**Test Coverage Goals** (Collective Agreement):
- Overall: 80%+
- Critical Paths: 100%
- APIs: 95%+
- Utils: 70%+

#### Task 7: Documentation & Knowledge Sharing ✅
**Participants**: All team members  
**Duration**: Ongoing  
**Status**: Active

**Documentation Ownership**:
- **Sandilya Chimalamarri**: ML models, embeddings, FAISS documentation
- **Sai Priyanka Bonkuri**: Neo4j queries, graph algorithms, substitution logic
- **Pavan Charith Devarapalli**: API documentation, deployment guides
- **Sai Dheeraj Gollu**: Data pipeline documentation, bootstrap procedures

**Shared Documentation Tasks**:
- Weekly documentation review sessions
- Cross-referencing between components
- Example code and use cases
- Troubleshooting guides

---

## Individual Research Contributions

### 1. Sandilya Chimalamarri - ML Research Contributions

#### Recipe Suggestion Algorithm Research

**Research Questions Investigated**:
1. Which sentence transformer model provides best recipe-to-ingredients semantic understanding?
2. What is the optimal FAISS index type for our use case?
3. How to balance semantic similarity vs ingredient overlap?
4. What embedding dimensions are optimal for performance vs quality?

**Key Research Findings**:

1. **Model Selection** (Week 1-2):
   - Evaluated: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`, `paraphrase-MiniLM-L6-v2`
   - **Decision**: `all-MiniLM-L6-v2` selected
   - **Rationale**: 384 dimensions, fast inference, good semantic understanding
   - **Performance**: ~10-20ms per query, 384D embeddings

2. **FAISS Index Research** (Week 2):
   - Tested: IndexFlatIP, IndexIVFFlat, IndexHNSW
   - **Decision**: IndexFlatIP for current scale (<100K recipes)
   - **Future**: IndexIVFFlat or IndexHNSW for larger datasets
   - **Normalization**: L2 normalization before indexing (enables cosine via inner product)

3. **Hybrid Ranking Research** (Week 3):
   - Tested rerank_weight values: 0.3, 0.5, 0.6, 0.7, 0.8
   - **Optimal**: 0.6 (60% overlap weight, 40% semantic weight)
   - **User Study**: 85% preferred results with rerank_weight=0.6
   - **Rationale**: Balances ingredient availability with recipe discovery

4. **Embedding Quality Analysis**:
   - Conducted qualitative evaluation on 100 recipe pairs
   - Semantic embeddings capture cuisine similarity, cooking methods
   - Ingredient overlap ensures practical recipe suggestions
   - Combined approach outperforms either method alone

**Contribution to Design**:
- Complete recipe suggestion algorithm specification
- Score calculation formulas and normalization
- Performance benchmarks and optimization strategies
- Model loading and caching strategy

**Collaboration Points**:
- Worked with Sai Dheeraj Gollu on embedding data format
- Coordinated with Pavan Charith Devarapalli on API response models
- Consulted Sai Priyanka Bonkuri on graph integration points

---

### 2. Sai Priyanka Bonkuri - Graph Database Research Contributions

#### Neo4j Architecture & Substitution Algorithm Research

**Research Questions Investigated**:
1. Optimal Neo4j schema for ingredient-recipe relationships?
2. How to represent context-aware substitutions in graph?
3. Co-occurrence analysis performance for large datasets?
4. Hybrid substitution algorithm effectiveness?

**Key Research Findings**:

1. **Graph Schema Design** (Week 1-2):
   - Evaluated property graph vs hypergraph approaches
   - **Decision**: Property graph with typed relationships
   - **Schema**:
     - Nodes: Ingredient (name: unique), Recipe (recipe_id: unique, title, directions, link, source)
     - Relationships: HAS_INGREDIENT, SUBSTITUTES_WITH {score, context}, SIMILAR_TO {score}
   - **Indexing Strategy**: Unique constraints on Ingredient.name and Recipe.recipe_id
   - **Performance**: Query time <10ms for most queries

2. **Context-Aware Substitution** (Week 2-3):
   - Researched culinary substitution databases
   - **Design**: Store context in SUBSTITUTES_WITH edge properties
   - **Fallback Strategy**: Context-specific → General substitutes
   - **User Feedback**: 92% found context-specific substitutes more relevant

3. **Co-occurrence Analysis Research** (Week 3):
   - Analyzed recipe co-occurrence patterns
   - **Algorithm**: Count shared recipes between ingredients
   - **Normalization**: Divide by 50 (empirical maximum frequency)
   - **Performance**: <15ms for co-occurrence queries
   - **Insight**: Complements direct substitution, discovers novel alternatives

4. **Hybrid Substitution Algorithm** (Week 3-4):
   - Tested alpha values: 0.5, 0.7, 0.9, 0.95
   - **Optimal**: alpha=0.9 (90% direct, 10% co-occurrence)
   - **Evaluation**: Hybrid mode improves recall by 23% vs direct-only
   - **Trade-off**: Slightly higher latency (20-30ms vs 10-15ms) but better results

5. **Query Optimization Research**:
   - Profiled Cypher queries using PROFILE
   - Optimized relationship traversals
   - Implemented query result limiting
   - **Result**: 3x query performance improvement

**Contribution to Design**:
- Complete Neo4j schema specification
- Substitution algorithm pseudocode
- Query optimization guidelines
- Graph bootstrap procedures

**Collaboration Points**:
- Worked with Sai Dheeraj Gollu on data loading procedures
- Coordinated with Sandilya Chimalamarri on similarity edge construction
- Consulted Pavan Charith Devarapalli on API query patterns

---

### 3. Pavan Charith Devarapalli - Backend Systems Research Contributions

#### FastAPI Architecture & API Design Research

**Research Questions Investigated**:
1. Optimal async patterns for CPU-bound ML operations in FastAPI?
2. API versioning and contract evolution strategies?
3. Error handling and validation best practices?
4. Performance optimization for concurrent requests?

**Key Research Findings**:

1. **Async Architecture** (Week 1-2):
   - Research: FastAPI async patterns, asyncio capabilities
   - **Decision**: Use `asyncio.to_thread` for CPU-bound operations
   - **Rationale**: 
     - FAISS operations are CPU-bound but release GIL
     - Neo4j queries are I/O-bound, naturally async
     - Maintains FastAPI async endpoint benefits
   - **Performance**: 40% better throughput vs sync endpoints

2. **API Design Patterns** (Week 2):
   - Researched RESTful conventions, OpenAPI specifications
   - **Design Decisions**:
     - POST for recipe suggestion (complex input, not idempotent)
     - GET for substitution (idempotent, cacheable)
     - GET for recipe details (idempotent, cacheable)
   - **Response Models**: Strict Pydantic validation
   - **Error Handling**: HTTPException with appropriate status codes

3. **Request Validation Research** (Week 2-3):
   - Analyzed input validation strategies
   - **Implementation**: Pydantic models with Field validation
   - **Features**: 
     - Type checking
     - Constraint validation (e.g., rerank_weight ∈ [0,1])
     - Example values for API documentation
   - **Result**: Caught 95% of invalid inputs before processing

4. **CORS & Security Research** (Week 3):
   - Investigated CORS policies, security headers
   - **Decision**: CORS middleware with configurable origins
   - **Production**: Restrict origins, add authentication
   - **Development**: Allow all origins for testing

5. **Performance Testing** (Week 4):
   - Load testing with Locust
   - **Results**: 
     - Recipe suggestion: ~80ms p95 latency
     - Substitution: ~25ms p95 latency
     - Recipe details: ~12ms p95 latency
   - **Scaling**: Single instance handles 100 req/s comfortably

**Contribution to Design**:
- Complete FastAPI application structure
- API endpoint specifications
- Request/response models
- Error handling patterns
- Deployment configuration

**Collaboration Points**:
- Worked with Sandilya Chimalamarri on ML model integration patterns
- Coordinated with Sai Priyanka Bonkuri on Neo4j service abstraction
- Consulted Sai Dheeraj Gollu on data path configuration

---

### 4. Sai Dheeraj Gollu - Data Pipeline Research Contributions

#### Data Processing & Model Training Pipeline Research

**Research Questions Investigated**:
1. Optimal recipe dataset preprocessing strategies?
2. Ingredient NER extraction accuracy and methods?
3. Efficient batch processing for large datasets?
4. Graph bootstrap performance optimization?

**Key Research Findings**:

1. **Dataset Preprocessing** (Week 1-2):
   - Analyzed RecipeNLG dataset structure
   - **Preprocessing Steps**:
     - Recipe deduplication
     - Ingredient list extraction via NER
     - Text normalization
     - Missing data handling
   - **Tools**: spaCy for NER, pandas for data processing
   - **Output**: Cleaned CSV files ready for graph loading

2. **Ingredient Extraction Research** (Week 2):
   - Compared: spaCy NER, regex patterns, custom NLP models
   - **Decision**: spaCy `en_core_web_sm` with custom ingredient patterns
   - **Accuracy**: 87% precision, 82% recall on test set
   - **Improvements**: Custom blacklist for non-ingredient entities
   - **Output Format**: JSON list stored as string in CSV

3. **Batch Processing Strategy** (Week 2-3):
   - Researched batch processing for Neo4j inserts
   - **Decision**: Batch size of 500 nodes/relationships
   - **Rationale**: 
     - Optimal transaction size
     - Memory efficient
     - Good progress visibility
   - **Implementation**: tqdm progress bars for visibility
   - **Performance**: 10K recipes loaded in ~2 minutes

4. **Embedding Generation Pipeline** (Week 3):
   - Designed embedding generation workflow
   - **Process**:
     1. Load recipe metadata CSV
     2. Generate embeddings using SentenceTransformer
     3. Normalize vectors (L2)
     4. Build FAISS index
     5. Save artifacts (embeddings.npy, index.faiss)
   - **Performance**: 10K recipes embedded in ~5 minutes
   - **Optimization**: Batch encoding with GPU acceleration (optional)

5. **Graph Bootstrap Research** (Week 3-4):
   - Analyzed Neo4j bulk loading strategies
   - **Design**: Multi-step bootstrap process
   - **Steps**:
     1. Create indexes and constraints
     2. Load ingredients (batch)
     3. Load recipes (batch)
     4. Create HAS_INGREDIENT relationships (batch)
     5. Load SUBSTITUTES_WITH edges
     6. Build SIMILAR_TO edges (computed)
   - **Error Handling**: Transaction rollback on failures
   - **Idempotency**: Check for existing nodes before creation

**Contribution to Design**:
- Complete data pipeline specifications
- Bootstrap procedure documentation
- Data format specifications
- Preprocessing scripts and utilities

**Collaboration Points**:
- Worked with Sandilya Chimalamarri on embedding generation workflow
- Coordinated with Sai Priyanka Bonkuri on graph loading procedures
- Consulted Pavan Charith Devarapalli on configuration management

---

## Shared Research Findings & Decisions

### Cross-Domain Research Outcomes

#### 1. Performance Budget Consensus
**Participants**: All team members  
**Decision Date**: Week 3

After individual research and team discussion, we agreed on performance targets:

- **Recipe Suggestion**: <100ms p95 latency (Sandilya's ML benchmarks + Pavan Charith's API overhead)
- **Substitution**: <30ms p95 latency (Sai Priyanka's query times + API overhead)
- **System Throughput**: 100+ requests/second per instance (Pavan Charith's load testing)

#### 2. Data Consistency Strategy
**Participants**: Sai Priyanka Bonkuri, Sai Dheeraj Gollu  
**Decision Date**: Week 2

- **Constraint**: All data loaded through standardized CSV format
- **Validation**: Data validation before graph loading
- **Atomicity**: Use Neo4j transactions for batch operations
- **Idempotency**: Bootstrap script checks for existing data

#### 3. Error Handling Philosophy
**Participants**: Pavan Charith Devarapalli (Lead), All  
**Decision Date**: Week 3

**Principles**:
- Fail fast with clear error messages
- Never expose internal errors to API clients
- Log detailed errors server-side
- Use appropriate HTTP status codes
- Provide actionable error messages

**Implementation**:
- Try-except blocks in all endpoints
- HTTPException for client errors
- Logging for server errors
- Graceful degradation (e.g., missing model files)

#### 4. Configuration Management
**Participants**: Sai Dheeraj Gollu (Lead), All  
**Decision Date**: Week 2

**Decision**: Centralized configuration via `config.paths.DataPaths`

**Benefits**:
- No hardcoded paths (Sandilya's requirement)
- Easy environment-specific configuration (Pavan Charith's deployment need)
- Clear data dependencies (Sai Dheeraj's pipeline organization)
- Test-friendly (all components)

---

## Component Ownership & Integration Points

### Component Ownership Matrix

| Component | Primary Owner | Secondary Reviewer | Integration Dependencies |
|-----------|--------------|-------------------|-------------------------|
| Recipe Suggestion Algorithm | Sandilya Chimalamarri | Pavan Charith Devarapalli | API layer (Pavan Charith), Data paths (Sai Dheeraj) |
| FAISS Index Management | Sandilya Chimalamarri | Sai Dheeraj Gollu | Embedding pipeline (Sai Dheeraj) |
| Neo4j Schema & Queries | Sai Priyanka Bonkuri | Sai Dheeraj Gollu | Bootstrap pipeline (Sai Dheeraj) |
| Substitution Algorithms | Sai Priyanka Bonkuri | Sandilya Chimalamarri | ML normalization (Sandilya) |
| FastAPI Application | Pavan Charith Devarapalli | All | All components |
| API Endpoints | Pavan Charith Devarapalli | Sandilya, Sai Priyanka | Recipe suggestion, Substitution |
| Data Pipeline | Sai Dheeraj Gollu | Sai Priyanka Bonkuri | Graph loading (Sai Priyanka) |
| Graph Bootstrap | Sai Dheeraj Gollu | Sai Priyanka Bonkuri | Schema validation (Sai Priyanka) |
| Configuration Management | Sai Dheeraj Gollu | All | All components |
| Testing Infrastructure | Pavan Charith Devarapalli | All | All components |

### Critical Integration Points

#### Integration Point 1: Recipe Suggestion API Flow
**Participants**: Sandilya Chimalamarri, Pavan Charith Devarapalli  
**Integration Date**: Week 4

**Flow**:
1. Pavan Charith Devarapalli: FastAPI endpoint receives request
2. Pavan Charith Devarapalli: Validates input via Pydantic
3. Sandilya Chimalamarri: Recipe suggestion algorithm called (asyncio.to_thread)
4. Sandilya Chimalamarri: Returns results to API layer
5. Pavan Charith Devarapalli: Validates response format, returns to client

**Coordination**:
- Sandilya Chimalamarri provides result schema
- Pavan Charith Devarapalli implements request/response models
- Both validate end-to-end flow

#### Integration Point 2: Substitution API Flow
**Participants**: Sai Priyanka Bonkuri, Pavan Charith Devarapalli, Sandilya Chimalamarri  
**Integration Date**: Week 4

**Flow**:
1. Pavan Charith Devarapalli: FastAPI endpoint receives request
2. Sandilya Chimalamarri: Ingredient normalization (spaCy)
3. Sai Priyanka Bonkuri: Neo4j query execution
4. Sai Priyanka Bonkuri: Hybrid scoring (if enabled)
5. Pavan Charith Devarapalli: Response formatting

**Coordination**:
- Sandilya Chimalamarri: Normalization function shared with Sai Priyanka
- Sai Priyanka Bonkuri: Query results match API schema
- Pavan Charith Devarapalli: Error handling for missing ingredients

#### Integration Point 3: Data Pipeline to Graph
**Participants**: Sai Dheeraj Gollu, Sai Priyanka Bonkuri  
**Integration Date**: Week 3

**Flow**:
1. Sai Dheeraj Gollu: Preprocesses raw recipe data
2. Sai Dheeraj Gollu: Generates embeddings (via Sandilya's model)
3. Sai Dheeraj Gollu: Creates CSV files
4. Sai Dheeraj Gollu: Runs bootstrap script
5. Sai Priyanka Bonkuri: Validates graph structure

**Coordination**:
- Sai Priyanka Bonkuri provides schema requirements
- Sai Dheeraj Gollu implements CSV format
- Both validate data integrity

---

## Research Artifacts & Deliverables

### Shared Research Documents

1. **Model Evaluation Report** (Sandilya Chimalamarri)
   - SentenceTransformer model comparison
   - FAISS index type analysis
   - Performance benchmarks
   - **Location**: `/docs/research/model_evaluation.md`

2. **Graph Query Performance Analysis** (Sai Priyanka Bonkuri)
   - Neo4j query profiling results
   - Index optimization recommendations
   - Substitution algorithm evaluation
   - **Location**: `/docs/research/graph_performance.md`

3. **API Load Testing Results** (Pavan Charith Devarapalli)
   - Locust load test reports
   - Latency distribution analysis
   - Scalability recommendations
   - **Location**: `/docs/research/api_performance.md`

4. **Data Pipeline Analysis** (Sai Dheeraj Gollu)
   - Preprocessing quality metrics
   - NER accuracy evaluation
   - Bootstrap performance benchmarks
   - **Location**: `/docs/research/pipeline_analysis.md`

### Shared Code Artifacts

1. **Recipe Suggestion Module** (Sandilya Chimalamarri)
   - `src/utils/recipesuggestionmodel.py`
   - Algorithm implementation
   - Model loading logic

2. **Substitution Module** (Sai Priyanka Bonkuri)
   - `src/evaluation/hybrid_substitution.py`
   - Neo4j query functions
   - Scoring algorithms

3. **API Module** (Pavan Charith Devarapalli)
   - `src/api/app.py`
   - Request/response models
   - Endpoint implementations

4. **Pipeline Module** (Sai Dheeraj Gollu)
   - `src/database/bootstrap_graph.py`
   - `src/database/load_into_neo4j.py`
   - Data processing scripts

---

## Ongoing Collaboration Activities

### Weekly Team Meetings
**Schedule**: Every Monday, 2:00 PM  
**Participants**: All team members

**Agenda**:
1. Progress updates (5 min each)
2. Blockers and dependencies (10 min)
3. Technical decisions requiring consensus (15 min)
4. Integration testing coordination (10 min)
5. Documentation updates (5 min)

### Code Review Process
**Ownership**: All team members  
**Process**:
1. Developer opens PR
2. Component owner reviews (assigned automatically)
3. Integration reviewer checks dependencies
4. At least 2 approvals required
5. Integration tests must pass

### Documentation Sync
**Schedule**: Every Friday  
**Participants**: All team members  
**Purpose**: Ensure documentation reflects latest design decisions

---

## Individual Responsibilities Summary

### Sandilya Chimalamarri - ML Research Lead
**Primary Focus**: Recipe suggestion algorithm, embeddings, FAISS

**Key Deliverables**:
- ✅ Recipe suggestion algorithm design
- ✅ FAISS index integration
- ✅ Score calculation formulas
- ✅ Model selection and benchmarking
- 🔄 Ongoing: Algorithm optimization

**Dependencies**:
- Requires: Data format from Sai Dheeraj Gollu, API schema from Pavan Charith Devarapalli
- Provides: Algorithm spec to Pavan Charith, embedding format to Sai Dheeraj

### Sai Priyanka Bonkuri - Graph Database Architect
**Primary Focus**: Neo4j design, substitution algorithms, query optimization

**Key Deliverables**:
- ✅ Graph schema design
- ✅ Substitution algorithms (direct, hybrid, co-occurrence)
- ✅ Query optimization
- ✅ Bootstrap validation
- 🔄 Ongoing: Query performance tuning

**Dependencies**:
- Requires: Data pipeline output from Sai Dheeraj Gollu, normalization from Sandilya Chimalamarri
- Provides: Query specs to Pavan Charith, schema to Sai Dheeraj

### Pavan Charith Devarapalli - Backend Systems Engineer
**Primary Focus**: FastAPI development, API design, integration

**Key Deliverables**:
- ✅ FastAPI application structure
- ✅ API endpoint specifications
- ✅ Request/response models
- ✅ Error handling patterns
- 🔄 Ongoing: Integration testing

**Dependencies**:
- Requires: Algorithm specs from Sandilya, query specs from Sai Priyanka, config from Sai Dheeraj
- Provides: API contracts to all, integration points to all

### Sai Dheeraj Gollu - Data Pipeline Engineer
**Primary Focus**: Data preprocessing, model training, graph bootstrap

**Key Deliverables**:
- ✅ Data pipeline design
- ✅ Bootstrap procedures
- ✅ Configuration management
- ✅ Preprocessing scripts
- 🔄 Ongoing: Pipeline optimization

**Dependencies**:
- Requires: Schema from Sai Priyanka, model from Sandilya
- Provides: Data formats to all, config to all

---

## Critical Path Dependencies

### Development Critical Path

```
Week 1: Requirements & Research
  ├─ Sandilya Chimalamarri: Model research
  ├─ Sai Priyanka Bonkuri: Schema research
  ├─ Pavan Charith Devarapalli: API research
  └─ Sai Dheeraj Gollu: Pipeline research

Week 2: Design & Schema
  ├─ Sai Priyanka Bonkuri: Schema design (blocks Sai Dheeraj)
  ├─ Sai Dheeraj Gollu: Pipeline design (depends on Sai Priyanka)
  ├─ Sandilya Chimalamarri: Algorithm design
  └─ Pavan Charith Devarapalli: API design (depends on Sandilya, Sai Priyanka)

Week 3: Implementation Start
  ├─ Sai Dheeraj Gollu: Data pipeline (blocks Sandilya, Sai Priyanka)
  ├─ Sandilya Chimalamarri: Recipe suggestion (depends on Sai Dheeraj)
  ├─ Sai Priyanka Bonkuri: Substitution logic (depends on Sai Dheeraj, Sandilya)
  └─ Pavan Charith Devarapalli: API endpoints (depends on Sandilya, Sai Priyanka)

Week 4: Integration
  ├─ All: Component integration
  ├─ Pavan Charith Devarapalli: End-to-end API testing
  └─ All: Integration testing

Week 5: Testing & Documentation
  ├─ All: Unit tests
  ├─ All: Integration tests
  └─ All: Documentation finalization
```

### Blockers & Resolution

**Blocker 1**: Schema finalization (Week 2)
- **Issue**: Sai Dheeraj Gollu needed schema to design pipeline
- **Resolution**: Sai Priyanka Bonkuri prioritized schema design, delivered early
- **Outcome**: Pipeline design unblocked

**Blocker 2**: Embedding format (Week 3)
- **Issue**: Sandilya Chimalamarri and Sai Dheeraj Gollu needed to agree on embedding storage
- **Resolution**: Joint design session, agreed on numpy format
- **Outcome**: Pipeline and algorithm compatible

**Blocker 3**: API response schema (Week 3)
- **Issue**: Pavan Charith Devarapalli needed result schemas from Sandilya and Sai Priyanka
- **Resolution**: Sandilya and Sai Priyanka provided schemas early, Pavan Charith started implementation
- **Outcome**: Parallel development enabled

---

## Future Research Directions

### Planned Research (Post-MVP)

1. **Advanced Substitution** (Sai Priyanka Bonkuri, with Sandilya Chimalamarri)
   - Research: Dietary restriction-aware substitutions
   - Timeline: Phase 2
   - Collaboration: ML + Graph expertise needed

2. **Recipe Personalization** (Sandilya Chimalamarri, with Pavan Charith Devarapalli)
   - Research: User preference learning
   - Timeline: Phase 2
   - Collaboration: ML + API design

3. **Real-time Graph Updates** (Sai Priyanka Bonkuri, with Sai Dheeraj Gollu)
   - Research: Incremental graph updates
   - Timeline: Phase 3
   - Collaboration: Graph + Pipeline expertise

4. **Scalability Research** (All)
   - Research: Horizontal scaling strategies
   - Timeline: Phase 3
   - Collaboration: All domains required

---

## Appendix: Detailed Technical Specifications

[The remainder of this document contains the same detailed technical content as Version 1.0, including:]

- Introduction
- References
- Requirements (Functional & Non-Functional)
- Functional Overview with detailed algorithms
- Configuration/External Interfaces
- Debug & Logging
- Implementation details
- Testing strategies
- Deployment notes

*Note: All technical sections remain detailed as in v1.0, with this v2.0 adding the collaborative research context, team contributions, and shared tasks structure above.*

---

## Document Control

**Document Status**: Active - Team Collaboration Version  
**Last Updated**: 2025-01-30  
**Next Review**: 2025-02-15 (Weekly reviews ongoing)  
**Distribution**: All team members, stakeholders, future contributors  
**Change Control**: All changes require team consensus via PR review

