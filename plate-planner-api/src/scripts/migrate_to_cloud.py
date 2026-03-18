#!/usr/bin/env python3
"""
migrate_to_cloud.py -- One-shot migration helper for PlatePlanner.

Creates all PostgreSQL tables on the cloud Neon instance and prints
instructions for migrating Neo4j data to AuraDB.

Usage:
  # Set cloud env vars first (or use a .env with cloud values)
  export DATABASE_URL="postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/plateplanner?sslmode=require"
  export NEO4J_URI="neo4j+s://xxxxxxxx.databases.neo4j.io"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="your-auradb-password"

  python -m src.scripts.migrate_to_cloud
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrate_to_cloud")


# ---------------------------------------------------------------------------
# 1. PostgreSQL / Neon -- create all tables
# ---------------------------------------------------------------------------

def migrate_postgres() -> bool:
    """Connect to Neon Postgres and create all SQLAlchemy tables.

    Returns True on success, False on failure.
    """
    from src.database.cloud_config import DATABASE_URL, IS_CLOUD_POSTGRES
    from src.database.session import engine, Base

    # Import all models so Base.metadata knows about them
    import src.database.models  # noqa: F401

    logger.info("=" * 60)
    logger.info("POSTGRES MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Target URL: {_redact_url(DATABASE_URL)}")
    logger.info(f"Cloud mode: {IS_CLOUD_POSTGRES}")

    try:
        # Create all tables from SQLAlchemy metadata
        logger.info("Creating tables from SQLAlchemy metadata...")
        Base.metadata.create_all(bind=engine)
        logger.info("Base tables created successfully.")

        # Run the idempotent schema guards for any ALTER/CREATE statements
        # that are not covered by the ORM model definitions.
        from src.database.schema_guards import (
            ensure_phase_two_schema,
            ensure_phase_three_schema,
            ensure_pantry_schema,
            ensure_meal_log_schema,
            ensure_onboarding_schema,
            ensure_admin_schema,
        )

        logger.info("Running schema guards (idempotent ALTER/CREATE)...")
        ensure_phase_two_schema()
        ensure_phase_three_schema()
        ensure_pantry_schema()
        ensure_meal_log_schema()
        ensure_onboarding_schema()
        ensure_admin_schema()
        logger.info("Schema guards completed.")

        # Quick verification - list tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables present in database ({len(tables)}): {', '.join(sorted(tables))}")
        return True

    except Exception:
        logger.exception("Failed to create Postgres tables")
        return False


# ---------------------------------------------------------------------------
# 2. Neo4j / AuraDB -- verify connectivity + print migration guide
# ---------------------------------------------------------------------------

def verify_neo4j() -> bool:
    """Verify the Neo4j/AuraDB connection and print data migration guide.

    Returns True if connection succeeds, False otherwise.
    """
    from src.database.cloud_config import (
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD,
        NEO4J_DRIVER_KWARGS,
        IS_CLOUD_NEO4J,
    )
    from neo4j import GraphDatabase

    logger.info("")
    logger.info("=" * 60)
    logger.info("NEO4J / AURADB VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Target URI: {NEO4J_URI}")
    logger.info(f"Cloud mode: {IS_CLOUD_NEO4J}")

    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            **NEO4J_DRIVER_KWARGS,
        )
        with driver.session() as session:
            result = session.run("RETURN 1 AS ping")
            record = result.single()
            if record and record["ping"] == 1:
                logger.info("Neo4j connectivity: OK")

            # Check existing node/relationship counts
            counts = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt "
                "ORDER BY cnt DESC LIMIT 10"
            )
            logger.info("Node counts:")
            for rec in counts:
                logger.info(f"  :{rec['label']} -> {rec['cnt']}")

        driver.close()
        return True

    except Exception:
        logger.exception("Failed to connect to Neo4j")
        return False


def print_neo4j_migration_guide():
    """Print step-by-step instructions for migrating Neo4j data to AuraDB."""
    guide = """
================================================================================
  NEO4J DATA MIGRATION GUIDE: Local Docker -> AuraDB
================================================================================

There are TWO recommended approaches for migrating Neo4j data to AuraDB:

────────────────────────────────────────────────────────────────────────────────
  OPTION A: Re-run the bootstrap scripts against AuraDB  (RECOMMENDED)
────────────────────────────────────────────────────────────────────────────────

Since PlatePlanner has idempotent graph bootstrap scripts, the simplest
approach is to re-run them pointing at AuraDB:

  1. Update your .env file with AuraDB credentials:

     NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=<your-auradb-password>

  2. Run the bootstrap pipeline:

     cd plate-planner-api
     python -m src.database.bootstrap_graph

     This will execute:
       - load_into_neo4j.main()          # Ingredients, Recipes, HAS_INGREDIENT
       - add_edges_from_csv.main()        # SUBSTITUTES_WITH edges
       - build_similar_to_edges.main()    # SIMILAR_TO edges (Word2Vec)
       - explore_util.main()              # Verification summary

  NOTE: AuraDB free tier has a 200K node limit. If your dataset exceeds
  this, consider AuraDB Professional or filter the CSV data first.

────────────────────────────────────────────────────────────────────────────────
  OPTION B: Export with APOC and import via Cypher  (for large/custom data)
────────────────────────────────────────────────────────────────────────────────

  1. EXPORT from local Neo4j (Docker must be running):

     # Export all nodes
     docker exec neo4j cypher-shell -u neo4j -p 12345678 \\
       "CALL apoc.export.json.all('/export/full_export.json', {useTypes: true})"

     # Copy from container
     docker cp neo4j:/var/lib/neo4j/export/full_export.json ./neo4j_export.json

  2. IMPORT into AuraDB:

     AuraDB does NOT support APOC import, so you need to convert the JSON
     export into Cypher statements. Use the neo4j-admin tool or a script:

     # Install neo4j Python driver locally
     pip install neo4j

     # Run a custom import script that reads the JSON and executes
     # batched Cypher MERGE statements against AuraDB.

     Example pseudo-code:

       import json
       from neo4j import GraphDatabase

       driver = GraphDatabase.driver(
           "neo4j+s://<your-instance>.databases.neo4j.io",
           auth=("neo4j", "<password>")
       )

       with open("neo4j_export.json") as f:
           data = json.load(f)

       with driver.session() as session:
           # Create constraints first
           session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.name IS UNIQUE")
           session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE")

           # Batch insert nodes
           for node in data["nodes"]:
               if "Ingredient" in node["labels"]:
                   session.run("MERGE (i:Ingredient {name: $name})", name=node["properties"]["name"])
               elif "Recipe" in node["labels"]:
                   session.run("MERGE (r:Recipe {recipe_id: $id, title: $title})",
                               id=node["properties"]["recipe_id"],
                               title=node["properties"]["title"])

           # Batch insert relationships
           for rel in data["relationships"]:
               # Use appropriate MERGE based on rel["type"]
               ...

       driver.close()

────────────────────────────────────────────────────────────────────────────────
  OPTION C: Use neo4j-admin dump/load  (AuraDB Professional only)
────────────────────────────────────────────────────────────────────────────────

  AuraDB Professional supports importing .dump files:

  1. Stop local Neo4j, then create a dump:
     neo4j-admin database dump neo4j --to-path=/path/to/dump/

  2. Upload via the AuraDB console:
     AuraDB Console -> your instance -> Import Database -> upload .dump file

  NOTE: This is NOT available on AuraDB Free tier.

================================================================================
"""
    print(guide)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _redact_url(url: str) -> str:
    """Redact password from a database URL for safe logging."""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.password:
        redacted = parsed._replace(
            netloc=f"{parsed.username}:***@{parsed.hostname}"
            + (f":{parsed.port}" if parsed.port else "")
        )
        return urlunparse(redacted)
    return url


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("PlatePlanner Cloud Migration Script")
    logger.info("=" * 60)

    # Step 1: Postgres
    pg_ok = migrate_postgres()

    # Step 2: Neo4j
    neo_ok = verify_neo4j()

    # Step 3: Print Neo4j migration guide
    print_neo4j_migration_guide()

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Postgres tables created: {'YES' if pg_ok else 'FAILED'}")
    logger.info(f"Neo4j connectivity:      {'OK' if neo_ok else 'FAILED'}")

    if pg_ok and neo_ok:
        logger.info("")
        logger.info("Both databases are reachable. Next steps:")
        logger.info("  1. If this is a fresh deployment, run the Neo4j bootstrap:")
        logger.info("       python -m src.database.bootstrap_graph")
        logger.info("  2. Update your deployment platform env vars to use cloud URLs")
        logger.info("  3. Deploy and verify the /health endpoint")
    elif not pg_ok:
        logger.error("Postgres migration failed. Check DATABASE_URL and network access.")
        sys.exit(1)
    elif not neo_ok:
        logger.warning(
            "Neo4j connection failed. The app will still work for Postgres-backed "
            "features (auth, meal plans, shopping lists). Graph features (substitutions, "
            "recipe search) require Neo4j."
        )


if __name__ == "__main__":
    main()
