# Recipe Generation Flow Architecture
## Plate Planner API - Technical Documentation

**Author:** Sandilya Chimalamarri  
**Date:** November 20, 2025  
**Version:** 1.0  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Components](#2-architecture-components)
3. [Recipe Generation Flow](#3-recipe-generation-flow)
4. [Technology Stack](#4-technology-stack)
5. [Code Implementation](#5-code-implementation)
6. [Neo4j vs FAISS: Role Clarification](#6-neo4j-vs-faiss-role-clarification)
7. [API Endpoints](#7-api-endpoints)
8. [Example Requests and Responses](#8-example-requests-and-responses)
9. [Performance Characteristics](#9-performance-characteristics)
10. [Design Rationale](#10-design-rationale)

---

## 1. System Overview

### 1.1 Purpose

The Plate Planner API provides intelligent recipe recommendations based on user-provided ingredients. The system employs a **hybrid architecture** combining:

- **FAISS (Facebook AI Similarity Search)** for semantic recipe retrieval at scale
- **Neo4j Graph Database** for relationship-based operations (substitutions, details)
- **SentenceTransformers** for encoding semantic meaning
- **Word2Vec** for ingredient similarity modeling

### 1.2 Key Features

| Feature | Technology | Purpose |
|---------|------------|---------|
| Recipe Search from Ingredients | FAISS + SentenceTransformer | Fast semantic similarity search (2.2M recipes) |
| Ingredient Substitution | Neo4j + Word2Vec | Context-aware substitution recommendations |
| Recipe Detail Retrieval | Neo4j Graph Traversal | Fetch ingredients, directions, metadata |
| Ingredient Similarity | Neo4j SIMILAR_TO edges | Find related ingredients |

---

## 2. Architecture Components

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MOBILE APPLICATION                        │
│                   (iOS / Android / Web Client)                  │
│                                                                  │
│  User Actions:                                                   │
│  • Upload pantry list: ["chicken", "tomato", "garlic"]         │
│  • Click "Generate Recipes" button                             │
│  • View recipe details                                          │
│  • Request ingredient substitutions                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ REST API (JSON over HTTP)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      FASTAPI BACKEND                             │
│                    (src/api/app.py)                             │
│                                                                  │
│  Endpoints:                                                      │
│  • POST /suggest_recipes        → Recipe generation            │
│  • GET  /substitute             → Ingredient substitution      │
│  • GET  /recipes/{title}        → Recipe details               │
│  • GET  /                       → Health check                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
        ┌───────────▼──────┐    ┌────▼──────────────┐
        │  RECIPE ENGINE   │    │  NEO4J SERVICE    │
        │  (FAISS-based)   │    │  (Graph Queries)  │
        └───────────┬──────┘    └────┬──────────────┘
                    │                 │
        ┌───────────▼──────────────────▼──────────────┐
        │         DATA LAYER & ML MODELS               │
        │                                              │
        │  ┌──────────────┐  ┌─────────────────────┐ │
        │  │   FAISS      │  │  SentenceTransformer│ │
        │  │ Vector Index │  │   (all-MiniLM-L6)   │ │
        │  │ 50K-2.2M     │  │   384-dim vectors   │ │
        │  │  recipes     │  │                     │ │
        │  └──────────────┘  └─────────────────────┘ │
        │                                              │
        │  ┌──────────────┐  ┌─────────────────────┐ │
        │  │   Neo4j      │  │    Word2Vec Model   │ │
        │  │ Graph DB     │  │   100-dim vectors   │ │
        │  │ 100K recipes │  │  Ingredient         │ │
        │  │              │  │  similarity         │ │
        │  └──────────────┘  └─────────────────────┘ │
        └──────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

#### **FAISS Index**
- **Purpose:** Ultra-fast approximate nearest neighbor search
- **Data:** 50,000 - 2.2M recipe embeddings (384-dimensional vectors)
- **Search Time:** 5-10ms for top-k retrieval
- **Use Case:** Primary recipe search engine

#### **SentenceTransformer**
- **Model:** `all-MiniLM-L6-v2` (22M parameters)
- **Input:** Text strings (e.g., "chicken, tomato, garlic")
- **Output:** 384-dimensional semantic embeddings
- **Use Case:** Convert ingredients to searchable vectors

#### **Neo4j Graph Database**
- **Nodes:** Ingredients (100K unique), Recipes (100K)
- **Relationships:** HAS_INGREDIENT, SUBSTITUTES_WITH, SIMILAR_TO
- **Use Case:** Relationship queries, substitutions, recipe details

#### **Word2Vec Model**
- **Training Data:** 100K recipe ingredient sequences
- **Vector Size:** 100 dimensions
- **Use Case:** Ingredient similarity for SIMILAR_TO edges

---

## 3. Recipe Generation Flow

### 3.1 Complete User Journey

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: USER INPUT                                              │
│ Mobile App Interface                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User uploads pantry list:                                       │
│  ┌───────────────────────────────────────────────────┐         │
│  │ 🥕 Pantry Ingredients:                             │         │
│  │  • chicken                                         │         │
│  │  • tomato                                          │         │
│  │  • garlic                                          │         │
│  │  • rice                                            │         │
│  │                                                    │         │
│  │  [Generate Recipes 🍳]                            │         │
│  └───────────────────────────────────────────────────┘         │
│                                                                  │
│  User clicks: "Generate Recipes"                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP POST Request
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ STEP 2: API REQUEST                                             │
│ REST API Call                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST http://localhost:8000/suggest_recipes                     │
│                                                                  │
│  Request Body (JSON):                                            │
│  {                                                               │
│    "ingredients": ["chicken", "tomato", "garlic", "rice"],     │
│    "top_n": 5,                                                  │
│    "rerank_weight": 0.6                                         │
│  }                                                               │
│                                                                  │
│  Headers:                                                        │
│  Content-Type: application/json                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ FastAPI receives request
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ STEP 3: FASTAPI ENDPOINT HANDLER                                │
│ src/api/app.py                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  @app.post("/suggest_recipes")                                  │
│  async def suggest_recipes_endpoint(request: RecipeRequest):    │
│      try:                                                        │
│          results = await asyncio.to_thread(                     │
│              suggest_recipes,          # ← Core function        │
│              request.ingredients,                                │
│              request.top_n,                                      │
│              request.rerank_weight,                              │
│          )                                                       │
│      except Exception:                                           │
│          raise HTTPException(500, "Recipe generation failed")   │
│                                                                  │
│      return results                                              │
│                                                                  │
│  NOTE: Uses asyncio.to_thread() for non-blocking execution      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Calls suggest_recipes()
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ STEP 4: RECIPE SUGGESTION ENGINE                                │
│ src/utils/recipesuggestionmodel.py                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  def suggest_recipes(ingredients, top_n=5, rerank_weight=0.6):  │
│                                                                  │
│      # PHASE A: Text → Vector Embedding                         │
│      ┌──────────────────────────────────────────────┐          │
│      │ Input: ["chicken", "tomato", "garlic", "rice"]│          │
│      │        ↓                                      │          │
│      │ Join:  "chicken, tomato, garlic, rice"       │          │
│      │        ↓                                      │          │
│      │ SentenceTransformer.encode()                 │          │
│      │        ↓                                      │          │
│      │ Output: [0.123, -0.456, 0.789, ..., 0.234]  │          │
│      │         (384 dimensions)                      │          │
│      └──────────────────────────────────────────────┘          │
│                                                                  │
│      query_vec = model.encode([" ".join(ingredients)])          │
│      faiss.normalize_L2(query_vec)  # Cosine similarity         │
│                                                                  │
│      # PHASE B: FAISS Vector Search                             │
│      ┌──────────────────────────────────────────────┐          │
│      │ FAISS Index Search                            │          │
│      │ (50,000 recipe vectors)                       │          │
│      │                                               │          │
│      │ Query: User's 384-dim vector                 │          │
│      │ Algorithm: Inner Product (cosine similarity) │          │
│      │ Retrieve: Top 50 candidates                  │          │
│      │ Time: ~5-10 milliseconds                     │          │
│      └──────────────────────────────────────────────┘          │
│                                                                  │
│      distances, indices = index.search(query_vec, k=50)         │
│                                                                  │
│      # PHASE C: Re-ranking by Ingredient Overlap                │
│      ┌──────────────────────────────────────────────┐          │
│      │ For each of 50 candidate recipes:            │          │
│      │                                               │          │
│      │ 1. Parse recipe ingredients list              │          │
│      │ 2. Calculate overlap with user ingredients    │          │
│      │    overlap_set = user_set ∩ recipe_set       │          │
│      │                                               │          │
│      │ 3. Filter: Skip if overlap < 2 ingredients    │          │
│      │                                               │          │
│      │ 4. Compute scores:                            │          │
│      │    • semantic_score = FAISS distance          │          │
│      │    • overlap_score = |overlap| / |user_set|  │          │
│      │                                               │          │
│      │ 5. Combine scores:                            │          │
│      │    combined = (1-w)*semantic + w*overlap      │          │
│      │    where w = rerank_weight (default: 0.6)    │          │
│      └──────────────────────────────────────────────┘          │
│                                                                  │
│      input_set = set(ingredients)                                │
│      results = []                                                │
│                                                                  │
│      for dist, idx in zip(distances[0], indices[0]):            │
│          recipe = metadata_df.iloc[idx]                          │
│          recipe_ings = parse_ingredients(recipe["NER"])          │
│          overlap_set = input_set & set(recipe_ings)             │
│                                                                  │
│          if len(overlap_set) < 2:                               │
│              continue  # Skip recipes with minimal overlap       │
│                                                                  │
│          semantic_score = dist                                   │
│          overlap_score = len(overlap_set) / len(input_set)      │
│          combined_score = (1-rerank_weight)*semantic_score +    │
│                           rerank_weight*overlap_score            │
│                                                                  │
│          results.append({                                        │
│              "title": recipe["title"],                           │
│              "ingredients": list(overlap_set),                   │
│              "semantic_score": semantic_score,                   │
│              "overlap_score": overlap_score,                     │
│              "combined_score": combined_score                    │
│          })                                                      │
│                                                                  │
│      # PHASE D: Sort and Return Top N                           │
│      results.sort(key=lambda x: x["combined_score"], reverse=True) │
│      return results[:top_n]                                      │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Returns JSON results
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ STEP 5: API RESPONSE                                            │
│ JSON Response to Mobile App                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HTTP 200 OK                                                     │
│                                                                  │
│  Response Body:                                                  │
│  [                                                               │
│    {                                                             │
│      "title": "Garlic Chicken with Tomato Rice",               │
│      "ingredients": ["chicken", "tomato", "garlic", "rice"],    │
│      "semantic_score": 0.89,                                    │
│      "overlap_score": 1.0,                                      │
│      "combined_score": 0.956,                                   │
│      "rank": 1                                                  │
│    },                                                            │
│    {                                                             │
│      "title": "Spanish Chicken and Rice",                       │
│      "ingredients": ["chicken", "rice", "tomato"],              │
│      "semantic_score": 0.85,                                    │
│      "overlap_score": 0.75,                                     │
│      "combined_score": 0.79,                                    │
│      "rank": 2                                                  │
│    },                                                            │
│    {                                                             │
│      "title": "Tomato Garlic Chicken Breast",                  │
│      "ingredients": ["chicken", "tomato", "garlic"],            │
│      "semantic_score": 0.82,                                    │
│      "overlap_score": 0.75,                                     │
│      "combined_score": 0.778,                                   │
│      "rank": 3                                                  │
│    },                                                            │
│    ...                                                           │
│  ]                                                               │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Renders UI
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ STEP 6: USER INTERFACE DISPLAY                                  │
│ Mobile App Renders Results                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────┐         │
│  │ 🍽️ Recommended Recipes                            │         │
│  │                                                    │         │
│  │  1. ⭐ Garlic Chicken with Tomato Rice           │         │
│  │     Match: 95.6% | All ingredients available     │         │
│  │     [View Recipe]                                 │         │
│  │                                                    │         │
│  │  2. 🌟 Spanish Chicken and Rice                  │         │
│  │     Match: 79.0% | 3/4 ingredients available     │         │
│  │     [View Recipe]                                 │         │
│  │                                                    │         │
│  │  3. 🌟 Tomato Garlic Chicken Breast              │         │
│  │     Match: 77.8% | 3/4 ingredients available     │         │
│  │     [View Recipe]                                 │         │
│  │                                                    │         │
│  │  ...                                              │         │
│  └───────────────────────────────────────────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Detailed Algorithmic Flow

#### **Step 4A: Text Embedding**

```python
# Input ingredients
ingredients = ["chicken", "tomato", "garlic", "rice"]

# Concatenate into single text string
query_text = " ".join(ingredients)
# → "chicken tomato garlic rice"

# Encode using SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
query_vector = model.encode([query_text])
# → numpy array of shape (1, 384)
# → [[0.123, -0.456, 0.789, ..., 0.234]]

# Normalize for cosine similarity
faiss.normalize_L2(query_vector)
# → L2 norm = 1.0, enables inner product = cosine similarity
```

#### **Step 4B: FAISS Search**

```python
# FAISS index contains 50,000 pre-computed recipe embeddings
# Each recipe was encoded as: title + ingredients + directions

# Search for top 50 most similar recipes
k = 50
distances, indices = index.search(query_vector, k)

# distances: numpy array of shape (1, 50)
#   → Cosine similarity scores in range [-1, 1]
#   → Higher values = more similar

# indices: numpy array of shape (1, 50)
#   → Row indices into recipe metadata dataframe
#   → Maps to specific recipes

# Example output:
# distances[0] = [0.89, 0.85, 0.82, 0.78, ...]
# indices[0]   = [1247, 8931, 3456, 9012, ...]
```

#### **Step 4C: Overlap Re-ranking**

```python
# Convert user ingredients to set for fast lookup
input_set = {"chicken", "tomato", "garlic", "rice"}

results = []
for dist, idx in zip(distances[0], indices[0]):
    # Load recipe from metadata
    recipe = metadata_df.iloc[idx]
    recipe_ingredients = ["chicken", "tomato", "garlic", "rice", "onion", "pepper"]
    
    # Calculate overlap
    recipe_set = set(recipe_ingredients)
    overlap_set = input_set & recipe_set
    # overlap_set = {"chicken", "tomato", "garlic", "rice"}
    
    # Filter low-overlap recipes
    if len(overlap_set) < 2:
        continue  # Skip this recipe
    
    # Calculate scores
    semantic_score = dist  # From FAISS (e.g., 0.89)
    overlap_score = len(overlap_set) / len(input_set)
    # overlap_score = 4/4 = 1.0
    
    # Weighted combination
    rerank_weight = 0.6
    combined_score = (1 - rerank_weight) * semantic_score + \
                     rerank_weight * overlap_score
    # combined_score = 0.4 * 0.89 + 0.6 * 1.0 = 0.956
    
    results.append({
        "title": recipe["title"],
        "ingredients": list(overlap_set),
        "semantic_score": semantic_score,
        "overlap_score": overlap_score,
        "combined_score": combined_score
    })

# Sort by combined score
results.sort(key=lambda x: x["combined_score"], reverse=True)

# Return top N
return results[:5]
```

---

## 4. Technology Stack

### 4.1 Machine Learning Models

| Component | Version/Model | Parameters | Purpose |
|-----------|--------------|------------|---------|
| **SentenceTransformer** | `all-MiniLM-L6-v2` | 22M | Semantic text encoding |
| **Word2Vec** | Gensim (CBOW) | 100-dim embeddings | Ingredient similarity |
| **FAISS** | IndexFlatIP | N/A | Fast vector search |
| **spaCy** | `en_core_web_sm` | CNN pipeline | Ingredient normalization |

### 4.2 Backend Technologies

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API framework |
| **Neo4j** | Graph database (relationships) |
| **Docker Compose** | Service orchestration |
| **Uvicorn** | ASGI server |
| **Pydantic** | Request/response validation |

### 4.3 Data Storage

| Storage Type | Technology | Data |
|--------------|------------|------|
| **Vector Index** | FAISS `.faiss` file | 50K-2.2M recipe embeddings |
| **Metadata** | CSV (`recipe_metadata.csv`) | Recipe titles, ingredients, directions |
| **Graph** | Neo4j | 100K recipes, ingredients, relationships |
| **ML Models** | Gensim `.model` files | Word2Vec ingredient embeddings |

---

## 5. Code Implementation

### 5.1 FastAPI Endpoint

**File:** `src/api/app.py`

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
import asyncio

from src.utils.recipesuggestionmodel import suggest_recipes

app = FastAPI(title="Plate Planner Backend")

# Request schema
class RecipeRequest(BaseModel):
    ingredients: List[str] = Field(
        ...,
        description="List of ingredients",
        example=["chicken", "tomato", "garlic"]
    )
    top_n: int = Field(5, description="Number of recipes to return")
    rerank_weight: float = Field(0.6, description="Overlap weight (0-1)")

# Response schema
class RecipeResult(BaseModel):
    title: str
    ingredients: List[str]
    semantic_score: float
    overlap_score: float
    combined_score: float
    rank: int

# Endpoint
@app.post("/suggest_recipes", response_model=List[RecipeResult])
async def suggest_recipes_endpoint(request: RecipeRequest):
    """
    Generate recipe recommendations based on user ingredients.
    
    Uses FAISS for semantic search + overlap re-ranking.
    """
    try:
        # Run CPU-intensive task in thread pool
        results = await asyncio.to_thread(
            suggest_recipes,
            request.ingredients,
            request.top_n,
            request.rerank_weight,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recipe generation failed: {str(e)}"
        )
    
    return results
```

### 5.2 Recipe Suggestion Engine

**File:** `src/utils/recipesuggestionmodel.py`

```python
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from src.config.paths import DataPaths
from ast import literal_eval

# Configuration
MODEL_NAME = "all-MiniLM-L6-v2"
paths = DataPaths()

# Load model and data at module import (once)
print("🔄 Loading SentenceTransformer model...")
model = SentenceTransformer(MODEL_NAME)

print("📥 Loading recipe metadata...")
metadata_df = pd.read_csv(paths.recipe_metadata)

print("🧮 Loading recipe embeddings...")
recipe_embeddings = np.load(paths.recipe_embeddings).astype("float32")
faiss.normalize_L2(recipe_embeddings)

print("🔍 Loading FAISS index...")
index = faiss.read_index(str(paths.recipe_faiss_index))

print(f"✅ Loaded: {len(metadata_df)} recipes, {index.ntotal} vectors")

def suggest_recipes(
    ingredients: list[str],
    top_n: int = 5,
    rerank_weight: float = 0.6,
    raw_k: int = 50,
    min_overlap: int = 2
) -> list[dict]:
    """
    Suggest recipes based on semantic similarity + ingredient overlap.
    
    Args:
        ingredients: User's available ingredients
        top_n: Number of recipes to return
        rerank_weight: Balance between overlap (1.0) and semantic (0.0)
        raw_k: Number of candidates to retrieve from FAISS
        min_overlap: Minimum ingredient overlap required
    
    Returns:
        List of recipe dictionaries with scores
    """
    # STEP 1: Encode user ingredients
    query_text = " ".join(ingredients)
    query_vec = model.encode([query_text])
    faiss.normalize_L2(query_vec)
    
    # STEP 2: FAISS search
    distances, indices = index.search(query_vec, raw_k)
    
    # STEP 3: Re-rank by ingredient overlap
    input_set = set(ingredients)
    results = []
    
    for dist_i, idx in enumerate(indices[0]):
        # Load recipe metadata
        row = metadata_df.iloc[idx]
        
        # Parse ingredient list (stored as string)
        try:
            recipe_ings = literal_eval(row["NER"])
        except (ValueError, SyntaxError):
            continue
        
        # Deduplicate ingredients
        seen = set()
        unique_ings = []
        for ing in recipe_ings:
            if ing not in seen:
                unique_ings.append(ing)
                seen.add(ing)
        
        # Calculate overlap
        overlap_set = input_set & set(unique_ings)
        if len(overlap_set) < min_overlap:
            continue  # Skip low-overlap recipes
        
        # Compute scores
        semantic_score = float(distances[0][dist_i])
        semantic_score = max(0.0, min(1.0, semantic_score))
        
        overlap_score = len(overlap_set) / max(len(ingredients), 1)
        
        combined_score = ((1 - rerank_weight) * semantic_score +
                         rerank_weight * overlap_score)
        combined_score = max(0.0, min(1.0, combined_score))
        
        results.append({
            "title": row["title"],
            "ingredients": [i for i in unique_ings if i in overlap_set],
            "semantic_score": semantic_score,
            "overlap_score": overlap_score,
            "combined_score": combined_score,
        })
    
    # STEP 4: Sort and rank
    results = sorted(results, key=lambda x: x["combined_score"], reverse=True)
    for rank, r in enumerate(results[:top_n], start=1):
        r["rank"] = rank
    
    return results[:top_n]
```

### 5.3 Configuration Management

**File:** `src/config/paths.py`

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class DataPaths:
    """Centralized path management for all data files."""
    
    project_root: Path = Path(__file__).resolve().parents[2]
    data_root: Path = project_root / "src" / "data"
    
    # Subdirectories
    models: Path = data_root / "models"
    processed: Path = data_root / "processed"
    raw: Path = data_root / "raw"
    
    # Recipe suggestion files
    recipe_metadata: Path = processed / "recipe_suggestion" / "recipe_metadata.csv"
    recipe_embeddings: Path = processed / "recipe_suggestion" / "recipe_embeddings.npy"
    recipe_faiss_index: Path = models / "recipe_suggestion" / "recipe_index.faiss"
    
    # Ingredient substitution files
    ingredient_w2v: Path = models / "ingredient_substitution" / "ingredient_w2v.model"
    substitution_edges: Path = processed / "ingredient_substitution" / "substitution_edges_with_context_cleaned.csv"
    
    # Raw datasets
    recipe_nlg: Path = raw / "RecipeNLG_dataset.csv"
    
    # Neo4j graph data
    ingredients: Path = processed / "ingredients.csv"
    recipes: Path = processed / "recipes.csv"
    recipe_ingredients: Path = processed / "recipe_ingredients.csv"
```

---

## 6. Neo4j vs FAISS: Role Clarification

### 6.1 Common Misconception

❌ **INCORRECT:** Neo4j's `HAS_INGREDIENT` relationships are used to generate recipe recommendations when user uploads pantry list.

✅ **CORRECT:** FAISS vector search is used for recipe generation. Neo4j is used for substitutions and recipe details.

### 6.2 Role Comparison

| Operation | Technology Used | Query Type | Response Time |
|-----------|-----------------|------------|---------------|
| **"Find recipes from ingredients"** | FAISS + SentenceTransformer | Vector similarity search | 5-10ms |
| **"Substitute butter with what?"** | Neo4j + Word2Vec | Graph traversal (`SUBSTITUTES_WITH`) | 10-50ms |
| **"Show full recipe details"** | Neo4j | Graph traversal (`HAS_INGREDIENT`) | 5-20ms |
| **"What's similar to tomato?"** | Neo4j | Graph traversal (`SIMILAR_TO`) | 5-20ms |

### 6.3 Why This Hybrid Architecture?

#### **FAISS: Speed at Scale**

**Advantages:**
- ✅ Search 2.2M recipes in < 10ms
- ✅ Semantic understanding (finds "creamy pasta" even without exact words)
- ✅ Scales to billions of vectors
- ✅ GPU-accelerated (optional)

**Limitations:**
- ❌ Cannot handle complex relationships
- ❌ No context-aware logic
- ❌ Only finds similar vectors, not relationships

#### **Neo4j: Relationship Intelligence**

**Advantages:**
- ✅ Complex multi-hop graph queries
- ✅ Context-aware substitutions (butter in baking vs. cooking)
- ✅ Ingredient co-occurrence patterns
- ✅ Explainable recommendations

**Limitations:**
- ❌ Slow for searching millions of nodes
- ❌ Not optimized for semantic similarity
- ❌ Typically limited to ~100K nodes for responsive queries

### 6.4 When Each Technology is Used

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                          │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ "Find        │  │ "Substitute  │  │ "Show me     │
│  recipes     │  │  butter"     │  │  full        │
│  from        │  │              │  │  recipe"     │
│  ingredients"│  │              │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │                 │                 │
   ┌───▼───┐         ┌───▼───┐         ┌───▼───┐
   │ FAISS │         │ Neo4j │         │ Neo4j │
   │Search │         │ Graph │         │ Graph │
   └───────┘         └───────┘         └───────┘
       │                 │                 │
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Semantic     │  │ SUBSTITUTES_ │  │ HAS_         │
│ similarity   │  │ WITH edges   │  │ INGREDIENT   │
│ + overlap    │  │              │  │ edges        │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 6.5 Neo4j Graph Structure (For Reference)

While Neo4j is **NOT** used for primary recipe search, it stores valuable relationship data:

```cypher
// Example: Recipe with ingredients (stored in Neo4j)
(r:Recipe {
    recipe_id: 1247,
    title: "Garlic Chicken with Tomato Rice"
})-[:HAS_INGREDIENT]->(i1:Ingredient {name: "chicken"})
                     -[:HAS_INGREDIENT]->(i2:Ingredient {name: "tomato"})
                     -[:HAS_INGREDIENT]->(i3:Ingredient {name: "garlic"})
                     -[:HAS_INGREDIENT]->(i4:Ingredient {name: "rice"})

// Ingredient substitution relationships
(butter:Ingredient {name: "butter"})
    -[:SUBSTITUTES_WITH {score: 0.92, context: "baking"}]->
        (margarine:Ingredient {name: "margarine"})

// Ingredient similarity (from Word2Vec)
(tomato:Ingredient {name: "tomato"})
    -[:SIMILAR_TO {score: 0.78}]->
        (pepper:Ingredient {name: "red bell pepper"})
```

#### **Example Neo4j Queries (NOT Used for Recipe Search)**

**Query 1: Get Recipe Details**
```cypher
MATCH (r:Recipe {title: "Garlic Chicken with Tomato Rice"})
      -[:HAS_INGREDIENT]->(i:Ingredient)
RETURN r.title, collect(i.name) AS ingredients
```

**Query 2: Find Substitutes**
```cypher
MATCH (i:Ingredient {name: "butter"})
      -[s:SUBSTITUTES_WITH]->(sub:Ingredient)
WHERE s.context = "baking"
RETURN sub.name, s.score
ORDER BY s.score DESC
LIMIT 5
```

**Query 3: Ingredient Co-occurrence**
```cypher
MATCH (i1:Ingredient {name: "chicken"})
      <-[:HAS_INGREDIENT]-(r:Recipe)
      -[:HAS_INGREDIENT]->(i2:Ingredient)
WHERE i1 <> i2
RETURN i2.name, count(*) AS frequency
ORDER BY frequency DESC
LIMIT 10
```

---

## 7. API Endpoints

### 7.1 Recipe Suggestion

#### **Endpoint**
```
POST /suggest_recipes
```

#### **Request Schema**
```json
{
  "ingredients": ["chicken", "tomato", "garlic", "rice"],
  "top_n": 5,
  "rerank_weight": 0.6
}
```

#### **Response Schema**
```json
[
  {
    "title": "Garlic Chicken with Tomato Rice",
    "ingredients": ["chicken", "tomato", "garlic", "rice"],
    "semantic_score": 0.89,
    "overlap_score": 1.0,
    "combined_score": 0.956,
    "rank": 1
  },
  ...
]
```

#### **Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ingredients` | list[str] | Required | User's available ingredients |
| `top_n` | int | 5 | Number of recipes to return |
| `rerank_weight` | float | 0.6 | Balance: 1.0 = all overlap, 0.0 = all semantic |

### 7.2 Ingredient Substitution

#### **Endpoint**
```
GET /substitute?ingredient=butter&context=baking&hybrid=true&top_k=5
```

#### **Response Schema**
```json
{
  "ingredient": "butter",
  "context": "baking",
  "hybrid": true,
  "substitutes": [
    {
      "name": "margarine",
      "score": 0.92,
      "context": "baking",
      "source": "direct"
    },
    ...
  ]
}
```

### 7.3 Recipe Details

#### **Endpoint**
```
GET /recipes/{recipe_title}
```

#### **Response Schema**
```json
{
  "title": "Garlic Chicken with Tomato Rice",
  "directions": [
    "Heat oil in a large pan over medium heat",
    "Add chicken and cook until browned",
    ...
  ],
  "link": "https://example.com/recipe",
  "source": "RecipeNLG",
  "ingredients": ["chicken", "tomato", "garlic", "rice", "oil", "salt"]
}
```

---

## 8. Example Requests and Responses

### 8.1 Scenario: User Has 4 Ingredients

#### **Request**
```bash
curl -X POST "http://localhost:8000/suggest_recipes" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": ["chicken", "tomato", "garlic", "rice"],
    "top_n": 3,
    "rerank_weight": 0.6
  }'
```

#### **Response**
```json
[
  {
    "title": "Garlic Chicken with Tomato Rice",
    "ingredients": ["chicken", "tomato", "garlic", "rice"],
    "semantic_score": 0.89,
    "overlap_score": 1.0,
    "combined_score": 0.956,
    "rank": 1
  },
  {
    "title": "Spanish Chicken and Rice",
    "ingredients": ["chicken", "rice", "tomato"],
    "semantic_score": 0.85,
    "overlap_score": 0.75,
    "combined_score": 0.79,
    "rank": 2
  },
  {
    "title": "Tomato Garlic Chicken Breast",
    "ingredients": ["chicken", "tomato", "garlic"],
    "semantic_score": 0.82,
    "overlap_score": 0.75,
    "combined_score": 0.778,
    "rank": 3
  }
]
```

### 8.2 Scenario: User Needs Substitution

#### **Request**
```bash
curl "http://localhost:8000/substitute?ingredient=butter&context=baking&hybrid=true&top_k=5"
```

#### **Response**
```json
{
  "ingredient": "butter",
  "context": "baking",
  "hybrid": true,
  "substitutes": [
    {
      "name": "margarine",
      "score": 0.92,
      "context": "baking",
      "source": "direct"
    },
    {
      "name": "coconut oil",
      "score": 0.85,
      "context": "baking",
      "source": "direct"
    },
    {
      "name": "applesauce",
      "score": 0.78,
      "context": "baking",
      "source": "cooccurrence"
    },
    {
      "name": "greek yogurt",
      "score": 0.72,
      "context": "baking",
      "source": "cooccurrence"
    },
    {
      "name": "vegetable oil",
      "score": 0.68,
      "context": null,
      "source": "hybrid"
    }
  ]
}
```

### 8.3 Scenario: User Wants Recipe Details

#### **Request**
```bash
curl "http://localhost:8000/recipes/Garlic%20Chicken%20with%20Tomato%20Rice"
```

#### **Response**
```json
{
  "title": "Garlic Chicken with Tomato Rice",
  "directions": [
    "Heat 2 tbsp oil in a large skillet over medium-high heat",
    "Season chicken with salt and pepper, then add to pan",
    "Cook chicken until golden brown, about 5 minutes per side",
    "Remove chicken and set aside",
    "Add garlic to pan and sauté for 1 minute",
    "Add rice and stir to coat with oil",
    "Add tomatoes and chicken broth",
    "Return chicken to pan, cover, and simmer for 20 minutes",
    "Fluff rice with fork and serve"
  ],
  "link": "https://www.recipenlg.com/recipe/12345",
  "source": "RecipeNLG",
  "ingredients": [
    "chicken breast",
    "tomato",
    "garlic",
    "rice",
    "olive oil",
    "salt",
    "pepper",
    "chicken broth"
  ]
}
```

---

## 9. Performance Characteristics

### 9.1 Latency Breakdown

| Phase | Operation | Time | Technology |
|-------|-----------|------|------------|
| **1. Text Encoding** | SentenceTransformer.encode() | 5-15ms | CPU |
| **2. FAISS Search** | index.search() for top 50 | 5-10ms | CPU |
| **3. Overlap Re-ranking** | Set intersection + scoring | 2-5ms | Python |
| **4. Sorting & Filtering** | Sort by combined_score | < 1ms | Python |
| **Total (API)** | End-to-end request → response | **15-35ms** | FastAPI |

### 9.2 Throughput

| Metric | Value | Notes |
|--------|-------|-------|
| **Concurrent Requests** | 50-100 req/s | Single FastAPI instance |
| **FAISS Index Size** | 50K recipes: ~75 MB<br>2.2M recipes: ~3.3 GB | Float32 embeddings |
| **Memory Usage** | ~500 MB (50K)<br>~4 GB (2.2M) | Model + index + metadata |
| **Startup Time** | ~5-10 seconds | Load model + FAISS index |

### 9.3 Scalability

#### **Current Scale (50K Recipes)**
- ✅ FAISS search: < 10ms
- ✅ Memory: ~500 MB
- ✅ Single server handles 100+ req/s

#### **Target Scale (2.2M Recipes)**
- ⚠️ FAISS search: 10-20ms (still acceptable)
- ⚠️ Memory: ~4 GB (requires larger instance)
- ✅ Can serve 50+ req/s per instance
- 💡 **Recommendation:** Use `IndexIVFFlat` (clustered index) for > 1M vectors

#### **Future Scale (10M+ Recipes)**
- 💡 Use FAISS GPU index (`IndexFlatIP` on CUDA)
- 💡 Distributed FAISS with index sharding
- 💡 Redis caching for frequent queries

---

## 10. Design Rationale

### 10.1 Why FAISS for Recipe Search?

#### **Problem:**
User has 4 ingredients → Need to search 2.2M recipes in real-time (< 50ms)

#### **Alternatives Considered:**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Neo4j Graph Traversal** | Relationship-aware | Too slow for millions of nodes | ❌ Rejected |
| **Elasticsearch** | Full-text search | No semantic understanding | ❌ Rejected |
| **SQL with Full-Text** | Simple to implement | No semantic, no scale | ❌ Rejected |
| **FAISS Vector Search** | Ultra-fast, semantic | Requires embeddings | ✅ **Selected** |

#### **Key Advantages of FAISS:**
1. **Speed:** 5-10ms for 50K-2.2M recipes
2. **Semantic:** Understands meaning, not just keywords
3. **Scalability:** Proven at billion-scale (Facebook)
4. **Flexibility:** Multiple index types (flat, IVF, HNSW)

### 10.2 Why Hybrid Scoring?

#### **Problem:**
Pure semantic search returns recipes that are "similar" but may not match user's actual ingredients.

#### **Solution:**
Combine semantic similarity with ingredient overlap:

```
combined_score = (1 - w) * semantic_score + w * overlap_score
```

Where `w = 0.6` (60% overlap, 40% semantic)

#### **Example:**

| Recipe | Semantic | Overlap | Combined (w=0.6) | Rank |
|--------|----------|---------|------------------|------|
| A | 0.95 | 0.50 | 0.68 | 2 |
| B | 0.80 | 1.00 | 0.92 | **1** ← Winner |

**Recipe B wins** because user has ALL ingredients (overlap=1.0), even though semantic score is lower.

### 10.3 Why Neo4j for Substitutions?

#### **Problem:**
"Butter" can be substituted with "margarine" in baking, but "olive oil" in cooking.

#### **Why Graph Database:**
- ✅ Context-aware relationships
- ✅ Multi-hop traversal (e.g., if A→B and B→C, then A→C)
- ✅ Explainable paths
- ✅ Co-occurrence patterns

#### **Example Neo4j Query:**
```cypher
// Context-aware substitution
MATCH (butter:Ingredient {name: 'butter'})
      -[s:SUBSTITUTES_WITH]->(sub)
WHERE s.context = 'baking'
RETURN sub.name, s.score
ORDER BY s.score DESC
```

### 10.4 Why SentenceTransformers?

#### **Alternatives:**

| Model | Pros | Cons | Decision |
|-------|------|------|----------|
| **TF-IDF** | Fast, simple | No semantic understanding | ❌ |
| **Word2Vec** | Semantic | Word-level, not sentence-level | ❌ |
| **BERT (base)** | High quality | Slow inference (110M params) | ❌ |
| **all-MiniLM-L6-v2** | Fast, good quality | Slightly lower accuracy | ✅ |

#### **all-MiniLM-L6-v2 Stats:**
- **Size:** 22M parameters (5x smaller than BERT)
- **Speed:** 5-15ms per encoding
- **Quality:** 95% of BERT performance
- **Training:** Distilled from larger models

---

## Appendix A: File Structure

```
plate-planner-api/
├── src/
│   ├── api/
│   │   └── app.py                    # FastAPI endpoints
│   ├── config/
│   │   ├── config.py                 # Environment variables
│   │   └── paths.py                  # Path management
│   ├── data/
│   │   ├── models/
│   │   │   ├── recipe_suggestion/
│   │   │   │   └── recipe_index.faiss       # FAISS index
│   │   │   └── ingredient_substitution/
│   │   │       └── ingredient_w2v.model     # Word2Vec
│   │   ├── processed/
│   │   │   ├── recipe_suggestion/
│   │   │   │   ├── recipe_metadata.csv      # Recipe data
│   │   │   │   └── recipe_embeddings.npy    # 384-dim vectors
│   │   │   ├── ingredients.csv              # For Neo4j
│   │   │   ├── recipes.csv                  # For Neo4j
│   │   │   └── recipe_ingredients.csv       # For Neo4j
│   │   └── raw/
│   │       └── RecipeNLG_dataset.csv        # Source data
│   ├── services/
│   │   └── neo4j_service.py          # Neo4j graph queries
│   ├── utils/
│   │   └── recipesuggestionmodel.py  # FAISS search logic
│   └── database/
│       ├── bootstrap_graph.py        # Neo4j setup
│       └── load_into_neo4j.py        # Data loading
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **FAISS** | Facebook AI Similarity Search - library for efficient vector search |
| **Embedding** | Dense vector representation of text (e.g., 384-dim) |
| **Semantic Similarity** | Meaning-based similarity (not just keyword matching) |
| **Cosine Similarity** | Measure of angle between two vectors (range: -1 to 1) |
| **Inner Product** | Dot product of vectors (FAISS uses this for cosine similarity) |
| **Re-ranking** | Adjusting search results based on additional criteria |
| **Overlap Score** | Fraction of user ingredients present in recipe |
| **Graph Traversal** | Following edges in Neo4j to find related nodes |
| **Context-Aware** | Using situational information (e.g., "baking" vs "cooking") |

---

## Appendix C: Future Enhancements

### C.1 Planned Improvements

1. **GPU-Accelerated FAISS**
   - Use `IndexFlatIP` on CUDA
   - 10-100x faster search
   - Enable real-time search of 10M+ recipes

2. **Multi-Modal Search**
   - CLIP model for image+text
   - User uploads photo of dish → find similar recipes
   - "Show me recipes that look like this"

3. **Personalization**
   - User preference learning
   - Collaborative filtering
   - "Users like you also enjoyed..."

4. **Natural Language Queries**
   - GPT-4 integration
   - "I want a healthy dinner with chicken"
   - Extract intent + ingredients + constraints

### C.2 Research Directions

1. **Graph Neural Networks (GNNs)**
   - Replace Word2Vec with GNN embeddings
   - Learn from graph structure
   - Multi-hop relationship modeling

2. **Reinforcement Learning**
   - Multi-armed bandit for recipe ranking
   - Learn from user feedback (clicks, saves, cooks)
   - Optimize for engagement

3. **Federated Learning**
   - Train on user data without centralization
   - Privacy-preserving personalization
   - Collaborative model improvement

---

## Contact & Contribution

**Project Repository:** [https://github.com/irangareddy/plate-planner-api](https://github.com/irangareddy/plate-planner-api)  
**Documentation:** See `README.md` and `Chapter6_7_Evaluation_and_System_Methodology.md`  
**Issues:** GitHub Issues  

**Authors:**
- Sandilya Chimalamarri (Recipe Suggestion Subsystem)
- Sai Priyanka Bonkuri (Ingredient Substitution Subsystem)
- Pavan Charith Devarapalli (Data Preprocessing & Model Training)
- Sai Dheeraj Gollu (Graph Database & API Integration)

---

**Document Version:** 1.0  
**Last Updated:** November 20, 2025  
**Status:** Production-Ready

