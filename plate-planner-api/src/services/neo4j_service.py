from neo4j import GraphDatabase

from src.config.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.evaluation.hybrid_substitution import (
    get_direct_subs,
    get_hybrid_subs,
    normalize_ingredient,
)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


class Neo4jService:
    """Lightweight Neo4j wrapper used by service layer."""

    def __init__(self):
        self._driver = driver

    def execute_query(self, query: str, params: dict | None = None):
        """Run a Cypher query and return list of dict rows."""
        def _run(tx):
            result = tx.run(query, **(params or {}))
            return [record.data() for record in result]

        with self._driver.session() as session:
            return session.execute_read(_run)

    def close(self):
        """Close the shared driver."""
        try:
            self._driver.close()
        except Exception:
            pass

def get_hybrid_substitutes(
    ingredient: str,
    context: str | None = None,
    top_k: int = 5,
    alpha: float = 0.9,
    use_hybrid: bool = True
):
    norm_ing = normalize_ingredient(ingredient)

    with driver.session() as session:
        if use_hybrid:
            return session.execute_read(get_hybrid_subs, norm_ing, context, top_k, alpha)
        else:
            return session.execute_read(_direct_only, norm_ing, context, top_k)

# Helper: direct-only fallback
def _direct_only(tx, ingredient, context=None, top_k=5):
    direct, _ = get_direct_subs(tx, ingredient, context, top_k)
    return sorted(direct, key=lambda x: -x["score"])[:top_k]


def recipe_details(title: str):
    def _fetch_recipe(tx, title):
        result = tx.run("""
            MATCH (r:Recipe)
            WHERE toLower(r.title) = toLower($title)
            OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
            RETURN r.title AS title,
                   r.directions AS directions,
                   r.link AS link,
                   r.source AS source,
                   collect(i.name) AS ingredients
        """, title=title)
        return result.single()

    with driver.session() as session:
        return session.execute_read(_fetch_recipe, title)

def get_random_recipes(limit: int = 50):
    """Fetch a random set of recipes."""
    def _fetch_random(tx, limit):
        result = tx.run("""
            MATCH (r:Recipe)
            WITH r, rand() AS rnd
            ORDER BY rand()
            LIMIT $limit
            OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
            RETURN r.recipe_id AS id,
                   r.title AS title,
                   collect(i.name) AS ingredients
        """, limit=limit)
        return [record.data() for record in result]

    with driver.session() as session:
        return session.execute_read(_fetch_random, limit)


def get_recipe_ingredients_by_id(recipe_id: str):
    """Fetch ingredients for a recipe by recipe_id from Neo4j."""
    def _fetch_ingredients(tx, recipe_id):
        try:
            # Try to parse as int first (common case)
            recipe_id_int = int(recipe_id)
            result = tx.run("""
                MATCH (r:Recipe {recipe_id: $recipe_id})
                OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
                RETURN collect(i.name) AS ingredients
            """, recipe_id=recipe_id_int)
        except ValueError:
            # If not an int, try as string match on title
            result = tx.run("""
                MATCH (r:Recipe)
                WHERE r.recipe_id = $recipe_id OR toLower(r.title) = toLower($recipe_id)
                OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
                RETURN collect(i.name) AS ingredients
            """, recipe_id=recipe_id)
        
        record = result.single()
        if record and record.get("ingredients"):
            # Filter out None values
            return [ing for ing in record["ingredients"] if ing]
        return []

    with driver.session() as session:
        return session.execute_read(_fetch_ingredients, recipe_id)
