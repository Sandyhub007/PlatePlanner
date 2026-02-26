"""
Integrate international recipe datasets into PlatePlanner's SQLite DB + FAISS index.

This script:
1. Reads downloaded CSVs from src/data/raw/international/
2. Normalizes each dataset to a common schema
3. Adds new recipes to the existing SQLite database (with deduplication)
4. Rebuilds the FAISS index to include new entries

Usage:
    poetry run python -m src.pipelines.integrate_international_recipes
"""

import os
import sys
import json
import csv
import sqlite3
import re
from pathlib import Path
from ast import literal_eval
from typing import Optional
from collections import defaultdict

import numpy as np

# Project setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# ─── Paths ───
RAW_DIR = PROJECT_ROOT / "src" / "data" / "raw" / "international"
DB_PATH = PROJECT_ROOT / "src" / "data" / "models" / "recipe_suggestion" / "recipes.db"
INDEX_DIR = PROJECT_ROOT / "src" / "data" / "models" / "recipe_suggestion"
EMBEDDINGS_DIR = PROJECT_ROOT / "src" / "data" / "processed" / "recipe_suggestion"


# ─── Schema Migration ───
def migrate_schema(conn: sqlite3.Connection):
    """Add new columns to the recipes table if they don't exist."""
    cursor = conn.cursor()
    columns_to_add = [
        ("cuisine", "TEXT"),
        ("source", "TEXT"),
        ("dietary_tags", "TEXT"),
        ("cook_time_minutes", "INTEGER"),
        ("difficulty", "TEXT"),
        ("calories_per_serving", "INTEGER"),
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(recipes)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE recipes ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Added column: {col_name} ({col_type})")
    
    conn.commit()


def get_existing_titles(conn: sqlite3.Connection) -> set:
    """Get set of existing recipe titles for deduplication."""
    cursor = conn.cursor()
    cursor.execute("SELECT LOWER(title) FROM recipes WHERE title IS NOT NULL")
    return {row[0] for row in cursor.fetchall()}


def get_max_id(conn: sqlite3.Connection) -> int:
    """Get the current max ID in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM recipes")
    result = cursor.fetchone()[0]
    return result if result is not None else 0


# ─── Normalizers ───
def normalize_ingredients_list(raw) -> list:
    """Parse ingredients from various formats into a clean list."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if x]
    if isinstance(raw, str):
        raw = raw.strip()
        # Try JSON/Python list literal
        if raw.startswith("["):
            try:
                parsed = literal_eval(raw)
                return [str(x).strip() for x in parsed if x]
            except:
                try:
                    parsed = json.loads(raw)
                    return [str(x).strip() for x in parsed if x]
                except:
                    pass
        # Comma-separated
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def normalize_directions(raw) -> str:
    """Parse directions from various formats into a list string."""
    if not raw:
        return "[]"
    if isinstance(raw, list):
        return str(raw)
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("["):
            try:
                parsed = literal_eval(raw)
                if isinstance(parsed, list):
                    return str(parsed)
            except:
                pass
        # Split on numbered steps or newlines
        steps = re.split(r'\d+\.\s+|\n+', raw)
        steps = [s.strip() for s in steps if s.strip()]
        return str(steps) if steps else str([raw])
    return str([str(raw)])


# ─── Dataset Parsers ───

def parse_recipes_with_nutrition(filepath: Path) -> list[dict]:
    """Parse datahiveai/recipes-with-nutrition dataset."""
    print(f"  📖 Parsing: {filepath.name}")
    recipes = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        print(f"     Columns: {columns}")
        
        for row in reader:
            title = row.get("recipe_name") or row.get("name") or row.get("title", "")
            if not title or not title.strip():
                continue
            
            ingredients = normalize_ingredients_list(
                row.get("ingredients") or row.get("ingredient_list", "")
            )
            if not ingredients:
                continue
            
            directions = normalize_directions(
                row.get("directions") or row.get("instructions") or row.get("steps", "")
            )
            
            cuisine = row.get("cuisine", "")
            
            # Parse dietary tags
            dietary = {}
            for tag in ["vegan", "vegetarian", "gluten_free", "dairy_free"]:
                val = row.get(tag, "")
                if val:
                    dietary[tag] = str(val).lower() in ("true", "1", "yes")
            
            calories = None
            cal_raw = row.get("calories") or row.get("calories_per_serving", "")
            if cal_raw:
                try:
                    calories = int(float(cal_raw))
                except:
                    pass
            
            cook_time = None
            ct_raw = row.get("cook_time") or row.get("cooking_time_minutes", "")
            if ct_raw:
                try:
                    cook_time = int(float(ct_raw))
                except:
                    pass
            
            recipes.append({
                "title": title.strip(),
                "ingredients": str(ingredients),
                "directions": directions,
                "ner": str(ingredients),
                "cuisine": cuisine.strip() if cuisine else None,
                "source": "recipes_with_nutrition",
                "dietary_tags": json.dumps(dietary) if dietary else None,
                "cook_time_minutes": cook_time,
                "difficulty": row.get("difficulty"),
                "calories_per_serving": calories,
            })
    
    print(f"     ✅ Parsed {len(recipes)} recipes")
    return recipes


def _parse_iso_duration_minutes(iso: str) -> Optional[int]:
    """Parse ISO 8601 duration (e.g. PT1H30M) to minutes."""
    if not iso or not isinstance(iso, str):
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes
    return None


def _parse_r_vector(raw: str) -> list:
    """Parse R-style c(...) vectors from Food.com CSV."""
    if not raw or not isinstance(raw, str):
        return []
    raw = raw.strip()
    # Handle R-style c("a", "b") format
    if raw.startswith('c(') and raw.endswith(')'):
        inner = raw[2:-1]
        # Split by ", " pattern (quoted items)
        items = re.findall(r'""([^""]*?)""', inner)
        if items:
            return [x.strip() for x in items if x.strip()]
        # Fallback: try splitting by comma
        return [x.strip().strip('"').strip("'") for x in inner.split(',') if x.strip()]
    # Try list literal
    if raw.startswith('['):
        try:
            return literal_eval(raw)
        except:
            try:
                return json.loads(raw)
            except:
                pass
    return [x.strip() for x in raw.split(',') if x.strip()]


def parse_food_com(filepath: Path) -> list[dict]:
    """Parse AkashPS11/recipes_data_food.com dataset.
    
    Columns: RecipeId, Name, RecipeIngredientParts, RecipeInstructions,
             Keywords, Calories, CookTime (ISO 8601), etc.
    """
    print(f"  📖 Parsing: {filepath.name}")
    recipes = []
    
    cuisine_keywords = {
        "italian", "mexican", "chinese", "japanese", "thai", "indian",
        "french", "greek", "korean", "vietnamese", "mediterranean",
        "african", "caribbean", "middle-eastern", "spanish", "german",
        "british", "irish", "brazilian", "peruvian", "turkish",
        "ethiopian", "moroccan", "indonesian", "filipino", "malaysian",
        "american", "southern", "cajun", "tex-mex", "hawaiian",
        "scandinavian", "polish", "russian", "hungarian", "lebanese",
        "persian", "pakistani", "bangladeshi", "sri-lankan", "nepalese",
        "swiss", "austrian", "portuguese", "cuban", "jamaican",
        "argentinian", "colombian", "venezuelan", "chilean", "asian",
        "european", "latin-american", "south-american", "north-african",
        "west-african", "east-african", "southeast-asian", "south-asian",
        "central-american", "australian", "new-zealand"
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        print(f"     Columns: {columns}")
        
        for row in reader:
            title = row.get("Name") or row.get("name", "")
            if not title or not title.strip():
                continue
            
            # Parse R-style c(...) ingredient parts
            ing_raw = row.get("RecipeIngredientParts", "")
            ingredients = _parse_r_vector(ing_raw)
            if not ingredients:
                ingredients = normalize_ingredients_list(ing_raw)
            if not ingredients:
                continue
            
            # Parse R-style c(...) instructions
            inst_raw = row.get("RecipeInstructions", "")
            steps = _parse_r_vector(inst_raw)
            directions = str(steps) if steps else normalize_directions(inst_raw)
            
            # Extract cuisine from Keywords (R-style c(...))
            kw_raw = row.get("Keywords", "")
            cuisine = None
            if kw_raw:
                keywords = _parse_r_vector(kw_raw)
                kw_lower = [k.lower().strip() for k in keywords]
                cuisine_tags = [k for k in kw_lower if k in cuisine_keywords]
                if cuisine_tags:
                    cuisine = ",".join(cuisine_tags)
            
            # Calories (direct column)
            calories = None
            cal_raw = row.get("Calories", "")
            if cal_raw:
                try:
                    calories = int(float(cal_raw))
                except:
                    pass
            
            # Cook time (ISO 8601 duration)
            cook_time = _parse_iso_duration_minutes(row.get("CookTime", ""))
            
            ner = [ing.lower().strip() for ing in ingredients]
            
            recipes.append({
                "title": title.strip(),
                "ingredients": str(ingredients),
                "directions": directions,
                "ner": str(ner),
                "cuisine": cuisine,
                "source": "food_com",
                "dietary_tags": None,
                "cook_time_minutes": cook_time,
                "difficulty": None,
                "calories_per_serving": calories,
            })
    
    print(f"     ✅ Parsed {len(recipes)} recipes")
    return recipes


def parse_cooking_recipes_large(filepath: Path) -> list[dict]:
    """Parse CodeKapital/CookingRecipes dataset.
    
    Same format as RecipeNLG: title, ingredients, directions, link, source, NER
    """
    print(f"  📖 Parsing: {filepath.name}")
    recipes = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        print(f"     Columns: {columns}")
        
        for row in reader:
            title = (row.get("title") or row.get("Title") or
                     row.get("name") or row.get("Name", ""))
            if not title or not title.strip():
                continue
            
            # Use NER column (clean ingredient names) if available
            ner_raw = row.get("NER", "")
            ner_list = normalize_ingredients_list(ner_raw)
            
            # Full ingredients
            ingredients_raw = row.get("ingredients", "")
            ingredients = normalize_ingredients_list(ingredients_raw)
            
            if not ner_list and not ingredients:
                continue
            
            directions = normalize_directions(
                row.get("directions") or row.get("instructions", "")
            )
            
            # This dataset has 'source' column (Gathered, Recipes1M)
            data_source = row.get("source", "")
            
            recipes.append({
                "title": title.strip(),
                "ingredients": ingredients_raw if ingredients_raw else str(ner_list),
                "directions": directions,
                "ner": ner_raw if ner_raw else str([x.lower() for x in ingredients]),
                "cuisine": None,  # No cuisine labels in this dataset
                "source": f"cooking_recipes_{data_source.lower()}" if data_source else "cooking_recipes_large",
                "dietary_tags": None,
                "cook_time_minutes": None,
                "difficulty": None,
                "calories_per_serving": None,
            })
    
    print(f"     ✅ Parsed {len(recipes)} recipes")
    return recipes


# ─── Main Integration ───

def insert_recipes(conn: sqlite3.Connection, recipes: list[dict], existing_titles: set, start_id: int) -> int:
    """Insert new recipes into the database, skipping duplicates."""
    cursor = conn.cursor()
    inserted = 0
    current_id = start_id
    
    for recipe in recipes:
        title_lower = recipe["title"].lower().strip()
        if title_lower in existing_titles:
            continue
        
        current_id += 1
        cursor.execute(
            """INSERT INTO recipes 
               (id, title, ingredients, directions, ner, cuisine, source, 
                dietary_tags, cook_time_minutes, difficulty, calories_per_serving)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                current_id,
                recipe["title"],
                recipe["ingredients"],
                recipe["directions"],
                recipe["ner"],
                recipe["cuisine"],
                recipe["source"],
                recipe["dietary_tags"],
                recipe["cook_time_minutes"],
                recipe["difficulty"],
                recipe["calories_per_serving"],
            )
        )
        existing_titles.add(title_lower)
        inserted += 1
    
    conn.commit()
    return inserted


def rebuild_faiss_index(conn: sqlite3.Connection):
    """Rebuild the FAISS index with all recipes in the database."""
    import faiss
    from sentence_transformers import SentenceTransformer
    
    print("\n" + "="*60)
    print("🔄 Rebuilding FAISS index...")
    print("="*60)
    
    # Load model
    FINETUNED_MODEL = str(PROJECT_ROOT / "src" / "data" / "models" / "recipe_suggestion" / "finetuned-recipe-encoder")
    if os.path.isdir(FINETUNED_MODEL):
        model_name = FINETUNED_MODEL
        print(f"  🎯 Using fine-tuned model")
    else:
        model_name = "all-MiniLM-L6-v2"
        print(f"  📦 Using base model: {model_name}")
    
    model = SentenceTransformer(model_name)
    
    # Fetch all recipes
    cursor = conn.cursor()
    cursor.execute("SELECT id, ner FROM recipes ORDER BY id")
    rows = cursor.fetchall()
    print(f"  📊 Total recipes in DB: {len(rows)}")
    
    # Build text representations
    texts = []
    valid_ids = []
    for row_id, ner in rows:
        if not ner:
            # Use empty string for recipes without NER
            texts.append("")
            valid_ids.append(row_id)
            continue
        try:
            ings = literal_eval(ner)
            texts.append(" ".join(ings))
        except:
            texts.append(ner)
        valid_ids.append(row_id)
    
    print(f"  🧠 Encoding {len(texts)} recipes...")
    
    # Encode in batches to manage memory
    BATCH_SIZE = 10000
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"    Batch {batch_num}/{total_batches} ({len(batch)} recipes)...")
        embeddings = model.encode(batch, show_progress_bar=True, batch_size=256)
        all_embeddings.append(embeddings)
    
    embeddings = np.vstack(all_embeddings).astype(np.float32)
    print(f"  ✅ Embeddings shape: {embeddings.shape}")
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Build IVF-PQ index for memory efficiency
    d = embeddings.shape[1]  # dimension
    n = embeddings.shape[0]  # number of vectors
    
    # Choose index type based on size
    if n > 100000:
        # IVF-PQ for large datasets (memory efficient)
        nlist = min(int(np.sqrt(n)), 4096)  # number of clusters
        m = 48  # sub-quantizers (must divide d)
        if d % m != 0:
            m = 32
        nbits = 8
        
        quantizer = faiss.IndexFlatIP(d)
        index = faiss.IndexIVFPQ(quantizer, d, nlist, m, nbits, faiss.METRIC_INNER_PRODUCT)
        
        print(f"  🏗️  Training IVF-PQ index (nlist={nlist}, m={m})...")
        # Train on a sample if dataset is very large
        train_size = min(n, 500000)
        if train_size < n:
            indices = np.random.choice(n, train_size, replace=False)
            train_data = embeddings[indices]
        else:
            train_data = embeddings
        
        index.train(train_data)
    else:
        # Flat index for smaller datasets
        index = faiss.IndexFlatIP(d)
    
    print(f"  📥 Adding {n} vectors to index...")
    index.add(embeddings)
    
    # Save optimized index
    opt_index_path = INDEX_DIR / "recipe_index_opt.faiss"
    faiss.write_index(index, str(opt_index_path))
    print(f"  💾 Saved index to: {opt_index_path}")
    print(f"     Index size: {opt_index_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"     Total vectors: {index.ntotal}")
    
    # Also save the finetuned version path if applicable
    if os.path.isdir(FINETUNED_MODEL):
        ft_index_path = INDEX_DIR / "recipe_index_finetuned_opt.faiss"
        faiss.write_index(index, str(ft_index_path))
        print(f"  💾 Also saved as finetuned index: {ft_index_path}")


def main():
    print("="*60)
    print("🌍 PlatePlanner — International Recipe Integration")
    print("="*60)
    
    # 1. Connect to DB & migrate schema
    print("\n📋 Step 1: Database schema migration")
    conn = sqlite3.connect(str(DB_PATH))
    migrate_schema(conn)
    
    # 2. Get existing data for deduplication
    print("\n📋 Step 2: Loading existing recipes for deduplication")
    existing_titles = get_existing_titles(conn)
    max_id = get_max_id(conn)
    print(f"  📊 Existing recipes: {len(existing_titles)}")
    print(f"  🔢 Max ID: {max_id}")
    
    # 3. Parse and insert each dataset
    print("\n📋 Step 3: Parsing and integrating datasets")
    
    total_inserted = 0
    parsers = {
        "recipes_with_nutrition.csv": parse_recipes_with_nutrition,
        "food_com_recipes.csv": parse_food_com,
        "cooking_recipes_large.csv": parse_cooking_recipes_large,
    }
    
    for filename, parser in parsers.items():
        filepath = RAW_DIR / filename
        if not filepath.exists():
            print(f"\n  ⚠️  {filename} not found, skipping...")
            continue
        
        print(f"\n  {'─'*50}")
        recipes = parser(filepath)
        
        if recipes:
            inserted = insert_recipes(conn, recipes, existing_titles, max_id + total_inserted)
            total_inserted += inserted
            print(f"  📥 Inserted: {inserted} new recipes (skipped {len(recipes) - inserted} duplicates)")
    
    # 4. Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recipes")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT source, COUNT(*) FROM recipes GROUP BY source ORDER BY COUNT(*) DESC")
    source_counts = cursor.fetchall()
    
    cursor.execute("SELECT cuisine, COUNT(*) FROM recipes WHERE cuisine IS NOT NULL AND cuisine != '' GROUP BY cuisine ORDER BY COUNT(*) DESC LIMIT 20")
    cuisine_counts = cursor.fetchall()
    
    print(f"\n{'='*60}")
    print(f"📊 Integration Summary")
    print(f"{'='*60}")
    print(f"  Total recipes in DB: {final_count:,}")
    print(f"  New recipes added:   {total_inserted:,}")
    print(f"\n  Recipes by source:")
    for source, count in source_counts:
        source_name = source or "RecipeNLG (original)"
        print(f"    {source_name}: {count:,}")
    
    if cuisine_counts:
        print(f"\n  Top cuisines:")
        for cuisine, count in cuisine_counts:
            print(f"    {cuisine}: {count:,}")
    
    # 5. Rebuild FAISS index
    print("\n📋 Step 4: Rebuilding FAISS index")
    if total_inserted > 0:
        print("  🔄 New recipes were added — rebuilding FAISS index...")
        rebuild_faiss_index(conn)
    else:
        print("  ⏭️  No new recipes added, skipping index rebuild.")
    
    conn.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
