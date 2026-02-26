import logging
from typing import Dict, List, Any
from src.services.retrieval_service import retrieval_service
from src.services.ontology_service import ontology_service
from src.services.nutrient_service import nutrient_service
from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)

async def run_hybrid_pipeline(query: str, goals: Dict[str, Any], restrictions: List[str]) -> Dict[str, Any]:
    """
    Orchestrates the 4-stage Hybrid Retrieval system.
    
    Stages:
    1. Retrieval: Broad semantic search via FAISS.
    2. Ontology: Strict deterministic filtering via Neo4j Graph queries.
    3. Nutrient: Mathematical ranking based on goal distance.
    4. RAG: Generative context for the top result.
    """
    logger.info(f"🚀 [HybridPipeline] Starting pipeline for query: '{query}'")
    
    # Stage 1: Semantic Retrieval
    candidates = retrieval_service.get_candidates(query, k=100)
    if not candidates:
        logger.warning(f"⚠️ [HybridPipeline] Stage 1 returned 0 candidates for query: {query}")
        return {"status": "error", "message": "No recipes found for the query."}
        
    logger.info(f"✅ [HybridPipeline] Stage 1 Retrieved {len(candidates)} candidates.")
    
    # Stage 2: Ontology Reasoning
    safe_recipes = ontology_service.filter_unsafe_recipes(candidates, restrictions)
    if not safe_recipes:
        logger.warning(f"⚠️ [HybridPipeline] Stage 2 filtered ALL recipes due to restrictions: {restrictions}")
        return {"status": "error", "message": "No recipes passed the strict dietary constraints."}
        
    logger.info(f"✅ [HybridPipeline] Stage 2 Kept {len(safe_recipes)} safe recipes.")
    
    # Stage 3: Nutrient Scoring
    ranked_recipes = nutrient_service.rank_by_nutrition(safe_recipes, goals)
    if not ranked_recipes:
        return {"status": "error", "message": "Failed to rank recipes by nutrition."}
        
    logger.info(f"✅ [HybridPipeline] Stage 3 Ranked recipes by fitness score.")
        
    # Stage 4: Generative Explainability
    best_recipe = ranked_recipes[0]
    rag_service = RAGService()
    
    user_context = {"goals": goals, "restrictions": restrictions}
    explanation = await rag_service.generate_explanation(best_recipe, user_context)
    
    best_recipe["explanation"] = explanation
    logger.info(f"✅ [HybridPipeline] Stage 4 generated explanation.")
    
    return {
        "status": "success",
        "top_recommendations": ranked_recipes[:5],
        "primary_explanation": explanation
    }
