"""
Graph Neural Network (GNN) for Ingredient Substitution
=======================================================
Trains a GNN (GraphSAGE) on the ingredient knowledge graph for
directed link prediction: predicting SUBSTITUTES_WITH edges.

Architecture:
  - Input: Ingredient nodes with W2V features + graph structure
  - Model: 2-layer GraphSAGE encoder + MLP link predictor
  - Task: Directed link prediction (A substitutes B ≠ B substitutes A)
  - Training: Positive edges (SUBSTITUTES_WITH) + negative sampling

Dependencies:
  pip install torch torch-geometric networkx

Run: poetry run python -m src.pipelines.train_gnn_substitution
"""

import logging
import os
import json
from pathlib import Path
from typing import Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

W2V_MODEL_PATH = Path("src/data/models/ingredient_substitution/ingredient_w2v.model")
GNN_OUTPUT_DIR = Path("src/data/models/ingredient_substitution/gnn")
GNN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Hyperparameters
EMBEDDING_DIM = 128       # Match W2V vector_size
HIDDEN_DIM = 128          # GraphSAGE hidden dimension
OUTPUT_DIM = 64           # Final node embedding dimension
NUM_LAYERS = 2            # GraphSAGE layers (2-hop neighborhood)
DROPOUT = 0.3
LEARNING_RATE = 1e-3
EPOCHS = 100
NEG_RATIO = 3             # Negative samples per positive edge
TRAIN_SPLIT = 0.85
VAL_SPLIT = 0.05
TEST_SPLIT = 0.10


# ─── Step 1: Extract Graph from Neo4j ────────────────────────────────
def extract_graph_from_neo4j():
    """
    Extract the ingredient knowledge graph from Neo4j.
    Returns node features, edge lists, and name→index mapping.
    """
    from neo4j import GraphDatabase
    from gensim.models import Word2Vec

    logger.info("Connecting to Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # Load W2V for initial node features
    logger.info(f"Loading W2V model from {W2V_MODEL_PATH}...")
    w2v = Word2Vec.load(str(W2V_MODEL_PATH))
    w2v_dim = w2v.vector_size
    
    # Get all ingredients
    logger.info("Fetching ingredients from Neo4j...")
    with driver.session() as session:
        result = session.run("MATCH (i:Ingredient) RETURN i.name AS name")
        all_ingredients = [r["name"] for r in result]
    
    # Build name→index mapping
    name_to_idx = {name: idx for idx, name in enumerate(all_ingredients)}
    num_nodes = len(all_ingredients)
    logger.info(f"Found {num_nodes} ingredient nodes")
    
    # Build node feature matrix from W2V
    features = np.zeros((num_nodes, w2v_dim), dtype=np.float32)
    w2v_coverage = 0
    for name, idx in name_to_idx.items():
        if name in w2v.wv:
            features[idx] = w2v.wv[name]
            w2v_coverage += 1
    
    logger.info(f"W2V coverage: {w2v_coverage}/{num_nodes} ({100*w2v_coverage/num_nodes:.1f}%)")
    
    # Get edges
    logger.info("Fetching SUBSTITUTES_WITH edges...")
    sub_edges = []
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Ingredient)-[r:SUBSTITUTES_WITH]->(b:Ingredient)
            RETURN a.name AS source, b.name AS target, r.score AS score
        """)
        for r in result:
            src = name_to_idx.get(r["source"])
            tgt = name_to_idx.get(r["target"])
            if src is not None and tgt is not None:
                sub_edges.append((src, tgt, r["score"] or 1.0))
    
    logger.info(f"Found {len(sub_edges)} SUBSTITUTES_WITH edges")
    
    # Also get co-occurrence edges (HAS_INGREDIENT)
    logger.info("Fetching co-occurrence edges...")
    cooc_edges = []
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Recipe)-[:HAS_INGREDIENT]->(a:Ingredient),
                  (r)-[:HAS_INGREDIENT]->(b:Ingredient)
            WHERE a.name < b.name
            WITH a.name AS source, b.name AS target, COUNT(r) AS freq
            WHERE freq >= 5
            RETURN source, target, freq
            ORDER BY freq DESC
            LIMIT 100000
        """)
        for r in result:
            src = name_to_idx.get(r["source"])
            tgt = name_to_idx.get(r["target"])
            if src is not None and tgt is not None:
                cooc_edges.append((src, tgt, min(r["freq"] / 100.0, 1.0)))
    
    logger.info(f"Found {len(cooc_edges)} co-occurrence edges (freq≥5)")
    
    # Also get SIMILAR_TO edges
    logger.info("Fetching SIMILAR_TO edges...")
    sim_edges = []
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Ingredient)-[r:SIMILAR_TO]->(b:Ingredient)
            RETURN a.name AS source, b.name AS target, r.score AS score
        """)
        for r in result:
            src = name_to_idx.get(r["source"])
            tgt = name_to_idx.get(r["target"])
            if src is not None and tgt is not None:
                sim_edges.append((src, tgt, r["score"] or 1.0))
    
    logger.info(f"Found {len(sim_edges)} SIMILAR_TO edges")
    
    driver.close()
    
    # Save graph data
    graph_data = {
        "num_nodes": num_nodes,
        "feature_dim": w2v_dim,
        "features": features,
        "sub_edges": sub_edges,
        "cooc_edges": cooc_edges,
        "sim_edges": sim_edges,
        "name_to_idx": name_to_idx,
        "idx_to_name": {v: k for k, v in name_to_idx.items()},
    }
    
    # Save metadata
    meta = {
        "num_nodes": num_nodes,
        "feature_dim": w2v_dim,
        "num_sub_edges": len(sub_edges),
        "num_cooc_edges": len(cooc_edges),
        "num_sim_edges": len(sim_edges),
        "w2v_coverage_pct": round(100 * w2v_coverage / max(num_nodes, 1), 1),
    }
    with open(GNN_OUTPUT_DIR / "graph_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    np.save(GNN_OUTPUT_DIR / "node_features.npy", features)
    logger.info(f"Saved graph data to {GNN_OUTPUT_DIR}")
    
    return graph_data


# ─── Step 2: Build PyTorch Geometric Data ─────────────────────────────
def build_pyg_data(graph_data: dict):
    """
    Convert extracted graph data into PyTorch Geometric format.
    """
    try:
        import torch
        from torch_geometric.data import Data
        from torch_geometric.transforms import RandomLinkSplit
    except ImportError:
        logger.error(
            "PyTorch Geometric not installed. Install with:\n"
            "  pip install torch torch-geometric\n"
            "  pip install pyg-lib torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.0.0+cpu.html"
        )
        return None
    
    num_nodes = graph_data["num_nodes"]
    features = torch.tensor(graph_data["features"], dtype=torch.float)
    
    # Build edge index from SUBSTITUTES_WITH (these are our target edges)
    # Direction matters: src→tgt means "src can substitute for tgt"
    sub_edges = graph_data["sub_edges"]
    if not sub_edges:
        logger.error("No SUBSTITUTES_WITH edges found! Cannot train.")
        return None
    
    src_list = [e[0] for e in sub_edges]
    tgt_list = [e[1] for e in sub_edges]
    edge_index = torch.tensor([src_list, tgt_list], dtype=torch.long)
    edge_attr = torch.tensor([e[2] for e in sub_edges], dtype=torch.float).unsqueeze(1)
    
    # Build message-passing edges (all edge types combined)
    # These are used for GNN neighborhood aggregation
    all_edges = []
    for src, tgt, _ in sub_edges:
        all_edges.append((src, tgt))
        all_edges.append((tgt, src))  # Bidirectional for message passing
    for src, tgt, _ in graph_data["cooc_edges"]:
        all_edges.append((src, tgt))
        all_edges.append((tgt, src))
    for src, tgt, _ in graph_data["sim_edges"]:
        all_edges.append((src, tgt))
        all_edges.append((tgt, src))
    
    # Deduplicate
    all_edges = list(set(all_edges))
    mp_src = [e[0] for e in all_edges]
    mp_tgt = [e[1] for e in all_edges]
    mp_edge_index = torch.tensor([mp_src, mp_tgt], dtype=torch.long)
    
    logger.info(f"Message-passing edges: {len(all_edges)}")
    logger.info(f"Target (substitution) edges: {len(sub_edges)}")
    
    # Create PyG Data object
    data = Data(
        x=features,
        edge_index=mp_edge_index,  # For GNN message passing
        num_nodes=num_nodes,
    )
    
    # Store target edges separately
    data.sub_edge_index = edge_index
    data.sub_edge_attr = edge_attr
    
    return data


# ─── Step 3: GNN Model Definition ─────────────────────────────────────
def build_model():
    """Build the GraphSAGE encoder + link prediction decoder."""
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch_geometric.nn import SAGEConv
    except ImportError:
        logger.error("PyTorch Geometric not installed.")
        return None, None
    
    class GraphSAGEEncoder(nn.Module):
        """2-layer GraphSAGE encoder for node embeddings."""
        
        def __init__(self, in_dim, hidden_dim, out_dim, dropout=0.3):
            super().__init__()
            self.conv1 = SAGEConv(in_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, out_dim)
            self.dropout = dropout
            self.bn1 = nn.BatchNorm1d(hidden_dim)
        
        def forward(self, x, edge_index):
            x = self.conv1(x, edge_index)
            x = self.bn1(x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
            x = self.conv2(x, edge_index)
            return x
    
    class LinkPredictor(nn.Module):
        """MLP predictor for directed link prediction."""
        
        def __init__(self, in_dim, hidden_dim=64):
            super().__init__()
            self.lin1 = nn.Linear(2 * in_dim, hidden_dim)
            self.lin2 = nn.Linear(hidden_dim, 1)
        
        def forward(self, z_src, z_tgt):
            # Concatenate source and target embeddings (order matters for direction)
            h = torch.cat([z_src, z_tgt], dim=-1)
            h = F.relu(self.lin1(h))
            return self.lin2(h).squeeze(-1)
    
    encoder = GraphSAGEEncoder(EMBEDDING_DIM, HIDDEN_DIM, OUTPUT_DIM, DROPOUT)
    predictor = LinkPredictor(OUTPUT_DIM)
    
    return encoder, predictor


# ─── Step 4: Training Loop ────────────────────────────────────────────
def train(graph_data: dict):
    """Main training loop."""
    try:
        import torch
        import torch.nn.functional as F
        from torch_geometric.utils import negative_sampling
    except ImportError:
        logger.error("PyTorch Geometric not installed.")
        return
    
    data = build_pyg_data(graph_data)
    if data is None:
        return
    
    encoder, predictor = build_model()
    if encoder is None:
        return
    
    # Split target edges into train/val/test
    num_sub_edges = data.sub_edge_index.size(1)
    perm = torch.randperm(num_sub_edges)
    
    n_train = int(num_sub_edges * TRAIN_SPLIT)
    n_val = int(num_sub_edges * VAL_SPLIT)
    
    train_mask = perm[:n_train]
    val_mask = perm[n_train:n_train + n_val]
    test_mask = perm[n_train + n_val:]
    
    train_edges = data.sub_edge_index[:, train_mask]
    val_edges = data.sub_edge_index[:, val_mask]
    test_edges = data.sub_edge_index[:, test_mask]
    
    logger.info(f"Edge splits: train={train_edges.size(1)}, val={val_edges.size(1)}, test={test_edges.size(1)}")
    
    # Optimizer
    optimizer = torch.optim.Adam(
        list(encoder.parameters()) + list(predictor.parameters()),
        lr=LEARNING_RATE,
        weight_decay=1e-5,
    )
    
    best_val_auc = 0
    patience = 10
    patience_counter = 0
    
    for epoch in range(1, EPOCHS + 1):
        encoder.train()
        predictor.train()
        
        # Forward pass: encode all nodes
        z = encoder(data.x, data.edge_index)
        
        # Positive edges
        pos_src = train_edges[0]
        pos_tgt = train_edges[1]
        pos_score = predictor(z[pos_src], z[pos_tgt])
        
        # Negative sampling
        neg_edges = negative_sampling(
            edge_index=data.sub_edge_index,
            num_nodes=data.num_nodes,
            num_neg_samples=train_edges.size(1) * NEG_RATIO,
        )
        neg_src = neg_edges[0]
        neg_tgt = neg_edges[1]
        neg_score = predictor(z[neg_src], z[neg_tgt])
        
        # Binary cross-entropy loss
        pos_loss = F.binary_cross_entropy_with_logits(
            pos_score, torch.ones_like(pos_score)
        )
        neg_loss = F.binary_cross_entropy_with_logits(
            neg_score, torch.zeros_like(neg_score)
        )
        loss = pos_loss + neg_loss
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Validation
        if epoch % 5 == 0:
            encoder.eval()
            predictor.eval()
            with torch.no_grad():
                z = encoder(data.x, data.edge_index)
                
                # Val positive
                val_pos = predictor(z[val_edges[0]], z[val_edges[1]])
                # Val negative
                val_neg_edges = negative_sampling(
                    edge_index=data.sub_edge_index,
                    num_nodes=data.num_nodes,
                    num_neg_samples=val_edges.size(1),
                )
                val_neg = predictor(z[val_neg_edges[0]], z[val_neg_edges[1]])
                
                # AUC
                from sklearn.metrics import roc_auc_score
                labels = torch.cat([
                    torch.ones(val_pos.size(0)),
                    torch.zeros(val_neg.size(0)),
                ]).numpy()
                scores = torch.cat([
                    torch.sigmoid(val_pos),
                    torch.sigmoid(val_neg),
                ]).numpy()
                
                val_auc = roc_auc_score(labels, scores)
            
            logger.info(f"Epoch {epoch:3d} | Loss: {loss.item():.4f} | Val AUC: {val_auc:.4f}")
            
            if val_auc > best_val_auc:
                best_val_auc = val_auc
                patience_counter = 0
                # Save best model
                torch.save({
                    "encoder": encoder.state_dict(),
                    "predictor": predictor.state_dict(),
                    "epoch": epoch,
                    "val_auc": val_auc,
                }, GNN_OUTPUT_DIR / "best_model.pt")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
    
    logger.info(f"Best Val AUC: {best_val_auc:.4f}")
    
    # Test evaluation
    encoder.eval()
    predictor.eval()
    checkpoint = torch.load(GNN_OUTPUT_DIR / "best_model.pt")
    encoder.load_state_dict(checkpoint["encoder"])
    predictor.load_state_dict(checkpoint["predictor"])
    
    with torch.no_grad():
        z = encoder(data.x, data.edge_index)
        test_pos = predictor(z[test_edges[0]], z[test_edges[1]])
        test_neg_edges = negative_sampling(
            edge_index=data.sub_edge_index,
            num_nodes=data.num_nodes,
            num_neg_samples=test_edges.size(1),
        )
        test_neg = predictor(z[test_neg_edges[0]], z[test_neg_edges[1]])
        
        from sklearn.metrics import roc_auc_score, average_precision_score
        labels = torch.cat([
            torch.ones(test_pos.size(0)),
            torch.zeros(test_neg.size(0)),
        ]).numpy()
        scores = torch.cat([
            torch.sigmoid(test_pos),
            torch.sigmoid(test_neg),
        ]).numpy()
        
        test_auc = roc_auc_score(labels, scores)
        test_ap = average_precision_score(labels, scores)
    
    logger.info(f"Test AUC: {test_auc:.4f} | Test AP: {test_ap:.4f}")
    
    # Save final node embeddings for inference
    with torch.no_grad():
        z = encoder(data.x, data.edge_index)
        np.save(GNN_OUTPUT_DIR / "node_embeddings.npy", z.numpy())
    
    # Save idx→name mapping
    with open(GNN_OUTPUT_DIR / "idx_to_name.json", "w") as f:
        json.dump(graph_data["idx_to_name"], f)
    
    logger.info(f"✅ GNN training complete! Model saved to {GNN_OUTPUT_DIR}")
    logger.info("Next: Integrate GNN embeddings into substitution_service.py")


# ─── Step 5: Inference Helper ─────────────────────────────────────────
def predict_substitutes(ingredient_name: str, top_k: int = 5) -> list[dict]:
    """
    Use trained GNN to predict substitutes for an ingredient.
    
    Args:
        ingredient_name: The ingredient to find substitutes for
        top_k: Number of substitutes to return
    
    Returns:
        List of {name, score} dicts
    """
    import torch
    
    # Load model and data
    embeddings = np.load(GNN_OUTPUT_DIR / "node_embeddings.npy")
    with open(GNN_OUTPUT_DIR / "idx_to_name.json") as f:
        idx_to_name = json.load(f)
    name_to_idx = {v: int(k) for k, v in idx_to_name.items()}
    
    # Check if ingredient exists
    norm_name = ingredient_name.lower().strip()
    if norm_name not in name_to_idx:
        logger.warning(f"'{ingredient_name}' not in graph vocabulary")
        return []
    
    src_idx = name_to_idx[norm_name]
    src_emb = embeddings[src_idx]
    
    # Load predictor
    _, predictor = build_model()
    checkpoint = torch.load(GNN_OUTPUT_DIR / "best_model.pt", map_location="cpu")
    predictor.load_state_dict(checkpoint["predictor"])
    predictor.eval()
    
    # Score all potential targets
    src_tensor = torch.tensor(src_emb, dtype=torch.float).unsqueeze(0).expand(len(embeddings), -1)
    tgt_tensor = torch.tensor(embeddings, dtype=torch.float)
    
    with torch.no_grad():
        scores = torch.sigmoid(predictor(src_tensor, tgt_tensor)).numpy()
    
    # Get top-k (excluding self)
    ranked = np.argsort(scores)[::-1]
    results = []
    for idx in ranked:
        if idx == src_idx:
            continue
        results.append({
            "name": idx_to_name[str(idx)],
            "score": float(scores[idx]),
            "source": "gnn",
        })
        if len(results) >= top_k:
            break
    
    return results


# ─── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--predict":
        ingredient = sys.argv[2] if len(sys.argv) > 2 else "butter"
        results = predict_substitutes(ingredient)
        print(f"\n🔍 GNN substitutes for '{ingredient}':")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['name']} (score: {r['score']:.4f})")
    elif len(sys.argv) > 1 and sys.argv[1] == "--extract":
        extract_graph_from_neo4j()
    else:
        graph_data = extract_graph_from_neo4j()
        train(graph_data)
