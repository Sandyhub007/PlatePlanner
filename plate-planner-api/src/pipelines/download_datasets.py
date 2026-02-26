"""
Download international recipe datasets from HuggingFace and prepare for integration.

Datasets downloaded:
1. RecipeNLG (mbien/recipe_nlg) - Already have, skip if present
2. Food.com recipes (AkashPS11/recipes_data_food.com) - 500K+ with tags & nutrition
3. Recipes with Nutrition (datahiveai/recipes-with-nutrition) - 40K with cuisine labels
4. CookingRecipes (CodeKapital/CookingRecipes) - Large multilingual recipes
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Optional

# Ensure we can import from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

RAW_DIR = PROJECT_ROOT / "src" / "data" / "raw" / "international"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def download_huggingface_datasets():
    """Download recipe datasets from HuggingFace."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Installing 'datasets' library...")
        os.system(f"{sys.executable} -m pip install datasets")
        from datasets import load_dataset

    datasets_to_download = [
        {
            "name": "recipes_with_nutrition",
            "hf_path": "datahiveai/recipes-with-nutrition",
            "description": "40K recipes with cuisine labels and nutrition",
            "output_file": RAW_DIR / "recipes_with_nutrition.csv",
        },
        {
            "name": "food_com_recipes",
            "hf_path": "AkashPS11/recipes_data_food.com",
            "description": "500K+ Food.com recipes with tags and nutrition",
            "output_file": RAW_DIR / "food_com_recipes.csv",
        },
        {
            "name": "cooking_recipes_large",
            "hf_path": "CodeKapital/CookingRecipes",
            "description": "Large set of cooking recipes",
            "output_file": RAW_DIR / "cooking_recipes_large.csv",
        },
    ]

    for ds_info in datasets_to_download:
        output_file = ds_info["output_file"]
        if output_file.exists():
            print(f"⏭️  {ds_info['name']} already downloaded, skipping...")
            continue

        print(f"\n{'='*60}")
        print(f"📥 Downloading: {ds_info['description']}")
        print(f"   Source: {ds_info['hf_path']}")
        print(f"{'='*60}")

        try:
            ds = load_dataset(ds_info["hf_path"])
            # Get the main split (usually 'train')
            split_name = list(ds.keys())[0]
            data = ds[split_name]

            print(f"   ✅ Loaded {len(data)} rows from split '{split_name}'")
            print(f"   Columns: {data.column_names}")

            # Save as CSV
            data.to_csv(str(output_file))
            print(f"   💾 Saved to {output_file}")
            print(f"   📊 File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

        except Exception as e:
            print(f"   ❌ Failed to download {ds_info['name']}: {e}")
            continue

    print(f"\n{'='*60}")
    print("✅ All downloads complete!")
    print(f"📁 Files saved to: {RAW_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    download_huggingface_datasets()
