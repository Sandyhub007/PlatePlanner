#!/usr/bin/env python3
"""
Script to classify all recipes for dietary restrictions and allergens
Run this after Phase 4A Week 1 migrations to populate dietary tags
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.neo4j_service import Neo4jService
from src.services.dietary_classifier import DietaryClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to classify all recipes"""
    logger.info("="*60)
    logger.info("Starting Recipe Dietary Classification")
    logger.info("="*60)
    
    try:
        # Initialize services
        logger.info("Connecting to Neo4j...")
        neo4j_service = Neo4jService()
        classifier = DietaryClassifier(neo4j_service)
        
        # Classify all recipes
        logger.info("Classifying recipes...")
        stats = classifier.classify_all_recipes(batch_size=50)
        
        logger.info("="*60)
        logger.info("Classification Complete!")
        logger.info(f"Total recipes: {stats['total']}")
        logger.info(f"Classified: {stats['classified']}")
        logger.info("="*60)
        
        # Get summary statistics
        query = """
        MATCH (r:Recipe)
        RETURN 
            count(r) as total,
            sum(CASE WHEN r.is_vegetarian THEN 1 ELSE 0 END) as vegetarian,
            sum(CASE WHEN r.is_vegan THEN 1 ELSE 0 END) as vegan,
            sum(CASE WHEN r.is_gluten_free THEN 1 ELSE 0 END) as gluten_free,
            sum(CASE WHEN r.is_dairy_free THEN 1 ELSE 0 END) as dairy_free,
            sum(CASE WHEN r.is_keto_friendly THEN 1 ELSE 0 END) as keto,
            sum(CASE WHEN r.is_high_protein THEN 1 ELSE 0 END) as high_protein
        """
        
        results = neo4j_service.execute_query(query)
        if results:
            summary = results[0]
            logger.info("\n📊 Dietary Classification Summary:")
            logger.info(f"  Total recipes: {summary['total']}")
            logger.info(f"  🥬 Vegetarian: {summary['vegetarian']} ({summary['vegetarian']/summary['total']*100:.1f}%)")
            logger.info(f"  🌱 Vegan: {summary['vegan']} ({summary['vegan']/summary['total']*100:.1f}%)")
            logger.info(f"  🌾 Gluten-free: {summary['gluten_free']} ({summary['gluten_free']/summary['total']*100:.1f}%)")
            logger.info(f"  🥛 Dairy-free: {summary['dairy_free']} ({summary['dairy_free']/summary['total']*100:.1f}%)")
            logger.info(f"  🥓 Keto-friendly: {summary['keto']} ({summary['keto']/summary['total']*100:.1f}%)")
            logger.info(f"  💪 High-protein: {summary['high_protein']} ({summary['high_protein']/summary['total']*100:.1f}%)")
        
        # Get allergen statistics
        allergen_query = """
        MATCH (r:Recipe)
        WHERE size(r.allergens) > 0
        UNWIND r.allergens as allergen
        RETURN allergen, count(*) as count
        ORDER BY count DESC
        """
        
        allergen_results = neo4j_service.execute_query(allergen_query)
        if allergen_results:
            logger.info("\n⚠️  Allergen Detection Summary:")
            for row in allergen_results:
                logger.info(f"  {row['allergen']}: {row['count']} recipes")
        
        logger.info("\n✅ All recipes successfully classified!")
        
    except Exception as e:
        logger.error(f"Error during classification: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

