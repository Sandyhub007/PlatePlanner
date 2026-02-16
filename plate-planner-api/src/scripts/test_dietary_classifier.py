from src.utils.dietary_classifier import DietaryClassifier
import pandas as pd
from src.config.paths import DataPaths
import ast

def test_classifier():
    print("🥗 Testing Dietary Classifier...")
    classifier = DietaryClassifier()
    
    # 1. Test with manual specific cases
    test_cases = [
        {
            "name": "Steak & Eggs",
            "ings": ["10oz Ribeye Steak", "2 Eggs", "Butter", "Salt", "Pepper"],
            "expected_vegan": False
        },
        {
            "name": "Green Smoothie",
            "ings": ["Spinach", "Kale", "Apple", "Banana", "Water"],
            "expected_vegan": True
        },
        {
            "name": "Standard Pasta",
            "ings": ["Wheat Pasta", "Tomato Sauce", "Parmesan Cheese"],
            "expected_vegan": False,
            "expected_gf": False
        }
    ]
    
    print("\n--- Manual Cases ---")
    for case in test_cases:
        result = classifier.classify(case["ings"])
        print(f"Recipe: {case['name']}")
        print(f"  Ingredients: {case['ings']}")
        print(f"  Result: Vegan={result['is_vegan']}, GF={result['is_gluten_free']}, DF={result['is_dairy_free']}")
        
        if "expected_vegan" in case:
            assert result['is_vegan'] == case['expected_vegan'], f"Failed vegan check for {case['name']}"
    
    # 2. Test with real data (first 5 recipes)
    print("\n--- Real Data Sample (Top 5) ---")
    paths = DataPaths()
    try:
        df = pd.read_csv(paths.recipe_metadata, nrows=5)
        for _, row in df.iterrows():
            # Parse NER or ingredients string
            try:
                ings = ast.literal_eval(row['NER'])
            except:
                ings = row['NER'].split(",")
                
            result = classifier.classify(ings)
            print(f"[{row['title']}]")
            print(f"  Tags: {result}")
    except Exception as e:
        print(f"Could not load real data: {e}")

if __name__ == "__main__":
    test_classifier()
