"""
Tests for Recipe Generation, Suggestion, and Details endpoints.

Covers:
  - POST /suggest_recipes (local FAISS, dietary filters, deduplication, ranking)
  - GET  /recipes/{recipe_title} (detail lookup with fallback)
  - _normalize_title / _is_duplicate_title helpers
  - RecipeRequest model validation
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.api.app import app, _normalize_title, _is_duplicate_title


client = TestClient(app)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_recipe_dict(
    title: str = "Test Recipe",
    combined_score: float = 0.7,
    semantic_score: float = 0.6,
    overlap_score: float = 0.5,
    ingredients: list[str] | None = None,
    source: str = "local",
    tags: dict | None = None,
) -> dict:
    return {
        "title": title,
        "ingredients": ingredients or ["tomato", "garlic"],
        "all_ingredients": ingredients or ["tomato", "garlic"],
        "directions": "Mix and cook.",
        "semantic_score": semantic_score,
        "overlap_score": overlap_score,
        "combined_score": combined_score,
        "rank": 1,
        "tags": tags or {},
        "source": source,
        "cuisine": [],
        "source_url": "",
        "image": "",
    }


# ── _normalize_title ─────────────────────────────────────────────────────────

class TestNormalizeTitle:
    def test_lowercases(self):
        assert _normalize_title("Pasta Salad") == _normalize_title("pasta salad")

    def test_strips_punctuation(self):
        assert _normalize_title("Pasta-Salad!") == _normalize_title("Pasta Salad")

    def test_word_order_invariant(self):
        """Word-order invariance via sorted tokens."""
        assert _normalize_title("Lemon Rosemary Chicken") == _normalize_title("Rosemary Chicken Lemon")

    def test_unicode_normalised(self):
        assert _normalize_title("café") == _normalize_title("cafe")

    def test_extra_whitespace_collapsed(self):
        assert _normalize_title("  pasta   salad  ") == _normalize_title("pasta salad")


# ── _is_duplicate_title ──────────────────────────────────────────────────────

class TestIsDuplicateTitle:
    def test_exact_match_is_duplicate(self):
        seen = [_normalize_title("Pasta Salad")]
        assert _is_duplicate_title("Pasta Salad", seen) is True

    def test_no_match_is_not_duplicate(self):
        seen = [_normalize_title("Pasta Salad")]
        assert _is_duplicate_title("Chicken Tikka Masala", seen) is False

    def test_punctuation_difference_is_duplicate(self):
        seen = [_normalize_title("Pasta Salad")]
        assert _is_duplicate_title("Pasta-Salad", seen) is True

    def test_high_similarity_is_duplicate(self):
        seen = [_normalize_title("Spicy Chicken Stir Fry")]
        assert _is_duplicate_title("Spicy Chicken Stir-Fry", seen) is True

    def test_empty_seen_list(self):
        assert _is_duplicate_title("Any Recipe", []) is False


# ── POST /suggest_recipes — input validation ─────────────────────────────────

class TestSuggestRecipesValidation:
    def test_empty_ingredients_list_returns_non_200(self):
        response = client.post("/suggest_recipes", json={"ingredients": []})
        # Empty ingredient list: either validation error (422) or no results (404)
        assert response.status_code in (400, 404, 422)

    def test_missing_ingredients_field_returns_422(self):
        response = client.post("/suggest_recipes", json={})
        assert response.status_code == 422

    def test_invalid_top_n_type_returns_422(self):
        response = client.post(
            "/suggest_recipes",
            json={"ingredients": ["pasta"], "top_n": "five"},
        )
        assert response.status_code == 422

    def test_rerank_weight_out_of_range_still_accepted(self):
        """rerank_weight has no Pydantic validator — just check it doesn't crash."""
        with patch("src.api.app.suggest_recipes", return_value=[_make_recipe_dict()]):
            with patch("src.api.app.spoonacular") as mock_sp:
                mock_sp.enabled = False
                response = client.post(
                    "/suggest_recipes",
                    json={"ingredients": ["pasta"], "rerank_weight": 2.0},
                )
        assert response.status_code in (200, 422)


# ── POST /suggest_recipes — local FAISS results ──────────────────────────────

class TestSuggestRecipesLocal:
    """Tests that exercise the local FAISS tier."""

    def _post(self, payload: dict, local_results: list[dict], spoonacular_enabled: bool = False):
        with patch("src.api.app.suggest_recipes", return_value=local_results) as _mock_local, \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = spoonacular_enabled
            return client.post("/suggest_recipes", json=payload)

    def test_returns_200_with_valid_ingredients(self):
        results = [_make_recipe_dict("Garlic Pasta", combined_score=0.8)]
        response = self._post({"ingredients": ["garlic", "pasta"]}, results)
        assert response.status_code == 200

    def test_response_is_list(self):
        results = [_make_recipe_dict("Garlic Pasta")]
        response = self._post({"ingredients": ["garlic"]}, results)
        assert isinstance(response.json(), list)

    def test_result_has_required_fields(self):
        results = [_make_recipe_dict("Test Recipe")]
        response = self._post({"ingredients": ["garlic"]}, results)
        data = response.json()
        assert len(data) >= 1
        item = data[0]
        assert "title" in item
        assert "ingredients" in item
        assert "combined_score" in item
        assert "rank" in item

    def test_results_sorted_by_combined_score_descending(self):
        results = [
            _make_recipe_dict("Recipe A", combined_score=0.5),
            _make_recipe_dict("Recipe B", combined_score=0.9),
            _make_recipe_dict("Recipe C", combined_score=0.7),
        ]
        response = self._post({"ingredients": ["a", "b"]}, results)
        scores = [r["combined_score"] for r in response.json()]
        assert scores == sorted(scores, reverse=True)

    def test_rank_1_is_highest_scored(self):
        results = [
            _make_recipe_dict("Low Score", combined_score=0.3),
            _make_recipe_dict("High Score", combined_score=0.9),
        ]
        response = self._post({"ingredients": ["test"]}, results)
        ranked = sorted(response.json(), key=lambda r: r["rank"])
        assert ranked[0]["combined_score"] >= ranked[-1]["combined_score"]

    def test_top_n_limits_results(self):
        results = [_make_recipe_dict(f"Recipe {i}", combined_score=0.9 - i * 0.1) for i in range(10)]
        response = self._post({"ingredients": ["test"], "top_n": 3}, results)
        assert len(response.json()) <= 3

    def test_no_results_returns_404(self):
        response = self._post({"ingredients": ["xyzsuperrareingredient99"]}, [])
        assert response.status_code == 404

    def test_source_field_is_local(self):
        results = [_make_recipe_dict("Local Recipe", source="local")]
        response = self._post({"ingredients": ["pasta"]}, results)
        assert response.json()[0]["source"] == "local"


# ── POST /suggest_recipes — dietary filters ──────────────────────────────────

class TestSuggestRecipesDietaryFilters:
    def _post_with_filter(self, dietary_flags: dict, local_results: list[dict]) -> list[dict]:
        payload = {"ingredients": ["tofu", "vegetables"], **dietary_flags}
        with patch("src.api.app.suggest_recipes", return_value=local_results), \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = False
            response = client.post("/suggest_recipes", json=payload)
        return response.json() if response.status_code == 200 else []

    def test_vegan_filter_passes_through(self):
        results = [_make_recipe_dict("Tofu Stir Fry", tags={"is_vegan": True})]
        data = self._post_with_filter({"is_vegan": True}, results)
        assert len(data) == 1

    def test_vegetarian_filter_passes_through(self):
        results = [_make_recipe_dict("Veggie Bowl", tags={"is_vegetarian": True})]
        data = self._post_with_filter({"is_vegetarian": True}, results)
        assert len(data) == 1

    def test_gluten_free_filter_passes_through(self):
        results = [_make_recipe_dict("GF Pasta", tags={"is_gluten_free": True})]
        data = self._post_with_filter({"is_gluten_free": True}, results)
        assert len(data) == 1

    def test_dairy_free_filter_passes_through(self):
        results = [_make_recipe_dict("Dairy-Free Soup", tags={"is_dairy_free": True})]
        data = self._post_with_filter({"is_dairy_free": True}, results)
        assert len(data) == 1

    def test_combined_vegan_gluten_free_filter(self):
        results = [_make_recipe_dict("Vegan GF Bowl", tags={"is_vegan": True, "is_gluten_free": True})]
        data = self._post_with_filter({"is_vegan": True, "is_gluten_free": True}, results)
        assert len(data) == 1


# ── POST /suggest_recipes — deduplication ────────────────────────────────────

class TestSuggestRecipesDeduplication:
    def test_duplicate_titles_are_removed(self):
        results = [
            _make_recipe_dict("Lemon Chicken", combined_score=0.8),
            _make_recipe_dict("Lemon-Chicken", combined_score=0.7),  # near-duplicate
            _make_recipe_dict("Pasta Bolognese", combined_score=0.6),
        ]
        with patch("src.api.app.suggest_recipes", return_value=results), \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = False
            response = client.post("/suggest_recipes", json={"ingredients": ["lemon"]})

        titles = [r["title"] for r in response.json()]
        assert "Pasta Bolognese" in titles
        # At most one of the near-duplicate "Lemon Chicken" variants
        lemon_count = sum(1 for t in titles if "Lemon" in t or "lemon" in t.lower())
        assert lemon_count <= 1

    def test_exact_duplicate_titles_are_removed(self):
        results = [
            _make_recipe_dict("Pasta Salad", combined_score=0.9),
            _make_recipe_dict("Pasta Salad", combined_score=0.8),
        ]
        with patch("src.api.app.suggest_recipes", return_value=results), \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = False
            response = client.post("/suggest_recipes", json={"ingredients": ["pasta"]})

        titles = [r["title"] for r in response.json()]
        assert titles.count("Pasta Salad") == 1


# ── GET /recipes/{recipe_title} — detail endpoint ────────────────────────────

class TestGetRecipeDetails:
    def test_returns_404_for_unknown_title(self):
        with patch("src.api.app._get_recipe_from_sqlite", return_value=None), \
             patch("src.api.app.fetch_recipe_details", return_value=None):
            response = client.get("/recipes/completely_unknown_recipe_xyz_123")
        assert response.status_code == 404

    def test_returns_recipe_from_sqlite(self):
        mock_record = {
            "title": "Spaghetti Carbonara",
            "ingredients": ["pasta", "eggs", "pancetta", "parmesan"],
            "directions": ["Boil pasta", "Mix eggs and cheese", "Combine"],
            "link": "https://example.com",
            "source": "SQLiteDB",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=mock_record):
            response = client.get("/recipes/Spaghetti Carbonara")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Spaghetti Carbonara"
        assert "pasta" in data["ingredients"]
        assert isinstance(data["directions"], list)
        assert len(data["directions"]) > 0

    def test_falls_back_to_neo4j_when_sqlite_empty(self):
        neo4j_record = {
            "title": "Thai Green Curry",
            "ingredients": ["coconut milk", "green curry paste", "chicken"],
            "directions": ["Heat paste", "Add coconut milk", "Add chicken"],
            "link": "https://example.com",
            "source": "Neo4j",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=None), \
             patch("src.api.app.fetch_recipe_details", return_value=neo4j_record):
            response = client.get("/recipes/Thai Green Curry")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Thai Green Curry"

    def test_response_has_required_fields(self):
        mock_record = {
            "title": "Simple Salad",
            "ingredients": ["lettuce", "tomato", "olive oil"],
            "directions": ["Combine all ingredients"],
            "link": "",
            "source": "test",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=mock_record):
            response = client.get("/recipes/Simple Salad")

        assert response.status_code == 200
        data = response.json()
        for field in ("title", "directions", "link", "source", "ingredients"):
            assert field in data

    def test_directions_are_list(self):
        mock_record = {
            "title": "Omelette",
            "ingredients": ["egg", "butter", "salt"],
            "directions": ["Beat eggs", "Cook in butter"],
            "link": "",
            "source": "test",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=mock_record):
            response = client.get("/recipes/Omelette")

        assert isinstance(response.json()["directions"], list)

    def test_ingredient_deduplication(self):
        """Duplicate ingredients should appear only once in response."""
        mock_record = {
            "title": "Duplicate Test",
            "ingredients": ["garlic", "garlic", "onion", "onion", "tomato"],
            "directions": ["Cook everything"],
            "link": "",
            "source": "test",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=mock_record):
            response = client.get("/recipes/Duplicate Test")

        ingredients = response.json()["ingredients"]
        # Should not have exact duplicates
        assert len(ingredients) == len(set(ing.lower() for ing in ingredients))


# ── POST /suggest_recipes — external source ──────────────────────────────────

class TestSuggestRecipesExternalSource:
    def test_external_result_appears_when_local_sparse(self):
        local_result = [_make_recipe_dict("Local Recipe", combined_score=0.2)]
        ext_result = [_make_recipe_dict("Spoon Recipe", combined_score=0.9, source="spoonacular")]

        async def mock_search(**kwargs):
            return ext_result

        with patch("src.api.app.suggest_recipes", return_value=local_result), \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = True
            mock_sp.search_by_ingredients = mock_search
            response = client.post(
                "/suggest_recipes",
                json={"ingredients": ["chicken"], "enable_external": True},
            )

        titles = [r["title"] for r in response.json()]
        assert "Spoon Recipe" in titles

    def test_no_external_when_disable_flag_set(self):
        local_result = [_make_recipe_dict("Local Only", combined_score=0.9)]

        with patch("src.api.app.suggest_recipes", return_value=local_result), \
             patch("src.api.app.spoonacular") as mock_sp:
            mock_sp.enabled = True
            response = client.post(
                "/suggest_recipes",
                json={"ingredients": ["chicken"], "enable_external": False},
            )

        sources = [r["source"] for r in response.json()]
        assert all(s == "local" for s in sources)


# ── Health check ─────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_message(self):
        response = client.get("/")
        assert "message" in response.json()
