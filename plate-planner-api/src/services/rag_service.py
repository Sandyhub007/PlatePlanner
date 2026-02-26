"""
RAG (Retrieval-Augmented Generation) Service for Recipe Intelligence
====================================================================
Augments the existing FAISS recipe retrieval with LLM-powered generation
to provide intelligent, context-aware responses about recipes.

Features:
  - Recipe Adaptation: Modify recipes based on pantry/dietary needs
  - Cooking Tips: Context-aware cooking advice
  - Substitution Reasoning: Explain why a substitute works
  - Meal Planning: Intelligent meal plan generation

Supports multiple LLM backends:
  - OpenAI (GPT-4, GPT-3.5-turbo)
  - Google (Gemini Pro)
  - Local (Ollama — llama3, mistral)

Usage:
  from src.services.rag_service import RAGService
  rag = RAGService()
  response = await rag.adapt_recipe("Chicken Parmesan", dietary="vegan", pantry=["tofu", "breadcrumbs"])
"""

import logging
import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("plate_planner.rag")

# ─── Config ───────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Model selection
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

# Auto-detect best provider: explicit env var > API key presence > fallback
def _detect_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER", "")
    if explicit:
        return explicit
    if GOOGLE_API_KEY:
        return "google"
    if OPENAI_API_KEY:
        return "openai"
    return "ollama"  # fallback to local

LLM_PROVIDER = _detect_provider()
logger.info(f"LLM provider auto-detected: {LLM_PROVIDER}")


# ─── LLM Abstraction ─────────────────────────────────────────────────

# Google model fallback chain (try each until one works)
GOOGLE_MODEL_FALLBACKS = ["gemini-2.5-flash", GOOGLE_MODEL, "gemini-2.0-flash-lite"]

class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    MAX_RETRIES = 2
    RETRY_BASE_DELAY = 5  # seconds
    
    def __init__(self, provider: str = LLM_PROVIDER):
        self.provider = provider
        self._client = None
        self._initialized = False
        self._google_model_name = GOOGLE_MODEL
    
    def _init_client(self):
        """Lazy initialization of LLM client."""
        if self._initialized:
            return
        
        if self.provider == "openai":
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                self._initialized = True
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("openai package not installed. Install with: pip install openai")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")
                
        elif self.provider == "google":
            try:
                from google import genai
                self._client = genai.Client(api_key=GOOGLE_API_KEY)
                self._initialized = True
                logger.info(f"Google Gemini client initialized (model: {self._google_model_name})")
            except ImportError:
                logger.warning("google-genai not installed. Install with: pip install google-genai")
            except Exception as e:
                logger.warning(f"Failed to initialize Google: {e}")
                
        elif self.provider == "ollama":
            try:
                import httpx
                self._client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=60.0)
                self._initialized = True
                logger.info(f"Ollama client initialized ({OLLAMA_MODEL})")
            except ImportError:
                logger.warning("httpx not installed. Install with: pip install httpx")
    
    async def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """Generate a response from the configured LLM."""
        self._init_client()
        
        if not self._initialized:
            return self._fallback_response(prompt)
        
        try:
            if self.provider == "openai":
                return await self._openai_generate(prompt, system_prompt, temperature)
            elif self.provider == "google":
                return await self._google_generate(prompt, system_prompt, temperature)
            elif self.provider == "ollama":
                return await self._ollama_generate(prompt, system_prompt, temperature)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"AI response unavailable: {str(e)[:200]}"
    
    async def _openai_generate(self, prompt: str, system_prompt: str, temperature: float) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self._client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    
    async def _google_generate(self, prompt: str, system_prompt: str, temperature: float) -> str:
        """Generate with Google Gemini, with retry + model fallback."""
        import asyncio
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        config = {"temperature": temperature, "max_output_tokens": 1024}
        
        # Try each model in the fallback chain
        last_error = None
        for model_name in GOOGLE_MODEL_FALLBACKS:
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = await asyncio.to_thread(
                        self._client.models.generate_content,
                        model=model_name,
                        contents=full_prompt,
                        config=config,
                    )
                    return response.text
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower():
                        delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            f"Rate limited on {model_name} (attempt {attempt+1}/{self.MAX_RETRIES}). "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Google Gemini error with {model_name}: {e}")
                        break  # Non-retryable error, try next model
            
            logger.info(f"Falling back from {model_name} to next model...")
        
        raise last_error or Exception("All Google models failed")
    
    async def _ollama_generate(self, prompt: str, system_prompt: str, temperature: float) -> str:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = await self._client.post("/api/generate", json=payload)
        return response.json().get("response", "")
    
    @staticmethod
    def _fallback_response(prompt: str) -> str:
        """Fallback when no LLM is available."""
        return (
            "I'd love to help with that, but no LLM backend is currently configured. "
            "Set one of these environment variables to enable AI features:\n"
            "  • OPENAI_API_KEY (for GPT-4)\n"
            "  • GOOGLE_API_KEY (for Gemini)\n"
            "  • Or run Ollama locally: ollama serve && ollama pull llama3"
        )


# ─── RAG Service ──────────────────────────────────────────────────────
class RAGService:
    """
    Retrieval-Augmented Generation for recipe intelligence.
    Combines FAISS retrieval with LLM generation.
    """
    
    SYSTEM_PROMPT = """You are PlatePlanner AI, a knowledgeable cooking assistant.
You help users adapt recipes, find ingredient substitutions, and plan meals.
Be concise, practical, and encouraging. Always consider food safety.
When suggesting substitutions, explain WHY they work (flavor, texture, function).
Format your responses with clear headers and bullet points when appropriate."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
    
    async def adapt_recipe(
        self,
        recipe_title: str,
        recipe_ingredients: list[str],
        recipe_directions: str,
        dietary: Optional[str] = None,
        pantry: Optional[list[str]] = None,
        missing_ingredients: Optional[list[str]] = None,
        substitutions: Optional[dict] = None,
    ) -> str:
        """
        Adapt a recipe based on dietary needs and available ingredients.
        """
        context_parts = [
            f"Recipe: {recipe_title}",
            f"Ingredients: {', '.join(recipe_ingredients)}",
            f"Directions: {recipe_directions[:500]}",
        ]
        
        if pantry:
            context_parts.append(f"User has: {', '.join(pantry)}")
        if missing_ingredients:
            context_parts.append(f"Missing: {', '.join(missing_ingredients)}")
        if substitutions:
            sub_text = "; ".join(f"{k} → {v}" for k, v in substitutions.items())
            context_parts.append(f"Suggested substitutions: {sub_text}")
        
        context = "\n".join(context_parts)
        
        if dietary:
            prompt = (
                f"{context}\n\n"
                f"Please adapt this recipe to be {dietary}. "
                f"Explain what changes to make and why each substitution works."
            )
        elif missing_ingredients:
            prompt = (
                f"{context}\n\n"
                f"The user is missing some ingredients. Suggest how to adapt the recipe "
                f"using what they have, or recommend the best substitutions. "
                f"Explain how each change affects the final dish."
            )
        else:
            prompt = (
                f"{context}\n\n"
                f"Provide cooking tips and suggestions for this recipe."
            )
        
        return await self.llm.generate(prompt, self.SYSTEM_PROMPT)
    
    async def explain_substitution(
        self,
        original: str,
        substitute: str,
        recipe_context: Optional[str] = None,
    ) -> str:
        """Explain why a substitution works (or doesn't) in a given recipe context."""
        prompt = f"Explain why '{substitute}' can be used as a substitute for '{original}'"
        if recipe_context:
            prompt += f" in the context of making {recipe_context}"
        prompt += ". Cover: flavor impact, texture impact, any ratio adjustments needed, and potential pitfalls."
        
        return await self.llm.generate(prompt, self.SYSTEM_PROMPT, temperature=0.5)

    async def generate_explanation(
        self,
        recipe: dict,
        user_context: dict,
    ) -> str:
        """
        Stage 4: Generate a plain-English explanation of why this mathematically optimized 
        recipe was chosen for the user's specific constraints.
        """
        context_parts = [
            f"Selected Recipe: {recipe.get('title')}",
            f"Ingredients used: {', '.join(recipe.get('ingredients', []))}",
            f"Fitness Score (Math fit): {recipe.get('fitness_score', 0):.2f}",
        ]
        
        goals = user_context.get("goals", {})
        if goals:
            goal_strs = [f"{k}: {v}" for k, v in goals.items()]
            context_parts.append(f"User Goals: {', '.join(goal_strs)}")
            
        restrictions = user_context.get("restrictions", [])
        if restrictions:
            context_parts.append(f"Hard Dietary Restrictions avoided: {', '.join(restrictions)}")
            
        context = "\n".join(context_parts)
        
        prompt = (
            f"{context}\n\n"
            f"Write a friendly 2-3 sentence explanation to the user about why this recipe "
            f"was selected for them as the perfect fit. Highlight how it respects their "
            f"hard dietary restrictions and aligns nicely with their fitness/macro goals."
        )
        
        return await self.llm.generate(prompt, self.SYSTEM_PROMPT, temperature=0.7)
    
    async def suggest_meal_plan(
        self,
        pantry: list[str],
        dietary_preferences: Optional[list[str]] = None,
        days: int = 3,
        meals_per_day: int = 2,
        retrieved_recipes: Optional[list[dict]] = None,
    ) -> str:
        """Generate a meal plan using retrieved recipes and pantry ingredients."""
        context_parts = [
            f"Available ingredients: {', '.join(pantry)}",
            f"Plan for: {days} days, {meals_per_day} meals per day",
        ]
        
        if dietary_preferences:
            context_parts.append(f"Dietary needs: {', '.join(dietary_preferences)}")
        
        if retrieved_recipes:
            recipe_list = "\n".join(
                f"  - {r.get('title', 'Unknown')} (match: {r.get('combined_score', 0):.0%})"
                for r in retrieved_recipes[:10]
            )
            context_parts.append(f"Matching recipes from our database:\n{recipe_list}")
        
        context = "\n".join(context_parts)
        prompt = (
            f"{context}\n\n"
            f"Create a practical meal plan. For each meal, suggest a recipe "
            f"that uses the available ingredients. Note any additional items "
            f"the user would need to buy. Keep it realistic and varied."
        )
        
        return await self.llm.generate(prompt, self.SYSTEM_PROMPT)
    
    async def cooking_tips(
        self,
        recipe_title: str,
        skill_level: str = "intermediate",
    ) -> str:
        """Provide cooking tips for a recipe."""
        prompt = (
            f"Provide 3-5 practical cooking tips for making {recipe_title}. "
            f"Target a {skill_level} cook. Include timing tips, common mistakes, "
            f"and one 'pro tip' that elevates the dish."
        )
        return await self.llm.generate(prompt, self.SYSTEM_PROMPT, temperature=0.6)


# ─── FastAPI Integration ──────────────────────────────────────────────
def create_rag_router():
    """Create FastAPI router for RAG endpoints."""
    from fastapi import APIRouter, Query
    from pydantic import BaseModel
    from typing import Optional, List
    
    router = APIRouter(prefix="/ai", tags=["AI Assistant"])
    rag = RAGService()
    
    class AdaptRecipeRequest(BaseModel):
        recipe_title: str
        recipe_ingredients: List[str]
        recipe_directions: str = ""
        dietary: Optional[str] = None
        pantry: Optional[List[str]] = None
        missing_ingredients: Optional[List[str]] = None
    
    class SubstitutionExplainRequest(BaseModel):
        original: str
        substitute: str
        recipe_context: Optional[str] = None
    
    class MealPlanRequest(BaseModel):
        pantry: List[str]
        dietary_preferences: Optional[List[str]] = None
        days: int = 3
        meals_per_day: int = 2
    
    class AIResponse(BaseModel):
        response: str
        provider: str
    
    @router.post("/adapt-recipe", response_model=AIResponse)
    async def adapt_recipe(request: AdaptRecipeRequest):
        result = await rag.adapt_recipe(
            recipe_title=request.recipe_title,
            recipe_ingredients=request.recipe_ingredients,
            recipe_directions=request.recipe_directions,
            dietary=request.dietary,
            pantry=request.pantry,
            missing_ingredients=request.missing_ingredients,
        )
        return AIResponse(response=result, provider=rag.llm.provider)
    
    @router.post("/explain-substitution", response_model=AIResponse)
    async def explain_substitution(request: SubstitutionExplainRequest):
        result = await rag.explain_substitution(
            original=request.original,
            substitute=request.substitute,
            recipe_context=request.recipe_context,
        )
        return AIResponse(response=result, provider=rag.llm.provider)
    
    @router.post("/meal-plan", response_model=AIResponse)
    async def suggest_meal_plan(request: MealPlanRequest):
        result = await rag.suggest_meal_plan(
            pantry=request.pantry,
            dietary_preferences=request.dietary_preferences,
            days=request.days,
            meals_per_day=request.meals_per_day,
        )
        return AIResponse(response=result, provider=rag.llm.provider)
    
    @router.get("/cooking-tips", response_model=AIResponse)
    async def cooking_tips(
        recipe: str = Query(..., description="Recipe title"),
        skill_level: str = Query("intermediate", description="beginner|intermediate|advanced"),
    ):
        result = await rag.cooking_tips(recipe_title=recipe, skill_level=skill_level)
        return AIResponse(response=result, provider=rag.llm.provider)
    
    return router
