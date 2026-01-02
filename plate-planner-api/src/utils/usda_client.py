"""
USDA FoodData Central API Client
Fetches nutrition data from USDA's official database
"""
import os
import logging
from typing import Optional, Dict, List, Any
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class USDAClient:
    """
    Client for interacting with USDA FoodData Central API
    
    API Documentation: https://fdc.nal.usda.gov/api-guide.html
    Rate Limit: 3600 requests/hour
    """
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize USDA API client
        
        Args:
            api_key: USDA API key (defaults to env var USDA_API_KEY)
        """
        self.api_key = api_key or os.getenv("USDA_API_KEY")
        if not self.api_key:
            logger.warning("No USDA API key found. Using demo mode with limited functionality.")
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(days=7)  # Cache for 1 week
        self.last_cache_clean = datetime.now()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        if (now - self.last_cache_clean) > timedelta(hours=1):
            expired_keys = [
                key for key, value in self.cache.items()
                if (now - value.get("cached_at", now)) > self.cache_ttl
            ]
            for key in expired_keys:
                del self.cache[key]
            self.last_cache_clean = now
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    async def search_foods(
        self, 
        query: str, 
        data_type: Optional[List[str]] = None,
        page_size: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for foods in USDA database
        
        Args:
            query: Search term (e.g., "chicken breast")
            data_type: Filter by data types (e.g., ["Foundation", "SR Legacy"])
            page_size: Number of results to return
        
        Returns:
            List of food items with basic info
        """
        if not self.api_key:
            logger.warning("Cannot search without API key")
            return []
        
        # Check cache first
        cache_key = f"search:{query}:{data_type}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["cached_at"]) < self.cache_ttl:
                logger.debug(f"Cache hit for search: {query}")
                return cached["data"]
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/foods/search"
        params = {
            "api_key": self.api_key,
            "query": query,
            "pageSize": page_size
        }
        
        if data_type:
            params["dataType"] = data_type
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    foods = data.get("foods", [])
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        "data": foods,
                        "cached_at": datetime.now()
                    }
                    
                    logger.info(f"Found {len(foods)} foods for query: {query}")
                    return foods
                else:
                    logger.error(f"USDA API error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error searching USDA: {e}")
            return []
    
    async def get_food_details(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed nutrition information for a food item
        
        Args:
            fdc_id: FoodData Central ID
        
        Returns:
            Detailed food information including all nutrients
        """
        if not self.api_key:
            logger.warning("Cannot get details without API key")
            return None
        
        # Check cache
        cache_key = f"details:{fdc_id}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["cached_at"]) < self.cache_ttl:
                logger.debug(f"Cache hit for FDC ID: {fdc_id}")
                return cached["data"]
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/food/{fdc_id}"
        params = {"api_key": self.api_key}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        "data": data,
                        "cached_at": datetime.now()
                    }
                    
                    logger.info(f"Retrieved details for FDC ID: {fdc_id}")
                    return data
                else:
                    logger.error(f"USDA API error for FDC ID {fdc_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting food details: {e}")
            return None
    
    def extract_nutrition(self, food_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standard nutrition values from USDA food data
        
        Args:
            food_data: Raw food data from USDA API
        
        Returns:
            Standardized nutrition dict (per 100g)
        """
        nutrients = food_data.get("foodNutrients", [])
        
        # Nutrient IDs from USDA database
        nutrient_map = {
            "Energy": 1008,  # Calories (kcal)
            "Protein": 1003,  # Protein (g)
            "Total lipid (fat)": 1004,  # Fat (g)
            "Carbohydrate, by difference": 1005,  # Carbs (g)
            "Fiber, total dietary": 1079,  # Fiber (g)
            "Sugars, total including NLEA": 2000,  # Sugar (g)
            "Sodium, Na": 1093,  # Sodium (mg)
            "Fatty acids, total saturated": 1258,  # Saturated fat (g)
            "Fatty acids, total trans": 1257,  # Trans fat (g)
            "Vitamin A, RAE": 1106,  # Vitamin A (mcg)
            "Vitamin C, total ascorbic acid": 1162,  # Vitamin C (mg)
            "Calcium, Ca": 1087,  # Calcium (mg)
            "Iron, Fe": 1089,  # Iron (mg)
            "Potassium, K": 1092,  # Potassium (mg)
        }
        
        nutrition = {
            "calories": 0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
            "sodium_mg": 0,
            "saturated_fat_g": 0.0,
            "trans_fat_g": 0.0,
            "vitamin_a_mcg": 0,
            "vitamin_c_mg": 0,
            "calcium_mg": 0,
            "iron_mg": 0.0,
            "potassium_mg": 0,
            "usda_fdc_id": food_data.get("fdcId"),
            "description": food_data.get("description"),
            "data_source": "usda",
            "confidence_score": 1.0
        }
        
        for nutrient in nutrients:
            name = nutrient.get("nutrient", {}).get("name")
            value = nutrient.get("amount", 0)
            
            if name == "Energy":
                nutrition["calories"] = int(value)
            elif name == "Protein":
                nutrition["protein_g"] = round(float(value), 2)
            elif name == "Total lipid (fat)":
                nutrition["fat_g"] = round(float(value), 2)
            elif name == "Carbohydrate, by difference":
                nutrition["carbs_g"] = round(float(value), 2)
            elif name == "Fiber, total dietary":
                nutrition["fiber_g"] = round(float(value), 2)
            elif name == "Sugars, total including NLEA":
                nutrition["sugar_g"] = round(float(value), 2)
            elif name == "Sodium, Na":
                nutrition["sodium_mg"] = int(value)
            elif name == "Fatty acids, total saturated":
                nutrition["saturated_fat_g"] = round(float(value), 2)
            elif name == "Fatty acids, total trans":
                nutrition["trans_fat_g"] = round(float(value), 2)
            elif name == "Vitamin A, RAE":
                nutrition["vitamin_a_mcg"] = int(value)
            elif name == "Vitamin C, total ascorbic acid":
                nutrition["vitamin_c_mg"] = int(value)
            elif name == "Calcium, Ca":
                nutrition["calcium_mg"] = int(value)
            elif name == "Iron, Fe":
                nutrition["iron_mg"] = round(float(value), 2)
            elif name == "Potassium, K":
                nutrition["potassium_mg"] = int(value)
        
        return nutrition
    
    async def get_ingredient_nutrition(
        self, 
        ingredient_name: str,
        prefer_data_type: str = "SR Legacy"
    ) -> Optional[Dict[str, Any]]:
        """
        Search and retrieve nutrition for an ingredient
        
        Args:
            ingredient_name: Name of ingredient (e.g., "chicken breast")
            prefer_data_type: Preferred USDA data type
        
        Returns:
            Nutrition dictionary or None if not found
        """
        # Search for the ingredient
        foods = await self.search_foods(ingredient_name, page_size=10)
        
        if not foods:
            logger.warning(f"No USDA data found for: {ingredient_name}")
            return None
        
        # Try to find best match (preferably SR Legacy or Foundation)
        best_match = None
        for food in foods:
            data_type = food.get("dataType")
            if data_type == prefer_data_type:
                best_match = food
                break
        
        # Fallback to first result
        if not best_match:
            best_match = foods[0]
        
        fdc_id = best_match.get("fdcId")
        if not fdc_id:
            return None
        
        # Get detailed nutrition
        details = await self.get_food_details(fdc_id)
        if not details:
            return None
        
        nutrition = self.extract_nutrition(details)
        nutrition["ingredient_name"] = ingredient_name
        
        return nutrition
    
    def get_fallback_nutrition(self, ingredient_name: str) -> Dict[str, Any]:
        """
        Provide estimated nutrition when USDA data unavailable
        
        Args:
            ingredient_name: Name of ingredient
        
        Returns:
            Estimated nutrition dictionary
        """
        # Basic estimates by category
        name_lower = ingredient_name.lower()
        
        if any(meat in name_lower for meat in ["chicken", "beef", "pork", "turkey", "lamb"]):
            return {
                "calories": 165,
                "protein_g": 31.0,
                "carbs_g": 0.0,
                "fat_g": 3.6,
                "fiber_g": 0.0,
                "sugar_g": 0.0,
                "sodium_mg": 70,
                "data_source": "estimated",
                "confidence_score": 0.5
            }
        elif any(veg in name_lower for veg in ["lettuce", "spinach", "kale", "broccoli", "tomato"]):
            return {
                "calories": 25,
                "protein_g": 2.0,
                "carbs_g": 5.0,
                "fat_g": 0.3,
                "fiber_g": 2.0,
                "sugar_g": 2.0,
                "sodium_mg": 25,
                "data_source": "estimated",
                "confidence_score": 0.4
            }
        else:
            # Generic fallback
            return {
                "calories": 100,
                "protein_g": 3.0,
                "carbs_g": 15.0,
                "fat_g": 3.0,
                "fiber_g": 1.0,
                "sugar_g": 2.0,
                "sodium_mg": 50,
                "data_source": "estimated",
                "confidence_score": 0.3
            }


# Singleton instance
_usda_client: Optional[USDAClient] = None

def get_usda_client() -> USDAClient:
    """Get or create USDA client singleton"""
    global _usda_client
    if _usda_client is None:
        _usda_client = USDAClient()
    return _usda_client

