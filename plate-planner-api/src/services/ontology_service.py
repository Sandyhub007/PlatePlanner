from src.services.neo4j_service import Neo4jService
from typing import List, Dict

class OntologyService:
    """
    Stage 2: Ontology Reasoning (Filtering)
    Acts as a strict, deterministic filter querying the Neo4j Graph DB 
    to remove any candidate recipes containing restricted constraints (allergies, diets).
    """
    def __init__(self):
        # Instantiate the shared neo4j service wrapper
        self.neo4j = Neo4jService()

    def filter_unsafe_recipes(self, candidates: List[Dict], restrictions: List[str]) -> List[Dict]:
        """
        Takes a raw list of candidate recipe dictionaries and a list of restricted string terms.
        Queries Neo4j to verify each recipe against its relationships in the graph.
        Returns solely the candidate dictionaries that passed the strict deterministic filter.
        
        Args:
            candidates: List of dictionaries (from retrieval_service, must contain 'recipe_id')
            restrictions: List of restricted ingredient substrings (e.g., ["peanut", "dairy", "meat"])
        """
        if not candidates:
            return []
        
        if not restrictions:
            # No hard restrictions means all candidates pass
            return candidates

        # Extract IDs from the candidates.
        candidate_ids = [c["recipe_id"] for c in candidates if "recipe_id" in c]
        if not candidate_ids:
            return candidates
        
        # Lowercase restrictions for case-insensitive matching in Cypher
        restricted_terms = [r.lower().strip() for r in restrictions]

        # Cypher Query:
        # Pass the list of candidate IDs and the list of restricted terms.
        # Check all :HAS_INGREDIENT relationships. If ANY related ingredient's name 
        # contains ANY of the restricted terms, drop the recipe.
        query = """
            UNWIND $recipe_ids AS rid
            
            // Handle possibility of recipe_id being int or string
            MATCH (r:Recipe)
            WHERE r.recipe_id = toInteger(rid) OR r.recipe_id = toString(rid)
            
            OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
            WITH r, collect(toLower(i.name)) AS ingredients
            
            // Check if ANY of the recipe's ingredients contain ANY of the restricted terms
            WHERE NOT any(
                ing IN ingredients WHERE any(
                    term IN $restricted_terms WHERE ing CONTAINS term
                )
            )
            
            // Return IDs of recipes that are SAFE
            RETURN r.recipe_id AS safe_id
        """

        params = {
            "recipe_ids": candidate_ids,
            "restricted_terms": restricted_terms
        }

        try:
            results = self.neo4j.execute_query(query, params)
        except Exception as e:
            print(f"❌ [OntologyService] Neo4j Query Failed: {e}")
            # Fail-safe: if Graph DB is down, we should NOT assume safe. 
            # In a strict health system, failure = drop.
            return []

        # Convert result rows into a set of safe IDs 
        safe_ids = set()
        for row in results:
            safe_id = row.get("safe_id")
            if safe_id is not None:
                # Store as string for universal matching since dict IDs might be dynamic
                safe_ids.add(str(safe_id))

        # Filter the original candidate list preserving metadata and scores
        safe_candidates = [
            c for c in candidates 
            if "recipe_id" in c and str(c["recipe_id"]) in safe_ids
        ]

        print(f"🛡️ [OntologyService] Filtered {len(candidates)} candidates down to {len(safe_candidates)} safe recipes.")
        return safe_candidates

# Singleton instance
ontology_service = OntologyService()
