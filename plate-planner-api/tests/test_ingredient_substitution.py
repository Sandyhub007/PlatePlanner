"""
Tests for Ingredient Substitution features.

Covers:
  - GET  /substitute — single-ingredient Neo4j substitute lookup
  - POST /recipes/{recipe_title}/substitutions — pantry-aware substitution
  - get_pantry_substitutions() service function
  - _fuzzy_match() helper
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.services.substitution_service import get_pantry_substitutions, _fuzzy_match


client = TestClient(app)


# ── _fuzzy_match unit tests ──────────────────────────────────────────────────

class TestFuzzyMatch:
    def test_exact_match(self):
        assert _fuzzy_match({"chicken"}, "chicken") is True

    def test_case_insensitive_match(self):
        assert _fuzzy_match({"Chicken"}, "CHICKEN") is True

    def test_pantry_item_contained_in_ingredient(self):
        """'chicken' in pantry should match 'chicken breast'."""
        assert _fuzzy_match({"chicken"}, "chicken breast") is True

    def test_plural_match(self):
        """'egg' in pantry should match 'eggs'."""
        assert _fuzzy_match({"egg"}, "eggs") is True

    def test_no_match(self):
        assert _fuzzy_match({"butter"}, "olive oil") is False

    def test_partial_word_does_not_match(self):
        """'corn' should NOT match 'popcorn'."""
        assert _fuzzy_match({"corn"}, "popcorn") is False

    def test_empty_pantry(self):
        assert _fuzzy_match(set(), "garlic") is False

    def test_empty_ingredient(self):
        assert _fuzzy_match({"garlic"}, "") is False

    def test_multiple_pantry_items_any_match(self):
        """Match if any pantry item matches."""
        assert _fuzzy_match({"onion", "garlic", "tomato"}, "garlic powder") is True

    def test_no_partial_substring_match(self):
        """'rice' should NOT match 'licorice'."""
        assert _fuzzy_match({"rice"}, "licorice") is False


# ── get_pantry_substitutions service unit tests ──────────────────────────────

class TestGetPantrySubstitutions:
    """Unit tests for substitution_service.get_pantry_substitutions()."""

    def _run(self, recipe_ingredients: list[str], pantry: list[str]) -> dict:
        """Helper: run with Neo4j disabled (no real DB needed)."""
        with patch(
            "src.services.substitution_service._is_neo4j_available",
            return_value=False,
        ):
            return get_pantry_substitutions(recipe_ingredients, pantry)

    def test_all_have_when_pantry_covers_recipe(self):
        result = self._run(["garlic", "onion", "olive oil"], ["garlic", "onion", "olive oil"])
        assert result["have_count"] == 3
        assert result["missing_count"] == 0
        assert result["coverage"] == 1.0

    def test_all_missing_when_pantry_empty(self):
        result = self._run(["garlic", "onion"], [])
        assert result["have_count"] == 0
        assert result["missing_count"] == 2
        assert result["coverage"] == 0.0

    def test_partial_coverage(self):
        result = self._run(["garlic", "onion", "cream"], ["garlic"])
        assert result["have_count"] == 1
        assert result["missing_count"] == 2
        assert abs(result["coverage"] - 1 / 3) < 0.01

    def test_coverage_is_between_0_and_1(self):
        result = self._run(["pasta", "tomato", "basil"], ["tomato"])
        assert 0.0 <= result["coverage"] <= 1.0

    def test_have_list_contains_matched_ingredients(self):
        result = self._run(["garlic", "onion", "cream"], ["garlic", "onion"])
        have_names = [h["ingredient"] for h in result["have"]]
        assert "garlic" in have_names
        assert "onion" in have_names

    def test_missing_list_contains_unmatched_ingredients(self):
        result = self._run(["garlic", "saffron"], ["garlic"])
        missing_names = [m["ingredient"] for m in result["missing"]]
        assert "saffron" in missing_names

    def test_missing_entry_has_required_keys(self):
        result = self._run(["truffle"], [])
        entry = result["missing"][0]
        assert "ingredient" in entry
        assert "pantry_substitutes" in entry
        assert "other_substitutes" in entry

    def test_have_entry_has_required_keys(self):
        result = self._run(["garlic"], ["garlic"])
        entry = result["have"][0]
        assert "ingredient" in entry
        assert "matched_as" in entry

    def test_total_ingredients_correct(self):
        ingredients = ["a", "b", "c", "d"]
        result = self._run(ingredients, [])
        assert result["total_ingredients"] == 4

    def test_plural_pantry_matches_ingredient(self):
        """'eggs' in pantry should cover 'egg' in recipe."""
        result = self._run(["egg", "flour"], ["eggs"])
        assert result["have_count"] >= 1

    def test_empty_recipe_returns_zero_totals(self):
        result = self._run([], ["garlic", "onion"])
        assert result["total_ingredients"] == 0
        assert result["have_count"] == 0
        assert result["coverage"] == 0.0

    def test_no_neo4j_substitutes_returned_when_offline(self):
        """When Neo4j is offline, substitute lists should be empty."""
        result = self._run(["saffron"], [])
        entry = result["missing"][0]
        assert entry["pantry_substitutes"] == []
        assert entry["other_substitutes"] == []

    def test_neo4j_substitutes_split_into_pantry_and_other(self):
        """When Neo4j returns substitutes, they should be split by pantry membership."""
        subs = [
            {"name": "fish sauce", "score": 0.82, "source": "direct"},   # in pantry
            {"name": "tamari", "score": 0.91, "source": "direct"},       # not in pantry
        ]
        with patch("src.services.substitution_service._is_neo4j_available", return_value=True), \
             patch("src.services.substitution_service._get_neo4j_driver") as mock_driver:
            mock_session = MagicMock()
            mock_session.__enter__ = lambda s: s
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.execute_read.return_value = subs
            mock_driver.return_value.session.return_value = mock_session

            result = get_pantry_substitutions(["soy sauce"], ["fish sauce"])

        missing = result["missing"][0]
        pantry_sub_names = [s["name"] for s in missing["pantry_substitutes"]]
        other_sub_names = [s["name"] for s in missing["other_substitutes"]]
        assert "fish sauce" in pantry_sub_names
        assert "tamari" in other_sub_names


# ── GET /substitute endpoint ─────────────────────────────────────────────────

class TestSubstituteEndpoint:
    def _call(self, ingredient: str, **kwargs) -> MagicMock:
        params = f"?ingredient={ingredient}"
        for k, v in kwargs.items():
            params += f"&{k}={v}"
        return client.get(f"/substitute{params}")

    def test_returns_200_with_mock_substitutes(self):
        mock_subs = [{"name": "margarine", "score": 0.85, "context": None, "source": "direct"}]
        with patch("src.api.app.get_hybrid_substitutes", return_value=mock_subs):
            response = self._call("butter")
        assert response.status_code == 200

    def test_response_has_ingredient_field(self):
        with patch("src.api.app.get_hybrid_substitutes", return_value=[]):
            response = self._call("butter")
        assert response.json()["ingredient"] == "butter"

    def test_response_has_substitutes_list(self):
        mock_subs = [{"name": "oleo", "score": 0.83, "context": "baking", "source": "direct"}]
        with patch("src.api.app.get_hybrid_substitutes", return_value=mock_subs):
            response = self._call("butter")
        data = response.json()
        assert "substitutes" in data
        assert isinstance(data["substitutes"], list)

    def test_substitute_item_has_required_fields(self):
        mock_subs = [{"name": "margarine", "score": 0.85, "context": None, "source": "direct"}]
        with patch("src.api.app.get_hybrid_substitutes", return_value=mock_subs):
            response = self._call("butter")
        sub = response.json()["substitutes"][0]
        assert "name" in sub
        assert "score" in sub
        assert "source" in sub

    def test_empty_substitutes_list_is_valid(self):
        with patch("src.api.app.get_hybrid_substitutes", return_value=[]):
            response = self._call("obscure_ingredient_xyz")
        assert response.status_code == 200
        assert response.json()["substitutes"] == []

    def test_context_is_passed_through(self):
        with patch("src.api.app.get_hybrid_substitutes", return_value=[]) as mock_fn:
            self._call("butter", context="baking")
        mock_fn.assert_called_once_with("butter", "baking", 5, use_hybrid=False)

    def test_hybrid_flag_is_passed_through(self):
        with patch("src.api.app.get_hybrid_substitutes", return_value=[]) as mock_fn:
            self._call("butter", hybrid=True)
        mock_fn.assert_called_once_with("butter", None, 5, use_hybrid=True)

    def test_top_k_is_passed_through(self):
        with patch("src.api.app.get_hybrid_substitutes", return_value=[]) as mock_fn:
            self._call("butter", top_k=10)
        mock_fn.assert_called_once_with("butter", None, 10, use_hybrid=False)

    def test_neo4j_failure_returns_500(self):
        with patch("src.api.app.get_hybrid_substitutes", side_effect=RuntimeError("Neo4j down")):
            response = self._call("butter")
        assert response.status_code == 500

    def test_missing_ingredient_param_returns_422(self):
        response = client.get("/substitute")
        assert response.status_code == 422


# ── POST /recipes/{recipe_title}/substitutions ──────────────────────────────

class TestRecipeSubstitutionsEndpoint:
    def _call(self, title: str, pantry: list[str], sqlite_record=None, neo4j_record=None):
        with patch("src.api.app._get_recipe_from_sqlite", return_value=sqlite_record), \
             patch("src.api.app.fetch_recipe_details", return_value=neo4j_record), \
             patch(
                 "src.api.app.get_pantry_substitutions",
                 return_value={
                     "have": [{"ingredient": "garlic", "matched_as": "garlic"}],
                     "missing": [{"ingredient": "saffron", "pantry_substitutes": [], "other_substitutes": []}],
                     "total_ingredients": 2,
                     "have_count": 1,
                     "missing_count": 1,
                     "coverage": 0.5,
                 },
             ):
            return client.post(
                f"/recipes/{title}/substitutions",
                json={"pantry": pantry},
            )

    def test_returns_200_for_known_recipe(self):
        sqlite_record = {
            "title": "Garlic Rice",
            "ingredients": ["garlic", "rice"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        response = self._call("Garlic Rice", ["garlic"], sqlite_record=sqlite_record)
        assert response.status_code == 200

    def test_response_contains_recipe_title(self):
        sqlite_record = {
            "title": "Garlic Rice",
            "ingredients": ["garlic", "saffron"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        response = self._call("Garlic Rice", ["garlic"], sqlite_record=sqlite_record)
        assert response.json()["recipe_title"] == "Garlic Rice"

    def test_response_has_coverage_field(self):
        sqlite_record = {
            "title": "Rice Pilaf",
            "ingredients": ["rice", "onion"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        response = self._call("Rice Pilaf", ["rice"], sqlite_record=sqlite_record)
        data = response.json()
        assert "coverage" in data
        assert 0.0 <= data["coverage"] <= 1.0

    def test_response_has_have_and_missing_lists(self):
        sqlite_record = {
            "title": "Pasta",
            "ingredients": ["pasta", "truffle"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        response = self._call("Pasta", ["pasta"], sqlite_record=sqlite_record)
        data = response.json()
        assert "have" in data
        assert "missing" in data

    def test_returns_404_for_unknown_recipe(self):
        with patch("src.api.app._get_recipe_from_sqlite", return_value=None), \
             patch("src.api.app.fetch_recipe_details", return_value=None):
            response = client.post(
                "/recipes/nonexistent_xyz_123/substitutions",
                json={"pantry": ["garlic"]},
            )
        assert response.status_code == 404

    def test_missing_pantry_field_returns_422(self):
        with patch("src.api.app._get_recipe_from_sqlite", return_value=None), \
             patch("src.api.app.fetch_recipe_details", return_value=None):
            response = client.post("/recipes/Some Recipe/substitutions", json={})
        assert response.status_code == 422

    def test_empty_pantry_gives_full_missing(self):
        sqlite_record = {
            "title": "Spicy Curry",
            "ingredients": ["curry paste", "coconut milk", "chicken"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=sqlite_record), \
             patch("src.api.app.fetch_recipe_details", return_value=None), \
             patch(
                 "src.api.app.get_pantry_substitutions",
                 return_value={
                     "have": [],
                     "missing": [
                         {"ingredient": "curry paste", "pantry_substitutes": [], "other_substitutes": []},
                         {"ingredient": "coconut milk", "pantry_substitutes": [], "other_substitutes": []},
                         {"ingredient": "chicken", "pantry_substitutes": [], "other_substitutes": []},
                     ],
                     "total_ingredients": 3,
                     "have_count": 0,
                     "missing_count": 3,
                     "coverage": 0.0,
                 },
             ):
            response = client.post(
                "/recipes/Spicy Curry/substitutions",
                json={"pantry": []},
            )
        data = response.json()
        assert data["coverage"] == 0.0
        assert data["missing_count"] == 3

    def test_full_pantry_gives_full_coverage(self):
        sqlite_record = {
            "title": "Simple Omelette",
            "ingredients": ["egg", "butter", "salt"],
            "directions": [],
            "link": "",
            "source": "test",
        }
        with patch("src.api.app._get_recipe_from_sqlite", return_value=sqlite_record), \
             patch("src.api.app.fetch_recipe_details", return_value=None), \
             patch(
                 "src.api.app.get_pantry_substitutions",
                 return_value={
                     "have": [
                         {"ingredient": "egg", "matched_as": "egg"},
                         {"ingredient": "butter", "matched_as": "butter"},
                         {"ingredient": "salt", "matched_as": "salt"},
                     ],
                     "missing": [],
                     "total_ingredients": 3,
                     "have_count": 3,
                     "missing_count": 0,
                     "coverage": 1.0,
                 },
             ):
            response = client.post(
                "/recipes/Simple Omelette/substitutions",
                json={"pantry": ["egg", "butter", "salt"]},
            )
        data = response.json()
        assert data["coverage"] == 1.0
        assert data["have_count"] == 3
        assert data["missing_count"] == 0


# ── Co-occurrence score clamping ─────────────────────────────────────────

class TestCooccurrenceScoreClamping:
    """
    Verify that co-occurrence scores are clamped to max 1.0 via
    min(count/50, 1.0) in hybrid_substitution.get_cooccurrence_subs.
    """

    def test_high_count_clamped_to_one(self):
        """A co-occurrence count of 100 should yield score = 1.0, not 2.0."""
        from unittest.mock import MagicMock

        # Build a mock transaction that returns a high count
        mock_result = [MagicMock()]
        mock_result[0].__getitem__ = lambda s, k: {"substitute": "olive oil", "score": 100}[k]
        mock_result[0].get = lambda k, default=None: {"substitute": "olive oil", "score": 100}.get(k, default)

        # Import the function directly
        try:
            from src.evaluation.hybrid_substitution import get_cooccurrence_subs
        except Exception:
            pytest.skip("hybrid_substitution module not importable (missing neo4j/spacy)")
            return

        # We need to mock the tx.run call
        mock_tx = MagicMock()
        mock_tx.run.return_value = [{"substitute": "olive oil", "score": 100}]

        subs = get_cooccurrence_subs(mock_tx, "butter", top_k=5)

        # All scores should be <= 1.0
        for sub in subs:
            assert sub["score"] <= 1.0, f"Score {sub['score']} exceeds 1.0"

    def test_low_count_not_clamped(self):
        """A co-occurrence count of 25 should yield score = 0.5."""
        try:
            from src.evaluation.hybrid_substitution import get_cooccurrence_subs
        except Exception:
            pytest.skip("hybrid_substitution module not importable")
            return

        mock_tx = MagicMock()
        mock_tx.run.return_value = [{"substitute": "margarine", "score": 25}]

        subs = get_cooccurrence_subs(mock_tx, "butter", top_k=5)

        assert len(subs) == 1
        assert abs(subs[0]["score"] - 0.5) < 0.01

    def test_zero_count_yields_zero_score(self):
        """A co-occurrence count of 0 should yield score = 0.0."""
        try:
            from src.evaluation.hybrid_substitution import get_cooccurrence_subs
        except Exception:
            pytest.skip("hybrid_substitution module not importable")
            return

        mock_tx = MagicMock()
        mock_tx.run.return_value = [{"substitute": "lard", "score": 0}]

        subs = get_cooccurrence_subs(mock_tx, "butter", top_k=5)

        assert subs[0]["score"] == 0.0


# ── Ontology word-boundary matching ──────────────────────────────────────

class TestOntologyWordBoundaryMatching:
    """
    Verify that word-boundary regex in ontology_service.filter_unsafe_recipes
    prevents false positives.

    The Cypher uses (?i).*\\bterm\\b.* so:
      - "nut" should match "nut" but NOT "nutmeg", "coconut", "butternut"
      - "egg" should match "egg" but NOT "eggplant"
    """

    def test_ontology_query_uses_word_boundary_regex(self):
        """
        The Cypher in OntologyService.filter_unsafe_recipes should use
        \\b word-boundary anchors.
        """
        try:
            from src.services.ontology_service import OntologyService
        except ImportError:
            pytest.skip("ontology_service not importable")
            return

        import inspect
        source = inspect.getsource(OntologyService.filter_unsafe_recipes)
        # Verify the query contains word-boundary regex
        assert "\\\\b" in source or "\\b" in source, \
            "Ontology filter should use word-boundary regex (\\b)"

    def test_word_boundary_regex_matches_exact_word(self):
        """\\bnut\\b should match 'nut' standalone."""
        import re
        pattern = re.compile(r'(?i).*\bnut\b.*')
        assert pattern.match("nut")
        assert pattern.match("mixed nut")
        assert pattern.match("nut butter")

    def test_word_boundary_regex_does_not_match_substrings(self):
        """\\bnut\\b should NOT match 'nutmeg', 'coconut', 'butternut'."""
        import re
        pattern = re.compile(r'(?i).*\bnut\b.*')
        assert not pattern.match("nutmeg")
        assert not pattern.match("coconut")
        assert not pattern.match("butternut squash")
        assert not pattern.match("chestnut")
        assert not pattern.match("doughnut")

    def test_egg_boundary_does_not_match_eggplant(self):
        """\\begg\\b should NOT match 'eggplant'."""
        import re
        pattern = re.compile(r'(?i).*\begg\b.*')
        assert pattern.match("egg")
        assert pattern.match("scrambled egg")
        assert not pattern.match("eggplant")

    def test_corn_boundary_does_not_match_acorn(self):
        """\\bcorn\\b should NOT match 'acorn' or 'peppercorn'."""
        import re
        pattern = re.compile(r'(?i).*\bcorn\b.*')
        assert pattern.match("corn")
        assert pattern.match("sweet corn")
        assert not pattern.match("acorn squash")
        assert not pattern.match("peppercorn")
