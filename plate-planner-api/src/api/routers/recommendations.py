from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.pipelines.hybrid_recommendation import run_hybrid_pipeline

router = APIRouter(prefix="/recommend", tags=["Recommendations"])

class HybridRecommendRequest(BaseModel):
    query: str = Field(..., description="Natural language query, e.g., 'A rainy day comfort food'")
    goals: Dict[str, Any] = Field(default={}, description="Nutritional goals, e.g., {'target_calories': 600}")
    restrictions: List[str] = Field(default=[], description="List of strict strings to avoid, e.g., ['peanut', 'dairy']")

@router.post(
    "/hybrid",
    status_code=status.HTTP_200_OK,
    summary="Get hybrid AI recipe recommendations",
)
async def hybrid_recommendation_endpoint(request: HybridRecommendRequest):
    """
    Executes the 4-stage Hybrid Retrieval Architecture:
    1. FAISS Semantic Search
    2. Neo4j Ontology Reasoning
    3. Mathematical Nutrient Scoring
    4. RAG Generative LLM Explanation
    """
    try:
        results = await run_hybrid_pipeline(
            query=request.query,
            goals=request.goals,
            restrictions=request.restrictions
        )
        
        if results.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=results.get("message")
            )
            
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid Recommendation failed: {str(e)}"
        )
