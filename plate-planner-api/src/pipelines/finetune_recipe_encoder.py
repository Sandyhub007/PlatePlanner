"""
Fine-tune SentenceTransformer on RecipeNLG Food-Domain Data
============================================================
Uses contrastive learning (MultipleNegativesRankingLoss) to teach the model
that recipe ingredient lists are semantically similar to user ingredient queries.

Training pairs:
  - Anchor: subset of ingredients (simulates user query)
  - Positive: full ingredient list from the same recipe
  - Negatives: mined from other recipes in the batch

Run: poetry run python -m src.pipelines.finetune_recipe_encoder
Estimated time: ~1-2 hours on GPU, ~6-8 hours on CPU (Mac M-series)
"""

import ast
import random
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import (
    SentenceTransformer,
    InputExample,
    losses,
    evaluation,
)
from torch.utils.data import DataLoader

# ─── Config ───────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_MODEL = "all-MiniLM-L6-v2"
OUTPUT_DIR = Path("src/data/models/recipe_suggestion/finetuned-recipe-encoder")
RAW_DATA = Path("src/data/raw/RecipeNLG_dataset.csv")

# Training hyperparameters
TRAIN_LIMIT = 500_000       # Number of recipes to use for training pairs
EVAL_LIMIT = 5_000          # Number for evaluation
BATCH_SIZE = 128            # Larger = better negatives mining
EPOCHS = 3                  # 3 epochs is usually sufficient for fine-tuning
WARMUP_RATIO = 0.1          # 10% of training steps
LEARNING_RATE = 2e-5        # Conservative LR for fine-tuning
MAX_SEQ_LENGTH = 128        # Ingredient lists are short
QUERY_INGREDIENT_RANGE = (2, 5)  # Simulate user typing 2-5 ingredients

random.seed(42)
np.random.seed(42)


# ─── Data Preparation ─────────────────────────────────────────────────
def parse_ingredients(ner_str: str) -> list[str]:
    """Parse NER column to ingredient list."""
    if pd.isna(ner_str):
        return []
    try:
        ing_list = ast.literal_eval(ner_str)
        if isinstance(ing_list, list):
            return [i.lower().strip() for i in ing_list if i and len(i.strip()) > 1]
    except (ValueError, SyntaxError):
        pass
    return []


def create_training_pair(ingredients: list[str]) -> tuple[str, str] | None:
    """
    Create (query, document) pair from a recipe's ingredients.
    
    Query = random subset (simulates what user types)
    Document = full ingredient list (what we want to retrieve)
    """
    if len(ingredients) < 3:
        return None
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for ing in ingredients:
        if ing not in seen:
            seen.add(ing)
            unique.append(ing)
    
    if len(unique) < 3:
        return None
    
    # Query: random 2-5 ingredients
    n_query = min(random.randint(*QUERY_INGREDIENT_RANGE), len(unique) - 1)
    query_ings = random.sample(unique, n_query)
    
    # Document: full ingredient list
    query = ", ".join(query_ings)
    document = ", ".join(unique)
    
    return query, document


def load_and_prepare_data():
    """Load RecipeNLG and create training/eval pairs."""
    logger.info(f"Loading RecipeNLG dataset...")
    df = pd.read_csv(RAW_DATA, nrows=TRAIN_LIMIT + EVAL_LIMIT, usecols=["NER"])
    logger.info(f"Loaded {len(df):,} recipes")
    
    # Parse ingredients
    logger.info("Parsing ingredients...")
    df["ingredients"] = df["NER"].apply(parse_ingredients)
    df = df[df["ingredients"].apply(len) >= 3].reset_index(drop=True)
    logger.info(f"After filtering: {len(df):,} recipes with ≥3 ingredients")
    
    # Shuffle and split
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    eval_df = df.iloc[:EVAL_LIMIT]
    train_df = df.iloc[EVAL_LIMIT:]
    
    # Create training pairs
    logger.info("Creating training pairs...")
    train_examples = []
    for _, row in train_df.iterrows():
        pair = create_training_pair(row["ingredients"])
        if pair:
            train_examples.append(InputExample(texts=[pair[0], pair[1]]))
    
    # Create additional hard-positive pairs (ingredient overlaps with different orderings)
    logger.info("Creating hard-positive augmentation pairs...")
    augmented = []
    for _, row in train_df.sample(min(50_000, len(train_df)), random_state=123).iterrows():
        ings = row["ingredients"]
        if len(ings) >= 4:
            # Create two different subsets from the same recipe
            n = len(ings)
            half = n // 2
            subset1 = ", ".join(random.sample(ings, min(half, 4)))
            subset2 = ", ".join(random.sample(ings, min(half, 4)))
            augmented.append(InputExample(texts=[subset1, subset2]))
    
    train_examples.extend(augmented)
    random.shuffle(train_examples)
    logger.info(f"Total training pairs: {len(train_examples):,}")
    
    # Create evaluation queries
    logger.info("Creating evaluation set...")
    eval_queries = {}
    eval_corpus = {}
    eval_relevant = {}
    
    for i, (_, row) in enumerate(eval_df.iterrows()):
        pair = create_training_pair(row["ingredients"])
        if pair:
            qid = f"q{i}"
            cid = f"c{i}"
            eval_queries[qid] = pair[0]
            eval_corpus[cid] = pair[1]
            eval_relevant[qid] = {cid}
    
    logger.info(f"Evaluation set: {len(eval_queries)} queries")
    
    return train_examples, eval_queries, eval_corpus, eval_relevant


# ─── Training ─────────────────────────────────────────────────────────
def train():
    """Fine-tune the SentenceTransformer model."""
    # Load base model
    logger.info(f"Loading base model: {BASE_MODEL}")
    model = SentenceTransformer(BASE_MODEL)
    model.max_seq_length = MAX_SEQ_LENGTH
    
    # Prepare data
    train_examples, eval_queries, eval_corpus, eval_relevant = load_and_prepare_data()
    
    # DataLoader
    train_dataloader = DataLoader(
        train_examples,
        shuffle=True,
        batch_size=BATCH_SIZE,
        drop_last=True,  # Ensures consistent batch size for MNR loss
    )
    
    # Loss: MultipleNegativesRankingLoss
    # Each batch automatically uses all other positives as negatives
    # With batch_size=128, each query gets 127 negative examples for free
    train_loss = losses.MultipleNegativesRankingLoss(model)
    
    # Evaluator
    evaluator = evaluation.InformationRetrievalEvaluator(
        queries=eval_queries,
        corpus=eval_corpus,
        relevant_docs=eval_relevant,
        name="recipe-retrieval",
        show_progress_bar=True,
    )
    
    # Calculate training steps
    total_steps = len(train_dataloader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    
    logger.info(f"Training configuration:")
    logger.info(f"  - Training pairs: {len(train_examples):,}")
    logger.info(f"  - Batch size: {BATCH_SIZE}")
    logger.info(f"  - Epochs: {EPOCHS}")
    logger.info(f"  - Total steps: {total_steps:,}")
    logger.info(f"  - Warmup steps: {warmup_steps:,}")
    logger.info(f"  - Learning rate: {LEARNING_RATE}")
    
    # Evaluate before training
    logger.info("Evaluating base model (before fine-tuning)...")
    pre_metrics = evaluator(model, output_path=str(OUTPUT_DIR / "eval_before"))
    
    # Train
    logger.info("Starting fine-tuning...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=evaluator,
        epochs=EPOCHS,
        warmup_steps=warmup_steps,
        output_path=str(OUTPUT_DIR),
        evaluation_steps=len(train_dataloader) // 2,  # Evaluate twice per epoch
        save_best_model=True,
        optimizer_params={"lr": LEARNING_RATE},
        show_progress_bar=True,
        use_amp=True,  # Mixed precision for faster training on GPU
    )
    
    logger.info(f"✅ Fine-tuned model saved to: {OUTPUT_DIR}")
    logger.info("Next step: Run rebuild_index_finetuned.py to regenerate FAISS index with new embeddings")


# ─── Post-Training: Rebuild FAISS Index ──────────────────────────────
def rebuild_index():
    """
    After fine-tuning, regenerate embeddings and FAISS index.
    Run this AFTER training completes successfully.
    """
    import faiss
    
    METADATA_PATH = Path("src/data/processed/recipe_suggestion/recipe_metadata.csv")
    EMBEDDINGS_OUT = Path("src/data/processed/recipe_suggestion/recipe_embeddings_finetuned.npy")
    INDEX_OUT = Path("src/data/models/recipe_suggestion/recipe_index_finetuned.faiss")
    OPT_INDEX_OUT = Path("src/data/models/recipe_suggestion/recipe_index_finetuned_opt.faiss")
    
    logger.info(f"Loading fine-tuned model from {OUTPUT_DIR}...")
    model = SentenceTransformer(str(OUTPUT_DIR))
    
    logger.info("Loading recipe metadata...")
    metadata = pd.read_csv(METADATA_PATH)
    texts = metadata["NER"].fillna("").tolist()
    
    logger.info(f"Generating embeddings for {len(texts):,} recipes...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=256,
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype("float32")
    
    logger.info(f"Saving embeddings (shape={embeddings.shape})...")
    np.save(EMBEDDINGS_OUT, embeddings)
    
    # Build flat index
    logger.info("Building flat FAISS index...")
    faiss.normalize_L2(embeddings)
    flat_index = faiss.IndexFlatIP(embeddings.shape[1])
    flat_index.add(embeddings)
    faiss.write_index(flat_index, str(INDEX_OUT))
    
    # Build optimized IVF-PQ index
    logger.info("Building optimized IVF-PQ index...")
    d = embeddings.shape[1]
    nlist = 4096
    m = 32
    quantizer = faiss.IndexFlatL2(d)
    opt_index = faiss.IndexIVFPQ(quantizer, d, nlist, m, 8)
    
    train_size = min(100_000, len(embeddings))
    x_train = embeddings[:train_size].copy()
    opt_index.train(x_train)
    
    batch_size = 50_000
    for i in range(0, len(embeddings), batch_size):
        end = min(i + batch_size, len(embeddings))
        opt_index.add(embeddings[i:end])
        logger.info(f"  Added {end:,}/{len(embeddings):,} vectors")
    
    faiss.write_index(opt_index, str(OPT_INDEX_OUT))
    logger.info(f"✅ Fine-tuned FAISS indices saved!")
    logger.info(f"  - Flat: {INDEX_OUT}")
    logger.info(f"  - Optimized: {OPT_INDEX_OUT}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild-index":
        rebuild_index()
    else:
        train()
