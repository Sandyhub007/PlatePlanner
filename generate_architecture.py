#!/usr/bin/env python3
"""Generate PlatePlanner Architecture Diagram."""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.framework import React, FastAPI
from diagrams.onprem.database import PostgreSQL, Neo4J
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.mlops import Mlflow
from diagrams.programming.language import Python
from diagrams.onprem.client import User
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.onprem.container import Docker
from diagrams.saas.cdn import Cloudflare
from diagrams.generic.device import Mobile

graph_attr = {
    "fontsize": "20",
    "fontname": "Helvetica",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "spline",
    "nodesep": "0.8",
    "ranksep": "1.2",
    "dpi": "200",
}

node_attr = {
    "fontsize": "12",
    "fontname": "Helvetica",
}

edge_attr = {
    "fontsize": "10",
    "fontname": "Helvetica",
}

with Diagram(
    "Plate Planner - System Architecture",
    filename="/Users/sandilyachimalamarri/Plateplanner/architecture_diagram",
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    user = Mobile("Mobile App\nUser")

    with Cluster("Client Tier", graph_attr={"bgcolor": "#E8F5E9", "fontsize": "16", "style": "rounded"}):
        mobile = React("React Native\n+ Expo 54")
        gluestack = Rack("Gluestack UI\nNativeWind")
        expo_router = Rack("Expo Router\nNavigation")

    with Cluster("API Tier (FastAPI + Uvicorn)", graph_attr={"bgcolor": "#E3F2FD", "fontsize": "16", "style": "rounded"}):
        with Cluster("Routers"):
            auth = Python("Auth\nRouter")
            meals = Python("Meal Plan\nRouter")
            shop = Python("Shopping\nList Router")
            rec = Python("Recommend\nRouter")
            nutr = Python("Nutrition\nRouter")
            sub = Python("Substitution\nRouter")
            pantry = Python("Pantry\nRouter")

        with Cluster("Middleware"):
            jwt = Rack("JWT Auth\nMiddleware")
            cors = Rack("CORS\nMiddleware")
            pydantic = Rack("Pydantic\nValidation")

    with Cluster("Service Tier (Business Logic)", graph_attr={"bgcolor": "#FFF3E0", "fontsize": "16", "style": "rounded"}):
        meal_svc = Python("MealPlan\nService")
        shop_svc = Python("ShoppingList\nService\n(730+ lines)")
        rec_svc = Python("Recommendation\nService")
        sub_svc = Python("Substitution\nService")
        nutr_svc = Python("Nutrition\nService")

    with Cluster("ML Inference Layer", graph_attr={"bgcolor": "#F3E5F5", "fontsize": "16", "style": "rounded"}):
        faiss = Storage("FAISS\nIVF-PQ Index")
        transformer = Mlflow("SentenceTransformer\nall-MiniLM-L6-v2")
        spacy = Mlflow("SpaCy NER\nen_core_web_sm")
        fuzzy = Rack("thefuzz\nFuzzy Matching")

    with Cluster("Data Persistence Tier", graph_attr={"bgcolor": "#FFEBEE", "fontsize": "16", "style": "rounded"}):
        pg = PostgreSQL("PostgreSQL 15\n(Users, Plans,\nShopping Lists)")
        neo = Neo4J("Neo4j 5.x\n(Ingredient Graph,\nSubstitutions)")
        redis = Redis("Redis 7\n(Cache,\nSessions)")
        sqlite = Storage("SQLite\n(Recipe Metadata\n100K+ recipes)")

    with Cluster("Deployment (Railway)", graph_attr={"bgcolor": "#F5F5F5", "fontsize": "16", "style": "rounded"}):
        docker = Docker("Docker\nMulti-Stage")
        neon = Rack("Neon\n(Serverless PG)")
        aura = Rack("Neo4j\nAuraDB")

    # Connections
    user >> Edge(label="HTTPS/REST", color="#2E7D32", style="bold") >> mobile
    mobile >> Edge(color="#1565C0") >> gluestack
    mobile >> Edge(color="#1565C0") >> expo_router

    mobile >> Edge(label="JWT + JSON", color="#1565C0", style="bold") >> jwt
    jwt >> cors >> pydantic

    pydantic >> Edge(color="#666") >> auth
    pydantic >> Edge(color="#666") >> meals
    pydantic >> Edge(color="#666") >> shop
    pydantic >> Edge(color="#666") >> rec
    pydantic >> Edge(color="#666") >> nutr
    pydantic >> Edge(color="#666") >> sub
    pydantic >> Edge(color="#666") >> pantry

    meals >> Edge(color="#E65100") >> meal_svc
    shop >> Edge(color="#E65100") >> shop_svc
    rec >> Edge(color="#E65100") >> rec_svc
    sub >> Edge(color="#E65100") >> sub_svc
    nutr >> Edge(color="#E65100") >> nutr_svc

    rec_svc >> Edge(label="Semantic\nSearch", color="#7B1FA2") >> faiss
    rec_svc >> Edge(label="Encode\nQuery", color="#7B1FA2") >> transformer
    shop_svc >> Edge(color="#7B1FA2") >> spacy
    shop_svc >> Edge(color="#7B1FA2") >> fuzzy

    meal_svc >> Edge(color="#C62828") >> pg
    shop_svc >> Edge(color="#C62828") >> pg
    nutr_svc >> Edge(color="#C62828") >> pg
    sub_svc >> Edge(label="Cypher\nQueries", color="#C62828") >> neo
    rec_svc >> Edge(label="Dietary\nFiltering", color="#C62828") >> neo
    rec_svc >> Edge(color="#C62828") >> sqlite
    rec_svc >> Edge(color="#C62828") >> redis

    docker >> Edge(style="dashed", color="#666") >> neon
    docker >> Edge(style="dashed", color="#666") >> aura

print("Architecture diagram generated!")
