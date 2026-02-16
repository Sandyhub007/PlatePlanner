import pandas as pd
import ast
from src.utils.dietary_classifier import DietaryClassifier
from src.config.paths import DataPaths
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def tag_recipes():
    paths = DataPaths()
    input_path = paths.recipe_metadata
    
    logging.info(f"Loading recipes from {input_path}...")
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        logging.error(f"File not found: {input_path}")
        return

    logging.info(f"Loaded {len(df)} recipes. Initializing classifier...")
    classifier = DietaryClassifier()

    # Lists to store new column data
    is_veg = []
    is_vegan = []
    is_gf = []
    is_df = []
    allergens_list = []

    logging.info("Starting classification...")
    
    # Iterate with progress bar
    for index, row in tqdm(df.iterrows(), total=len(df)):
        # Parse ingredients (NER column)
        try:
            # NER is usually a string representation of a list: "['ing1', 'ing2']"
            ingredients = ast.literal_eval(row['NER'])
        except (ValueError, SyntaxError):
            # Fallback for malformed strings
            ingredients = str(row['NER']).split(",")
        except Exception:
            ingredients = []

        # Classify
        result = classifier.classify(ingredients)
        
        is_veg.append(result['is_vegetarian'])
        is_vegan.append(result['is_vegan'])
        is_gf.append(result['is_gluten_free'])
        is_df.append(result['is_dairy_free'])
        allergens_list.append(result['allergens'])

    # Add new columns
    df['is_vegetarian'] = is_veg
    df['is_vegan'] = is_vegan
    df['is_gluten_free'] = is_gf
    df['is_dairy_free'] = is_df
    df['allergens'] = allergens_list

    # Save back to CSV
    # We will overwrite the existing file so the API picks it up automatically
    logging.info(f"Saving tagged metadata to {input_path}...")
    df.to_csv(input_path, index=False)
    
    logging.info("✅ Done! Recipes have been tagged with dietary info.")
    
    # Print summary stats
    logging.info(f"Vegetarian: {sum(is_veg)}")
    logging.info(f"Vegan: {sum(is_vegan)}")
    logging.info(f"Gluten-Free: {sum(is_gf)}")
    logging.info(f"Dairy-Free: {sum(is_df)}")

if __name__ == "__main__":
    tag_recipes()
