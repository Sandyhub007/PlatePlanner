"""
PlatePlanner Project Report Generator
Generates a comprehensive technical PDF report.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Flowable
import os

# ── Color Palette ───────────────────────────────────────────────────────────
PRIMARY      = HexColor("#1B4F72")   # deep navy
ACCENT       = HexColor("#2E86AB")   # teal-blue
LIGHT_BG     = HexColor("#EBF5FB")   # pale blue tint
DARK_BG      = HexColor("#154360")   # darker navy for header
GREY_TEXT    = HexColor("#566573")   # muted grey
LIGHT_GREY   = HexColor("#F2F3F4")   # table alt row
GREEN        = HexColor("#1E8449")
ORANGE       = HexColor("#D35400")
RED          = HexColor("#C0392B")

OUTPUT_PATH = "/Users/sandilyachimalamarri/Plateplanner/PlatePlanner_Technical_Report.pdf"

# ── Custom Flowables ─────────────────────────────────────────────────────────
class ColoredRule(Flowable):
    def __init__(self, width, color=ACCENT, thickness=2):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness
        self.height = thickness

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


class SectionHeader(Flowable):
    """A colored banner for top-level sections."""
    def __init__(self, text, width, bg=PRIMARY, fg=white, font_size=13):
        Flowable.__init__(self)
        self.text = text
        self.width = width
        self.bg = bg
        self.fg = fg
        self.font_size = font_size
        self.height = font_size + 14

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawString(10, 4, self.text)


# ── Style Sheet ───────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles['cover_title'] = ParagraphStyle(
        'cover_title', parent=base['Title'],
        fontSize=30, leading=36, textColor=white,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=8
    )
    styles['cover_sub'] = ParagraphStyle(
        'cover_sub', parent=base['Normal'],
        fontSize=13, leading=18, textColor=HexColor("#AED6F1"),
        alignment=TA_CENTER
    )
    styles['cover_meta'] = ParagraphStyle(
        'cover_meta', parent=base['Normal'],
        fontSize=10, textColor=HexColor("#D6EAF8"),
        alignment=TA_CENTER, spaceBefore=4
    )
    styles['h2'] = ParagraphStyle(
        'h2', parent=base['Heading2'],
        fontSize=12, leading=16, textColor=ACCENT,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=4
    )
    styles['h3'] = ParagraphStyle(
        'h3', parent=base['Heading3'],
        fontSize=10.5, leading=14, textColor=PRIMARY,
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=3
    )
    styles['body'] = ParagraphStyle(
        'body', parent=base['Normal'],
        fontSize=9.5, leading=14, textColor=HexColor("#2C3E50"),
        alignment=TA_JUSTIFY, spaceAfter=5
    )
    styles['bullet'] = ParagraphStyle(
        'bullet', parent=base['Normal'],
        fontSize=9.5, leading=14, textColor=HexColor("#2C3E50"),
        leftIndent=16, bulletIndent=4, spaceAfter=3
    )
    styles['code'] = ParagraphStyle(
        'code', parent=base['Code'],
        fontSize=8, leading=12, textColor=HexColor("#1A5276"),
        backColor=LIGHT_BG, leftIndent=12, rightIndent=12,
        borderPad=4, spaceAfter=6
    )
    styles['caption'] = ParagraphStyle(
        'caption', parent=base['Normal'],
        fontSize=8, leading=11, textColor=GREY_TEXT,
        alignment=TA_CENTER, spaceAfter=8
    )
    styles['metric_label'] = ParagraphStyle(
        'metric_label', parent=base['Normal'],
        fontSize=8.5, textColor=GREY_TEXT, alignment=TA_CENTER
    )
    styles['metric_value'] = ParagraphStyle(
        'metric_value', parent=base['Normal'],
        fontSize=20, fontName='Helvetica-Bold', textColor=PRIMARY,
        alignment=TA_CENTER
    )
    return styles


# ── Page Templates ────────────────────────────────────────────────────────────
def header_footer(canvas, doc):
    canvas.saveState()
    w, h = letter
    # Header bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, h - 36, w, 36, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(36, h - 22, "PlatePlanner — Technical Project Report")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 36, h - 22, "SJSU · CMPE 295B")
    # Footer
    canvas.setFillColor(HexColor("#BFC9CA"))
    canvas.rect(0, 0, w, 28, fill=1, stroke=0)
    canvas.setFillColor(GREY_TEXT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(36, 9, "Confidential — San Jose State University Master's Project")
    canvas.drawRightString(w - 36, 9, f"Page {doc.page}")
    canvas.restoreState()


def cover_page(canvas, doc):
    """Full-bleed cover — no standard header/footer."""
    canvas.saveState()
    w, h = letter
    # Background gradient effect (two rects)
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#1A6A9A"))
    canvas.rect(0, h * 0.55, w, h * 0.45, fill=1, stroke=0)
    # Decorative accent stripe
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h * 0.54, w, 6, fill=1, stroke=0)
    canvas.restoreState()


# ── Helper builders ───────────────────────────────────────────────────────────
def bullet(text, styles):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", styles['bullet'])

def h2(text, page_width, styles):
    return [
        Spacer(1, 6),
        SectionHeader(text, page_width),
        Spacer(1, 6),
    ]

def h3(text, styles):
    return Paragraph(text, styles['h3'])

def body(text, styles):
    return Paragraph(text, styles['body'])

def sp(n=8):
    return Spacer(1, n)

def rule(w, color=ACCENT, thickness=1):
    return ColoredRule(w, color, thickness)


def make_table(headers, rows, col_widths):
    data = [headers] + rows
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GREY]),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor("#BFC9CA")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    tbl.setStyle(style)
    return tbl


def metrics_table(items, styles):
    """items = [(label, value, color), ...]"""
    cells = []
    for label, value, color in items:
        cell = [
            Paragraph(value, ParagraphStyle('mv', parent=styles['metric_value'], textColor=color)),
            Paragraph(label, styles['metric_label'])
        ]
        cells.append(cell)
    n = len(items)
    tbl = Table([cells], colWidths=[inch * 6.5 / n] * n)
    tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#AED6F1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor("#AED6F1")),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tbl


# ── Report Content ────────────────────────────────────────────────────────────
def build_story(styles, page_width):
    story = []
    W = page_width

    # ─── COVER (first frame — no header/footer) ─────────────────────────────
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph("PlatePlanner", styles['cover_title']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("AI-Powered Meal Planning &amp; Recipe Recommendation System", styles['cover_sub']))
    story.append(Spacer(1, 18))
    story.append(rule(W, white, 1))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Technical Project Report", styles['cover_meta']))
    story.append(Paragraph("San Jose State University · CMPE 295B Master's Project", styles['cover_meta']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Sandilya Chimalamarri &nbsp;·&nbsp; Sai Priyanka Bonkuri &nbsp;·&nbsp; "
        "Pavan Charith Devarapalli &nbsp;·&nbsp; Sai Dheeraj Gollu",
        styles['cover_meta']
    ))
    story.append(Paragraph("April 2026", styles['cover_meta']))
    story.append(PageBreak())

    # ─── 1. EXECUTIVE SUMMARY ───────────────────────────────────────────────
    story += h2("1. Executive Summary", W, styles)
    story.append(body(
        "PlatePlanner is an AI-powered, graph-enhanced meal planning and recipe recommendation "
        "platform developed as a San Jose State University CMPE 295B capstone project. The system "
        "addresses a common problem: users have a set of available ingredients and dietary "
        "constraints, but lack a fast, intelligent way to discover suitable recipes, plan meals, "
        "generate shopping lists, and navigate ingredient substitutions.", styles
    ))
    story.append(body(
        "The platform combines a FastAPI backend, a Neo4j property-graph database, PostgreSQL "
        "relational storage, Redis caching, and a FAISS vector-search index over 2.2 million "
        "recipes. A hybrid semantic + ingredient-overlap ranking algorithm improves recall by 23% "
        "over a pure vector-search baseline. A React Native mobile client exposes the full feature "
        "set on iOS and Android.", styles
    ))
    story.append(sp(10))
    story.append(metrics_table([
        ("Total Recipes", "2.2M+", PRIMARY),
        ("Test Coverage", "95%+", GREEN),
        ("FAISS Latency", "<20ms", ACCENT),
        ("Recall Boost", "+23%", GREEN),
        ("Throughput", "100+ RPS", ORANGE),
    ], styles))
    story.append(sp(6))
    story.append(Paragraph("Table 1 — Key system performance metrics", styles['caption']))

    # ─── 2. CORE ARCHITECTURE ───────────────────────────────────────────────
    story += h2("2. Core Architecture", W, styles)
    story.append(body(
        "PlatePlanner follows a <b>4-Tier architecture</b> that cleanly separates concerns "
        "across API, service, data-persistence, and ML-inference layers.", styles
    ))

    story.append(h3("2.1 Tier 1 — API Layer (FastAPI)", styles))
    story.append(body(
        "The entry point is <code>src/api/app.py</code>. FastAPI 0.115 runs on Uvicorn (ASGI, "
        "fully async). Eight REST routers handle: <i>auth, users, meal_plans, shopping_lists, "
        "nutrition, recommendations, user_meals,</i> and <i>pantry</i>. Request/response "
        "validation is handled by Pydantic v2. CORS origins are configurable via the "
        "<code>ALLOWED_ORIGINS</code> environment variable.", styles
    ))

    story.append(h3("2.2 Tier 2 — Service Layer (Domain-Driven Design)", styles))
    story.append(body(
        "All business logic lives in <code>src/services/</code>. Key services:", styles
    ))
    svc_rows = [
        ["neo4j_service.py", "Graph database wrapper; Cypher query execution"],
        ["retrieval_service.py", "FAISS vector search + hybrid re-ranking"],
        ["substitution_service.py", "Pantry-aware ingredient substitution"],
        ["meal_plan_service.py", "AI-driven weekly meal plan generation"],
        ["shopping_list_service.py", "Multi-recipe aggregation & unit normalisation (730+ lines)"],
        ["nutrition_service.py", "USDA-backed macronutrient analysis & goal tracking"],
        ["rag_service.py", "LLM-powered recipe generation / adaptation (RAG pipeline)"],
        ["dietary_classifier.py", "Rule-based dietary tag & allergen detection"],
        ["external_recipe_service.py", "Spoonacular API fallback integration"],
    ]
    story.append(make_table(
        ["Service File", "Responsibility"],
        svc_rows,
        [2.4 * inch, 4.1 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 2 — Service layer modules", styles['caption']))

    story.append(h3("2.3 Tier 3 — Polyglot Persistence Layer", styles))
    story.append(body(
        "Each storage technology is chosen to match its data's access pattern:", styles
    ))
    db_rows = [
        ["PostgreSQL 15", "Users, meal plans, shopping lists, nutrition logs — ACID, relational"],
        ["Neo4j 5.x", "Recipe–ingredient graph, substitution edges, similarity edges"],
        ["Redis 7", "Session tokens, API response cache, rate-limiting, job queue"],
        ["SQLite 3", "Recipe metadata cache (2.2M rows); optimised for fast lookup"],
    ]
    story.append(make_table(
        ["Database", "Role"],
        db_rows,
        [1.8 * inch, 4.7 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 3 — Polyglot persistence layer", styles['caption']))

    story.append(h3("2.4 Tier 4 — ML / AI Inference Layer", styles))
    story.append(body(
        "CPU-bound inference tasks run in a dedicated thread pool to avoid blocking the async "
        "event loop. The inference pipeline is:", styles
    ))
    for step in [
        "<b>1. Query embedding</b> — User ingredients text → 384-d vector via SentenceTransformer.",
        "<b>2. ANN search</b> — FAISS IVF-PQ index returns top-500 nearest recipe vectors (&lt;20ms).",
        "<b>3. Hybrid re-ranking</b> — Combines cosine similarity (40%) with discrete ingredient "
        "overlap (60%) to produce a final combined score.",
        "<b>4. Dietary filtering</b> — Rule-based classifier removes recipes that violate user "
        "restrictions or contain allergens.",
        "<b>5. LLM fallback</b> — When FAISS matches are sparse, the RAG service calls "
        "OpenAI / Gemini / Ollama to synthesise novel recipes.",
    ]:
        story.append(bullet(step, styles))

    # ─── 3. ML MODELS ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += h2("3. Machine Learning Models", W, styles)

    story.append(h3("3.1 Sentence-Transformer Embedding Model", styles))
    story.append(body(
        "The primary embedding model is <b>all-MiniLM-L6-v2</b> from the "
        "sentence-transformers library (v4.1.0). It produces 384-dimensional dense vectors "
        "that capture semantic meaning of recipe titles and ingredient lists. The model is "
        "lightweight enough to run on CPU with sub-50ms encoding latency for typical queries. "
        "An optional <b>finetuned-recipe-encoder</b> (domain-adapted on food/recipe text) "
        "is auto-loaded when present at "
        "<code>src/data/models/recipe_suggestion/finetuned-recipe-encoder/</code>.", styles
    ))

    story.append(h3("3.2 FAISS Vector Index", styles))
    story.append(body(
        "All 2.2 million recipe embeddings are indexed with <b>FAISS 1.11.0</b>. "
        "Two variants are maintained:", styles
    ))
    faiss_rows = [
        ["recipe_index_opt.faiss", "IVF-PQ (quantised)", "~90 MB", "&lt;20ms", "Production"],
        ["recipe_index.faiss", "Flat (exact)", "~12 GB", "~200ms", "Evaluation only"],
    ]
    story.append(make_table(
        ["File", "Index Type", "Size", "p95 Latency", "Usage"],
        faiss_rows,
        [2.0 * inch, 1.4 * inch, 0.7 * inch, 0.9 * inch, 1.3 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph(
        "Table 4 — FAISS index variants. IVF-PQ (Inverted File + Product Quantisation) reduces "
        "RAM from ~12 GB to &lt;200 MB while maintaining sub-20ms recall.", styles['caption']
    ))

    story.append(h3("3.3 Hybrid Ranking Algorithm", styles))
    story.append(body(
        "Raw FAISS cosine similarity alone struggles to surface recipes that share many of the "
        "user's exact ingredients but differ in cooking style or phrasing. The hybrid ranker "
        "combines two complementary signals:", styles
    ))
    story.append(body(
        "<b>combined_score = 0.4 × cosine_similarity + 0.6 × normalised_ingredient_overlap</b>",
        styles
    ))
    story.append(body(
        "The 60/40 weighting was determined empirically and yields a <b>+23% recall improvement</b> "
        "over pure vector search on an internal evaluation set.", styles
    ))

    story.append(h3("3.4 Named Entity Recognition (SpaCy)", styles))
    story.append(body(
        "<b>SpaCy en_core_web_sm</b> (v3.8.5) is used during data-ingestion pipelines to "
        "extract ingredient entities from unstructured recipe text. It achieves 87% precision "
        "and 82% recall on 1.5M unstructured ingredient strings. Parsed entities feed the "
        "Neo4j graph and FAISS metadata.", styles
    ))

    story.append(h3("3.5 Dietary Classification", styles))
    story.append(body(
        "A rule-based <code>DietaryClassifier</code> (no external model required) flags recipes "
        "with dietary and allergen tags. It handles tricky compound ingredients "
        "(e.g., <i>coconut milk</i> is dairy-free; <i>soy sauce</i> contains gluten and soy). "
        "Supported tags:", styles
    ))
    tags = [
        "Dietary: vegan, vegetarian, gluten-free, dairy-free",
        "Allergens: peanuts, tree nuts, soy, fish, shellfish, eggs, dairy, gluten",
    ]
    for t in tags:
        story.append(bullet(t, styles))

    story.append(h3("3.6 LLM Backends (RAG Pipeline)", styles))
    story.append(body(
        "When FAISS retrieval returns insufficient results the RAG service generates novel "
        "recipes via a configurable LLM backend. The auto-detection chain is:", styles
    ))
    llm_rows = [
        ["OpenAI", "gpt-4o-mini (default) or gpt-4", "OPENAI_API_KEY set", "Best quality"],
        ["Google Gemini", "gemini-2.0-flash (with fallback chain)", "GOOGLE_API_KEY set", "Fast, free tier"],
        ["Ollama (local)", "llama3 or configurable model", "Default fallback", "Privacy, no cost"],
    ]
    story.append(make_table(
        ["Provider", "Model", "Activation", "Trade-off"],
        llm_rows,
        [1.2 * inch, 2.0 * inch, 1.6 * inch, 1.5 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 5 — LLM backend options", styles['caption']))

    # ─── 4. DATASETS & DATA SOURCES ─────────────────────────────────────────
    story.append(PageBreak())
    story += h2("4. Datasets & Data Sources", W, styles)

    story.append(h3("4.1 RecipeNLG (Primary Dataset)", styles))
    story.append(body(
        "<b>RecipeNLG</b> is the backbone of the recommendation engine. It contains "
        "<b>2,231,150 recipes</b> scraped from cookbooks.com and other sources, released as a "
        "benchmark for natural language generation in the cooking domain. Each record includes:", styles
    ))
    for col in [
        "<b>title</b> — Recipe name (used for fuzzy deduplication and display)",
        "<b>ingredients</b> — JSON list of raw ingredient strings",
        "<b>directions</b> — JSON list of cooking step strings",
        "<b>link</b> — Source URL",
        "<b>source</b> — Origin domain",
        "<b>NER</b> — SpaCy-parsed named entities (ingredient tokens only)",
    ]:
        story.append(bullet(col, styles))
    story.append(body(
        "The raw CSV is stored at <code>src/data/raw/RecipeNLG_dataset.csv</code> (approx. "
        "3–4 GB). A cleaned and indexed SQLite copy (~90 MB) is maintained at "
        "<code>src/data/models/recipe_suggestion/recipes.db</code> for fast lookup.", styles
    ))

    story.append(h3("4.2 International Recipe Datasets", styles))
    story.append(body(
        "Three supplementary datasets extend coverage beyond English-language recipes:", styles
    ))
    int_rows = [
        ["food_com_recipes.csv", "Food.com corpus", "Community-submitted, diverse cuisines"],
        ["recipes_with_nutrition.csv", "Nutrition-enriched recipes", "Adds calorie/macro data per recipe"],
        ["cooking_recipes_large.csv", "Large cooking collection", "Extended cuisine diversity"],
    ]
    story.append(make_table(
        ["File", "Source", "Value Added"],
        int_rows,
        [2.0 * inch, 2.0 * inch, 2.5 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 6 — International recipe datasets (src/data/raw/international/)", styles['caption']))

    story.append(h3("4.3 USDA Nutrient Data", styles))
    story.append(body(
        "Macronutrient values (calories, protein, carbohydrates, fat) per ingredient are sourced "
        "from the <b>USDA FoodData Central</b> database and stored in the "
        "<code>IngredientNutrition</code> PostgreSQL table. This powers the nutrition analysis "
        "and goal-tracking features.", styles
    ))

    story.append(h3("4.4 Spoonacular API", styles))
    story.append(body(
        "When the local recipe corpus does not contain a suitable match for a highly specific "
        "query, the <code>ExternalRecipeService</code> calls the <b>Spoonacular REST API</b> as "
        "a 3rd-tier fallback (after FAISS and before LLM generation). Results are normalised "
        "and returned in the same schema as local results.", styles
    ))

    story.append(h3("4.5 Processed Data (ETL Outputs)", styles))
    proc_rows = [
        ["recipes.csv", "Deduplicated recipe metadata"],
        ["ingredients.csv", "Unique ingredient vocabulary"],
        ["recipe_ingredients.csv", "Recipe–ingredient join table (for graph bootstrap)"],
        ["recipe_metadata.csv", "Extended attributes: cuisine, cook time, estimated calories"],
        ["substitution_edges_with_context_cleaned.csv", "Neo4j substitution relationship edges with context labels"],
    ]
    story.append(make_table(
        ["File (src/data/processed/)", "Contents"],
        proc_rows,
        [3.2 * inch, 3.3 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 7 — Processed data artefacts used for graph and index bootstrap", styles['caption']))

    # ─── 5. INGREDIENT SUBSTITUTIONS ────────────────────────────────────────
    story.append(PageBreak())
    story += h2("5. Ingredient Substitution System", W, styles)

    story.append(body(
        "Ingredient substitution is one of PlatePlanner's differentiating features. It "
        "combines a <b>Neo4j property graph</b> with <b>pantry-awareness</b> to suggest "
        "contextually appropriate swaps.", styles
    ))

    story.append(h3("5.1 Neo4j Graph Structure", styles))
    story.append(body(
        "The graph has three primary node types and three relationship types:", styles
    ))
    graph_rows = [
        ["Recipe", "Node", "Recipe entity with title, tags, cuisine"],
        ["Ingredient", "Node", "Normalised ingredient entity"],
        ["HAS_INGREDIENT", "Edge (Recipe→Ingredient)", "Recipe contains ingredient (with quantity)"],
        ["SUBSTITUTES_WITH", "Edge (Ingredient→Ingredient)", "Substitution with <i>context</i> property"],
        ["SIMILAR_TO", "Edge (Recipe→Recipe)", "Semantic recipe similarity for discovery"],
    ]
    story.append(make_table(
        ["Name", "Type", "Description"],
        graph_rows,
        [1.9 * inch, 1.9 * inch, 2.7 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 8 — Neo4j graph schema", styles['caption']))

    story.append(h3("5.2 Context-Aware Substitution Edges", styles))
    story.append(body(
        "The <code>SUBSTITUTES_WITH</code> relationship carries a <b>context</b> property "
        "that distinguishes <i>why</i> an ingredient is being substituted. This prevents "
        "semantically valid but culinarily wrong swaps, for example:", styles
    ))
    ctx_rows = [
        ["eggs → flax egg", "baking (binding)"],
        ["eggs → tofu scramble", "primary protein (scramble)"],
        ["cornstarch → arrowroot", "thickening"],
        ["butter → coconut oil", "fat/moisture (baking)"],
        ["milk → oat milk", "dairy-free liquid substitute"],
    ]
    story.append(make_table(
        ["Substitution Pair", "Context"],
        ctx_rows,
        [3.2 * inch, 3.3 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 9 — Example context-aware substitution edges", styles['caption']))

    story.append(h3("5.3 Hybrid Substitution Algorithm", styles))
    story.append(body(
        "For any query ingredient the service executes a two-stage lookup:", styles
    ))
    for step in [
        "<b>Stage 1 — Direct edges:</b> Traverse <code>SUBSTITUTES_WITH</code> edges in Neo4j. "
        "These are curated or similarity-derived relationships with explicit context labels. "
        "Query latency &lt;10ms (p95) even for densely connected ingredient nodes.",
        "<b>Stage 2 — Co-occurrence analysis:</b> Identify ingredients that frequently appear "
        "together in the same substitution context across the 2.2M recipe corpus.",
        "<b>Merge:</b> Results are combined with alpha-weighting (default α = 0.9), "
        "heavily favouring direct graph edges over statistical co-occurrence.",
    ]:
        story.append(bullet(step, styles))
    story.append(body(
        "User satisfaction with dietary substitution recommendations measured at <b>92%</b> "
        "in internal evaluations.", styles
    ))

    story.append(h3("5.4 Pantry-Aware Substitution", styles))
    story.append(body(
        "When a user requests substitutions for an entire recipe, <code>SubstitutionService</code> "
        "compares recipe ingredients against the user's pantry inventory "
        "(<code>UserPantryItem</code> table) and returns three lists:", styles
    ))
    for item in [
        "<b>Have:</b> Ingredients the user already owns (no substitution needed).",
        "<b>Missing:</b> Ingredients not in pantry — candidate for purchase or substitution.",
        "<b>Substitutable:</b> Missing ingredients for which a pantry item is a valid substitute, "
        "ranked by: 1) direct Neo4j edge, 2) similarity score.",
    ]:
        story.append(bullet(item, styles))

    story.append(h3("5.5 Unit Conversion & Shopping List Consolidation", styles))
    story.append(body(
        "A key enabling component is the unit-conversion engine "
        "(<code>src/utils/unit_converter.py</code>, 9,000+ lines). It:", styles
    ))
    for item in [
        "Normalises heterogeneous units: <i>1 cup → 240 ml, 1 lb → 454 g, 1 tsp → 5 ml</i>.",
        "Applies volumetric / mass conversions with density heuristics per ingredient category.",
        "Uses <b>fuzzy Levenshtein matching</b> to consolidate ingredient name variants "
        "(e.g., <i>\"diced tomatoes\"</i> and <i>\"whole tomatoes\"</i> → <i>tomatoes</i>).",
        "Achieves <b>95%+ accuracy</b> on complex multi-recipe shopping list aggregations.",
    ]:
        story.append(bullet(item, styles))

    # ─── 6. DATABASE SCHEMA ──────────────────────────────────────────────────
    story.append(PageBreak())
    story += h2("6. PostgreSQL Data Schema", W, styles)
    story.append(body(
        "All user, meal-plan, nutrition, and transactional data is stored in PostgreSQL 15 "
        "via SQLAlchemy ORM. Alembic manages schema migrations.", styles
    ))
    schema_rows = [
        ["User", "id (UUID), email, hashed_password, full_name, is_premium, is_admin, auth_provider"],
        ["UserPreferences", "dietary_restrictions[], allergies[], cuisine_preferences[], calorie/macro targets, max_cooking_time, budget"],
        ["MealPlan", "week_start/end_date, status, total macros, is_valid, validation_issues (JSON)"],
        ["MealPlanItem", "recipe_id (Neo4j ref), recipe_title, servings, macros, prep_time, estimated_cost"],
        ["ShoppingList", "status (active/completed/archived), total_estimated_cost, item counts"],
        ["ShoppingListItem", "ingredient_name, normalized_name, quantity, unit, category, estimated_price, store_prices (JSON)"],
        ["NutritionGoal", "daily calorie/protein/carb/fat targets per user"],
        ["NutritionLog", "Per-day actual macro tracking"],
        ["UserMeal", "Custom meals created by user"],
        ["UserPantryItem", "ingredient, quantity, unit, expiry_date, purchase_date"],
        ["IngredientNutrition", "USDA nutrition facts per ingredient (calories, protein, carbs, fat per 100g)"],
    ]
    story.append(make_table(
        ["Model", "Key Fields"],
        schema_rows,
        [1.7 * inch, 4.8 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 10 — PostgreSQL ORM models", styles['caption']))

    # ─── 7. API ENDPOINTS ────────────────────────────────────────────────────
    story += h2("7. Key API Endpoints", W, styles)
    api_rows = [
        ["POST /suggest_recipes", "3-tier federated search: FAISS → Spoonacular → LLM; accepts ingredients, dietary filters, allergies, cuisine"],
        ["GET /recipes/{title}", "Full recipe detail; fallback chain: SQLite → Neo4j → CSV"],
        ["GET /substitute", "Get substitutes for one ingredient with optional context and hybrid flag"],
        ["POST /recipes/{title}/substitutions", "Full recipe substitution check against user pantry"],
        ["POST /meal-plans/generate", "AI-driven weekly meal plan generation with constraint satisfaction"],
        ["POST /shopping-lists/generate", "Generate aggregated shopping list from a meal plan"],
        ["GET /nutrition/analysis", "Macronutrient breakdown for a given date range"],
        ["POST /nutrition/log", "Log a meal and update nutrition totals"],
        ["GET /nutrition/insights", "Health trends and goal-progress summary"],
        ["POST /auth/register", "JWT-based user registration"],
        ["POST /auth/login", "JWT token issuance (+ Google OAuth2 support)"],
    ]
    story.append(make_table(
        ["Endpoint", "Description"],
        api_rows,
        [2.3 * inch, 4.2 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 11 — Core REST API endpoints", styles['caption']))

    # ─── 8. TECHNOLOGY STACK ─────────────────────────────────────────────────
    story.append(PageBreak())
    story += h2("8. Technology Stack", W, styles)
    tech_rows = [
        ["FastAPI 0.115", "Backend", "Async REST framework (Uvicorn ASGI)"],
        ["Pydantic v2.11", "Backend", "Request/response validation & serialisation"],
        ["SQLAlchemy 2.0", "ORM", "PostgreSQL ORM + Alembic migrations"],
        ["sentence-transformers 4.1", "ML", "all-MiniLM-L6-v2 recipe embedding model"],
        ["FAISS 1.11", "ML", "IVF-PQ vector index over 2.2M recipes"],
        ["SpaCy 3.8", "NLP", "Named entity recognition for ingredient parsing"],
        ["scikit-learn 1.6", "ML", "Evaluation utilities, distance metrics"],
        ["neo4j-driver 5.28", "DB", "Neo4j Bolt protocol client"],
        ["Redis 7", "Cache", "Session cache, rate limiting, job queue"],
        ["PostgreSQL 15", "DB", "Primary relational store"],
        ["SQLite 3", "DB", "Local recipe metadata cache"],
        ["OpenAI SDK", "LLM", "GPT-4o-mini / GPT-4 recipe generation"],
        ["google-genai", "LLM", "Gemini 2.0 Flash recipe generation"],
        ["Ollama", "LLM", "Local model inference (llama3)"],
        ["thefuzz / python-Levenshtein", "Utils", "Fuzzy string matching for deduplication"],
        ["pint 0.23", "Utils", "Unit conversion"],
        ["React Native + Expo", "Frontend", "Cross-platform iOS/Android mobile client"],
        ["Docker + Docker Compose", "Infra", "Container orchestration"],
    ]
    story.append(make_table(
        ["Library / Tool", "Layer", "Purpose"],
        tech_rows,
        [2.0 * inch, 1.0 * inch, 3.5 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 12 — Full technology stack", styles['caption']))

    # ─── 9. PERFORMANCE & EVALUATION ─────────────────────────────────────────
    story += h2("9. Performance & Evaluation", W, styles)
    perf_rows = [
        ["FAISS query latency (500-NN)", "&lt;20ms p95", "IVF-PQ quantisation"],
        ["Neo4j substitution traversal", "&lt;10ms p95", "Dense ingredient node clusters"],
        ["End-to-end HTTP response", "&lt;80ms p95", "Async FastAPI + connection pooling"],
        ["Throughput", "100+ RPS", "Locust load tests"],
        ["SpaCy NER precision", "87%", "1.5M unstructured ingredient strings"],
        ["SpaCy NER recall", "82%", "Same evaluation set"],
        ["Shopping list accuracy", "95%+", "Multi-recipe aggregation benchmark"],
        ["Hybrid ranking recall gain", "+23%", "vs. pure FAISS cosine similarity"],
        ["Substitution user satisfaction", "92%", "Dietary substitution user study"],
        ["FAISS index size (IVF-PQ)", "~90 MB", "Down from ~12 GB flat index"],
        ["Data ingestion (10K recipes → FAISS)", "~5 min", "On standard CPU hardware"],
    ]
    story.append(make_table(
        ["Metric", "Value", "Notes"],
        perf_rows,
        [2.6 * inch, 1.1 * inch, 2.8 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 13 — Measured performance benchmarks", styles['caption']))

    # ─── 10. DEPLOYMENT ──────────────────────────────────────────────────────
    story += h2("10. Deployment & Infrastructure", W, styles)
    story.append(body(
        "The full stack is containerised with <b>Docker</b> and orchestrated via "
        "<b>Docker Compose</b>. A single <code>docker-compose.yml</code> declares five "
        "services: FastAPI, PostgreSQL, Neo4j, Redis, and a data-init bootstrap container.", styles
    ))
    for item in [
        "<b>Local dev:</b> <code>.env</code> file; all services on localhost.",
        "<b>Production:</b> <code>.env.prod</code> with TLS; PostgreSQL hosted on <b>Neon</b> "
        "(serverless Postgres); Neo4j on <b>AuraDB</b>; FastAPI on <b>Railway</b>.",
        "<b>Mobile:</b> React Native Expo build targeting iOS and Android.",
        "<b>Admin:</b> SQLAdmin dashboard mounted at <code>/admin</code> for content management.",
    ]:
        story.append(bullet(item, styles))

    # ─── 11. TEAM CONTRIBUTIONS ──────────────────────────────────────────────
    story.append(PageBreak())
    story += h2("11. Team Contributions", W, styles)
    team_rows = [
        ["Sandilya Chimalamarri",
         "ML Research Lead",
         "Sentence-transformer + FAISS pipeline (10–20ms); hybrid ranking algorithm (+23% recall); "
         "shopping list aggregation engine (95%+ accuracy)"],
        ["Sai Priyanka Bonkuri",
         "Graph DB Architect",
         "Neo4j schema design; context-aware substitution graph; traversal optimisation "
         "(3× speed-up); 92% substitution user satisfaction"],
        ["Pavan Charith Devarapalli",
         "Backend Systems Engineer",
         "FastAPI async architecture; REST API design; Locust load testing "
         "(100+ RPS, &lt;80ms p95); deployment and DevOps"],
        ["Sai Dheeraj Gollu",
         "Data Pipeline Engineer",
         "ETL pipelines for 100K+ recipes; SpaCy NER filtering (87% precision); "
         "FAISS embedding compilation; graph bootstrap orchestration"],
    ]
    story.append(make_table(
        ["Name", "Role", "Key Contributions"],
        team_rows,
        [1.7 * inch, 1.5 * inch, 3.3 * inch]
    ))
    story.append(sp(4))
    story.append(Paragraph("Table 14 — Team member contributions", styles['caption']))

    # ─── 12. CONCLUSION ──────────────────────────────────────────────────────
    story += h2("12. Conclusion", W, styles)
    story.append(body(
        "PlatePlanner demonstrates that a carefully composed polyglot architecture — combining "
        "relational, graph, vector, and key-value storage — can power a user-facing AI "
        "application that is simultaneously <i>fast</i> (sub-80ms end-to-end), <i>accurate</i> "
        "(92–95% on key metrics), and <i>memory-efficient</i> (90 MB FAISS index covering "
        "2.2M recipes). The hybrid semantic + discrete ranking algorithm and context-aware "
        "Neo4j substitution graph are the two key technical contributions beyond off-the-shelf "
        "components.", styles
    ))
    story.append(body(
        "Future directions include fine-tuning the recipe encoder on user interaction data, "
        "adding real-time inventory tracking via barcode scan, and expanding the substitution "
        "graph with crowd-sourced feedback loops.", styles
    ))

    # ─── BACK PAGE ────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 2.0 * inch))
    story.append(Paragraph(
        "PlatePlanner",
        ParagraphStyle('bp_title', fontSize=22, textColor=PRIMARY,
                       fontName='Helvetica-Bold', alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 10))
    story.append(rule(W, ACCENT, 2))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "San Jose State University · CMPE 295B · April 2026",
        ParagraphStyle('bp_sub', fontSize=10, textColor=GREY_TEXT, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Sandilya Chimalamarri · Sai Priyanka Bonkuri · "
        "Pavan Charith Devarapalli · Sai Dheeraj Gollu",
        ParagraphStyle('bp_team', fontSize=9, textColor=GREY_TEXT, alignment=TA_CENTER)
    ))

    return story


# ── Build PDF ────────────────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.55 * inch,
        title="PlatePlanner Technical Report",
        author="SJSU CMPE 295B Team",
        subject="AI-Powered Meal Planning System",
    )

    styles = build_styles()
    page_width = letter[0] - 1.5 * inch   # usable width

    story = build_story(styles, page_width)

    # First page uses cover_page template (no header/footer), rest use header_footer
    def on_page(canvas, doc):
        if doc.page == 1:
            cover_page(canvas, doc)
        else:
            header_footer(canvas, doc)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
