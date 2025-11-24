"""
Train Word2Vec model on RecipeNLG ingredient co-occurrences.
This creates proper ingredient similarity embeddings.
"""
import ast
import pandas as pd
from pathlib import Path
from gensim.models import Word2Vec

# Paths
RAW_DATA = Path("src/data/raw/RecipeNLG_dataset.csv")
MODEL_DIR = Path("src/data/models/ingredient_substitution")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = MODEL_DIR / "ingredient_w2v.model"

# Training parameters
LIMIT = 100000  # Train on 100K recipes (can use more or all 2.2M)
VECTOR_SIZE = 100
WINDOW = 5  # Ingredients within 5 positions are considered related
MIN_COUNT = 10  # Only include ingredients that appear in at least 10 recipes
WORKERS = 4
EPOCHS = 10

print(f"📥 Loading RecipeNLG dataset (limit={LIMIT})...")
df = pd.read_csv(RAW_DATA, nrows=LIMIT)
print(f"✅ Loaded {len(df)} recipes")

# Parse NER column and prepare training data
print("🔍 Preparing ingredient sequences...")
ingredient_sequences = []

for idx, row in df.iterrows():
    ingredients = row["NER"]
    
    # Parse the ingredient list
    if pd.isna(ingredients):
        continue
    
    try:
        ing_list = ast.literal_eval(ingredients)
    except:
        continue
    
    if not isinstance(ing_list, list) or len(ing_list) == 0:
        continue
    
    # Clean and normalize ingredients
    cleaned = [ing.lower().strip() for ing in ing_list if ing]
    cleaned = [ing for ing in cleaned if len(ing) > 1]
    
    if len(cleaned) >= 2:  # Need at least 2 ingredients to learn relationships
        ingredient_sequences.append(cleaned)

print(f"✅ Prepared {len(ingredient_sequences)} ingredient sequences")

# Count unique ingredients
all_ingredients = set()
for seq in ingredient_sequences:
    all_ingredients.update(seq)
print(f"📊 Found {len(all_ingredients)} unique ingredients before filtering")

# Train Word2Vec model
print(f"\n🤖 Training Word2Vec model...")
print(f"   - Vector size: {VECTOR_SIZE}")
print(f"   - Window: {WINDOW}")
print(f"   - Min count: {MIN_COUNT}")
print(f"   - Epochs: {EPOCHS}")
print(f"   - Workers: {WORKERS}")

model = Word2Vec(
    sentences=ingredient_sequences,
    vector_size=VECTOR_SIZE,
    window=WINDOW,
    min_count=MIN_COUNT,
    workers=WORKERS,
    epochs=EPOCHS,
    sg=0,  # Use CBOW (0) or Skip-gram (1)
    negative=5,
    seed=42
)

# Save the model
print(f"\n💾 Saving model to {OUTPUT_PATH}...")
model.save(str(OUTPUT_PATH))
print(f"✅ Model saved successfully!")

# Model statistics
vocab_size = len(model.wv)
print(f"\n📊 MODEL STATISTICS:")
print(f"   - Vocabulary size: {vocab_size:,} ingredients")
print(f"   - Vector dimensions: {VECTOR_SIZE}")
print(f"   - Training recipes: {len(ingredient_sequences):,}")

# Test the model with some examples
print(f"\n🧪 TESTING SIMILARITY (examples):")
test_ingredients = ["butter", "chicken", "tomato", "garlic", "flour"]

for ingredient in test_ingredients:
    if ingredient in model.wv:
        similar = model.wv.most_similar(ingredient, topn=5)
        print(f"\n   {ingredient} is similar to:")
        for sim_ing, score in similar:
            print(f"      - {sim_ing}: {score:.3f}")
    else:
        print(f"\n   {ingredient}: not in vocabulary (appears in < {MIN_COUNT} recipes)")

print("\n✨ Word2Vec training complete!")
print(f"   Ready for: task neo4j:bootstrap (to build SIMILAR_TO edges)")

