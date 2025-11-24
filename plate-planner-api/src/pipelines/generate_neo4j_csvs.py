"""
Generate Neo4j CSV files from RecipeNLG dataset.
Creates: ingredients.csv, recipes.csv, recipe_ingredients.csv
"""
import ast
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Paths
RAW_DATA = Path("src/data/raw/RecipeNLG_dataset.csv")
OUTPUT_DIR = Path("src/data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Limit for processing
LIMIT = 100000  # 100K recipes for Neo4j

print(f"📥 Loading RecipeNLG dataset (limit={LIMIT})...")
df = pd.read_csv(RAW_DATA, nrows=LIMIT)
print(f"✅ Loaded {len(df)} recipes")

# Parse NER column (cleaned ingredient names)
print("🔍 Parsing ingredients...")
df["NER"] = df["NER"].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])

# Clean up ingredients (normalize)
def clean_ingredient(ing):
    """Basic ingredient normalization"""
    return ing.lower().strip()

# Build ingredient and recipe data structures
print("🧮 Processing recipes and ingredients...")
ingredient_set = set()
recipe_data = []
recipe_ingredient_relationships = []

for idx, row in df.iterrows():
    recipe_id = idx
    title = row["title"]
    directions = row.get("directions", "")
    link = row.get("link", "")
    source = row.get("source", "")
    
    # Get ingredients for this recipe
    ingredients = row["NER"]
    if not isinstance(ingredients, list):
        continue
    
    # Clean ingredients
    cleaned_ingredients = [clean_ingredient(ing) for ing in ingredients if ing]
    cleaned_ingredients = [ing for ing in cleaned_ingredients if len(ing) > 1]  # Filter too short
    
    if not cleaned_ingredients:
        continue
    
    # Add to recipe data
    recipe_data.append({
        "recipe_id": recipe_id,
        "title": title,
        "directions": directions[:500] if directions else "",  # Truncate long directions
        "link": link,
        "source": source
    })
    
    # Track unique ingredients
    for ingredient in cleaned_ingredients:
        ingredient_set.add(ingredient)
        
        # Create relationship
        recipe_ingredient_relationships.append({
            "recipe_id": recipe_id,
            "ingredient_name": ingredient
        })

print(f"✅ Processed {len(recipe_data)} recipes with {len(ingredient_set)} unique ingredients")

# Create ingredients DataFrame
print("📝 Creating ingredients.csv...")
ingredients_df = pd.DataFrame([
    {"name": ing} for ing in sorted(ingredient_set)
])
ingredients_df.to_csv(OUTPUT_DIR / "ingredients.csv", index=False)
print(f"✅ Saved {len(ingredients_df)} ingredients to {OUTPUT_DIR / 'ingredients.csv'}")

# Create recipes DataFrame
print("📝 Creating recipes.csv...")
recipes_df = pd.DataFrame(recipe_data)
recipes_df.to_csv(OUTPUT_DIR / "recipes.csv", index=False)
print(f"✅ Saved {len(recipes_df)} recipes to {OUTPUT_DIR / 'recipes.csv'}")

# Create recipe-ingredient relationships DataFrame
print("📝 Creating recipe_ingredients.csv...")
relationships_df = pd.DataFrame(recipe_ingredient_relationships)
relationships_df.to_csv(OUTPUT_DIR / "recipe_ingredients.csv", index=False)
print(f"✅ Saved {len(relationships_df)} relationships to {OUTPUT_DIR / 'recipe_ingredients.csv'}")

# Summary statistics
print("\n📊 SUMMARY:")
print(f"   - Recipes: {len(recipes_df):,}")
print(f"   - Unique Ingredients: {len(ingredients_df):,}")
print(f"   - Recipe-Ingredient Relationships: {len(relationships_df):,}")
print(f"   - Avg ingredients per recipe: {len(relationships_df) / len(recipes_df):.1f}")

# Find most common ingredients
ingredient_counts = relationships_df["ingredient_name"].value_counts()
print(f"\n🔝 Top 10 Most Common Ingredients:")
for i, (ing, count) in enumerate(ingredient_counts.head(10).items(), 1):
    print(f"   {i}. {ing}: {count:,} recipes")

print("\n✨ Neo4j CSV generation complete!")
print(f"   Ready for: task neo4j:bootstrap")

