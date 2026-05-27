"""
PlatePlanner — Models & Recipe Generation Report
Generates a detailed technical PDF on ingredient breakdown and recipe generation.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Flowable

# ── Colors ───────────────────────────────────────────────────────────────────
PRIMARY    = HexColor("#1B4F72")
ACCENT     = HexColor("#2E86AB")
LIGHT_BG   = HexColor("#EBF5FB")
DARK_BG    = HexColor("#154360")
GREY_TEXT  = HexColor("#566573")
LIGHT_GREY = HexColor("#F2F3F4")
GREEN      = HexColor("#1E8449")
ORANGE     = HexColor("#D35400")
CODE_BG    = HexColor("#F0F3F4")
CODE_FG    = HexColor("#1A5276")

OUTPUT = "/Users/sandilyachimalamarri/Plateplanner/PlatePlanner_Models_Report.pdf"

# ── Custom Flowables ──────────────────────────────────────────────────────────
class SectionBanner(Flowable):
    def __init__(self, text, width, bg=PRIMARY, fg=white, size=13):
        Flowable.__init__(self)
        self.text = text; self.width = width
        self.bg = bg; self.fg = fg; self.size = size
        self.height = size + 14

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", self.size)
        c.drawString(10, 4, self.text)

class AccentRule(Flowable):
    def __init__(self, width, color=ACCENT, thickness=2):
        Flowable.__init__(self)
        self.width = width; self.color = color
        self.thickness = thickness; self.height = thickness

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

class StepBox(Flowable):
    """Numbered step with colored circle badge."""
    def __init__(self, number, text, width, styles):
        Flowable.__init__(self)
        self.number = str(number); self.text = text
        self.width = width; self.styles = styles
        self.height = 32

    def draw(self):
        c = self.canv
        # Circle
        c.setFillColor(ACCENT)
        c.circle(14, 14, 12, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(14, 10, self.number)
        # Text
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica", 9)
        c.drawString(34, 10, self.text)

# ── Styles ────────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    s = {}
    s['cover_title'] = ParagraphStyle('ct', parent=base['Title'],
        fontSize=28, leading=34, textColor=white,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=6)
    s['cover_sub'] = ParagraphStyle('cs', parent=base['Normal'],
        fontSize=12, leading=17, textColor=HexColor("#AED6F1"), alignment=TA_CENTER)
    s['cover_meta'] = ParagraphStyle('cm', parent=base['Normal'],
        fontSize=9.5, textColor=HexColor("#D6EAF8"), alignment=TA_CENTER, spaceBefore=3)
    s['h2'] = ParagraphStyle('h2', parent=base['Heading2'],
        fontSize=12, leading=15, textColor=ACCENT,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=4)
    s['h3'] = ParagraphStyle('h3', parent=base['Heading3'],
        fontSize=10.5, leading=14, textColor=PRIMARY,
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=3)
    s['body'] = ParagraphStyle('body', parent=base['Normal'],
        fontSize=9.5, leading=14, textColor=HexColor("#2C3E50"),
        alignment=TA_JUSTIFY, spaceAfter=5)
    s['bullet'] = ParagraphStyle('bul', parent=base['Normal'],
        fontSize=9.5, leading=14, textColor=HexColor("#2C3E50"),
        leftIndent=16, bulletIndent=4, spaceAfter=3)
    s['code'] = ParagraphStyle('code', parent=base['Code'],
        fontSize=7.8, leading=11.5, textColor=CODE_FG,
        backColor=CODE_BG, leftIndent=10, rightIndent=10,
        borderPad=5, fontName='Courier', spaceAfter=6)
    s['caption'] = ParagraphStyle('cap', parent=base['Normal'],
        fontSize=7.8, leading=11, textColor=GREY_TEXT,
        alignment=TA_CENTER, spaceAfter=8)
    s['label'] = ParagraphStyle('lbl', parent=base['Normal'],
        fontSize=8, textColor=GREY_TEXT, alignment=TA_CENTER)
    s['value'] = ParagraphStyle('val', parent=base['Normal'],
        fontSize=18, fontName='Helvetica-Bold', textColor=PRIMARY,
        alignment=TA_CENTER)
    s['formula'] = ParagraphStyle('form', parent=base['Normal'],
        fontSize=10, leading=14, textColor=PRIMARY,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
        backColor=LIGHT_BG, borderPad=8, spaceAfter=8, spaceBefore=6)
    return s

# ── Page callbacks ────────────────────────────────────────────────────────────
def on_cover(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#1A6A9A"))
    canvas.rect(0, h * 0.55, w, h * 0.45, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h * 0.54, w, 5, fill=1, stroke=0)
    canvas.restoreState()

def on_page(canvas, doc):
    if doc.page == 1:
        on_cover(canvas, doc)
        return
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, h - 36, w, 36, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(36, h - 22, "PlatePlanner — Models & Recipe Generation")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 36, h - 22, "Technical Deep Dive")
    canvas.setFillColor(HexColor("#BFC9CA"))
    canvas.rect(0, 0, w, 28, fill=1, stroke=0)
    canvas.setFillColor(GREY_TEXT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(36, 9, "San Jose State University · CMPE 295B")
    canvas.drawRightString(w - 36, 9, f"Page {doc.page}")
    canvas.restoreState()

# ── Helpers ───────────────────────────────────────────────────────────────────
def banner(text, W): return [Spacer(1,6), SectionBanner(text, W), Spacer(1,6)]
def h3(t, s): return Paragraph(t, s['h3'])
def body(t, s): return Paragraph(t, s['body'])
def bul(t, s): return Paragraph(f"<bullet>&bull;</bullet> {t}", s['bullet'])
def code(t, s): return Paragraph(t.replace('\n','<br/>').replace(' ','&nbsp;'), s['code'])
def sp(n=8): return Spacer(1, n)
def rule(w): return AccentRule(w)
def caption(t, s): return Paragraph(t, s['caption'])
def formula(t, s): return Paragraph(t, s['formula'])

def tbl(headers, rows, widths, caption_text=None, s=None):
    data = [headers] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_GREY]),
        ('TOPPADDING', (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.4, HexColor("#BFC9CA")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    items = [t]
    if caption_text and s:
        items += [sp(3), caption(caption_text, s)]
    return items

def metrics_row(items, s, W):
    cells = [[
        Paragraph(v, ParagraphStyle('mv', fontSize=18, fontName='Helvetica-Bold',
                  textColor=c, alignment=TA_CENTER)),
        Paragraph(l, ParagraphStyle('ml', fontSize=8, textColor=GREY_TEXT, alignment=TA_CENTER))
    ] for l, v, c in items]
    n = len(items)
    t = Table([cells], colWidths=[W/n]*n)
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, HexColor("#AED6F1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, HexColor("#AED6F1")),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    return t

# ── Story ─────────────────────────────────────────────────────────────────────
def story(s, W):
    S = []

    # ── COVER ──────────────────────────────────────────────────────────────
    S += [Spacer(1, 1.5*inch),
          Paragraph("PlatePlanner", s['cover_title']), sp(8),
          Paragraph("Models, Ingredient Breakdown &amp; Recipe Generation", s['cover_sub']),
          sp(16), AccentRule(W, white, 1), sp(12),
          Paragraph("A deep-dive into the ML pipeline — from raw ingredient text to ranked recipe results", s['cover_meta']),
          sp(6),
          Paragraph("San Jose State University · CMPE 295B · April 2026", s['cover_meta']),
          PageBreak()]

    # ── 1. OVERVIEW ────────────────────────────────────────────────────────
    S += banner("1. System Overview", W)
    S.append(body(
        "PlatePlanner's recommendation engine is not a single model — it is a <b>multi-stage "
        "pipeline</b> where each component handles the part of the problem it is best suited for. "
        "SpaCy parses raw text at ingest time, a sentence-transformer handles semantic similarity "
        "at query time, a discrete overlap function handles exact ingredient matching, Neo4j "
        "enforces dietary safety, and an LLM fires only as a last resort to synthesise "
        "novel recipes when the corpus falls short.", s))
    S.append(sp(8))
    S.append(metrics_row([
        ("Recipes Indexed", "2.2M+", PRIMARY),
        ("Embedding Dims", "384", ACCENT),
        ("FAISS Latency", "&lt;20ms", GREEN),
        ("Recall Boost", "+23%", GREEN),
        ("LLM Providers", "3", ORANGE),
    ], s, W))
    S.append(sp(4))
    S.append(caption("Key pipeline statistics", s))

    # ── 2. INGREDIENT BREAKDOWN ────────────────────────────────────────────
    S += banner("2. Ingredient Breakdown", W)
    S.append(body(
        "Before any ML model sees an ingredient, it passes through two preprocessing stages: "
        "<b>normalization</b> (at query time) and <b>Named Entity Recognition</b> (at ingest time).", s))

    S.append(h3("2.1  Text Normalization  (ingredient_normalizer.py)", s))
    S.append(body(
        "Every ingredient string — whether from a user query or stored recipe — is cleaned by "
        "the same normalization pipeline:", s))
    norm_rows = [
        ["Input", '"1 cup diced tomatoes"'],
        ["Lowercase + strip non-alpha", '"1 cup diced tomatoes"'],
        ["WordNinja split", '["1","cup","diced","tomatoes"]'],
        ["Remove units", 'cup, tbsp, oz, ml, lb, tsp … → dropped'],
        ["Remove descriptors", 'diced, chopped, minced, sliced … → dropped'],
        ["Remove stopwords / blacklist", 'of, fresh, large, small … → dropped'],
        ["Result", '"tomato"'],
    ]
    S += tbl(["Stage", "Value"], norm_rows, [2.2*inch, 4.3*inch],
             "Table 1 — Normalization pipeline for '1 cup diced tomatoes'", s)

    S.append(h3("2.2  Named Entity Recognition  (SpaCy en_core_web_sm)", s))
    S.append(body(
        "SpaCy NER runs <b>once during data ingestion</b> across all 2.2M recipes. "
        "The parsed ingredient tokens are stored in the <code>ner</code> column of the "
        "SQLite database so query-time lookup requires only a fast <code>literal_eval()</code> "
        "rather than live NLP inference.", s))
    for b in [
        "<b>87% precision</b> on 1.5M unstructured ingredient strings",
        "<b>82% recall</b> on the same evaluation set",
        "Handles fractions, unicode vulgar fractions (½ ¾ ⅓), ranges (1–2 cups)",
        "Strips brand names, preparation notes, temperature hints",
    ]:
        S.append(bul(b, s))

    S.append(h3("2.3  Fuzzy Ingredient Matching  (ingredient_matcher.py)", s))
    S.append(body(
        "For shopping list consolidation and pantry matching, a three-level similarity check "
        "resolves ingredient name variants:", s))
    fuzz_rows = [
        ["1. Exact match", "After normalization — fastest path"],
        ["2. Synonym lookup", "Hardcoded dict: tomato ↔ tomatoes ↔ cherry tomato ↔ roma tomato"],
        ["3. Fuzzy ratio", "Max of fuzz.ratio, partial_ratio, token_sort_ratio ≥ 85%"],
    ]
    S += tbl(["Check", "Logic"], fuzz_rows, [1.4*inch, 5.1*inch],
             "Table 2 — Three-level ingredient similarity check", s)

    # ── 3. EMBEDDING MODEL ─────────────────────────────────────────────────
    S += banner("3. Semantic Embedding Model", W)
    S.append(body(
        "The semantic similarity backbone is <b>all-MiniLM-L6-v2</b> from the "
        "sentence-transformers library. At query time the user's ingredient list is joined "
        "into a single string and encoded into a 384-dimensional dense vector.", s))

    model_rows = [
        ["Model", "all-MiniLM-L6-v2 (base) / finetuned-recipe-encoder (if present)"],
        ["Output dimension", "384-d float32 dense vector"],
        ["Normalization", "L2-normalized before FAISS search (enables cosine similarity via dot product)"],
        ["Hardware", "CPU inference, ~30–50ms per query"],
        ["Auto-selection", "Checks for finetuned path first; falls back to base model"],
    ]
    S += tbl(["Property", "Value"], model_rows, [1.8*inch, 4.7*inch],
             "Table 3 — Sentence-transformer model properties", s)

    S.append(h3("3.1  Query Encoding  (step-by-step)", s))
    S.append(code(
        'query = " ".join(ingredients)          # ["butter","sugar","flour"] → "butter sugar flour"\n'
        'query_vec = model.encode([query])       # shape: (1, 384)\n'
        'faiss.normalize_L2(query_vec)           # L2 norm → cosine similarity via inner product', s))

    S.append(h3("3.2  Fine-tuned Recipe Encoder  (optional)", s))
    S.append(body(
        "If a fine-tuned domain model is present at "
        "<code>src/data/models/recipe_suggestion/finetuned-recipe-encoder/</code>, "
        "it is loaded automatically. This model is adapted on food/recipe text and "
        "produces embeddings that better capture culinary concepts "
        "(e.g., 'braise' and 'slow-cook' map closer together than in the general model). "
        "A matching fine-tuned FAISS index "
        "(<code>recipe_index_finetuned_opt.faiss</code>) is also used when available.", s))

    # ── 4. FAISS INDEX ─────────────────────────────────────────────────────
    S.append(PageBreak())
    S += banner("4. FAISS Vector Index", W)
    S.append(body(
        "All 2.2M recipe embeddings are stored in a <b>FAISS IVF-PQ</b> (Inverted File + "
        "Product Quantization) index. This is the key engineering decision that makes the "
        "system practical: it reduces memory from ~12 GB (flat exact index) to ~90 MB while "
        "keeping query latency under 20ms.", s))

    faiss_rows = [
        ["Index type", "IVF-PQ (Inverted File Index + Product Quantization)"],
        ["File", "recipe_index_opt.faiss"],
        ["Size on disk", "~90 MB (vs ~12 GB for flat exact index)"],
        ["Vectors indexed", "2,231,150 recipe embeddings"],
        ["Query (k=500)", "&lt;20ms p95 on CPU"],
        ["Quantization", "8-bit per component; reduces RAM ×60 with minimal recall loss"],
        ["Fallback", "recipe_index.faiss (flat, exact) used for offline evaluation only"],
    ]
    S += tbl(["Property", "Value"], faiss_rows, [2.0*inch, 4.5*inch],
             "Table 4 — FAISS index properties", s)

    S.append(h3("4.1  Search Execution", s))
    S.append(code(
        'distances, indices = index.search(query_vec, k=500)   # top-500 ANN\n'
        'found_ids = [int(i) for i in indices[0] if i >= 0]    # filter invalid\n'
        '\n'
        '# Batch fetch from SQLite\n'
        'placeholders = ",".join("?" * len(found_ids))\n'
        'cursor.execute(\n'
        '    f"SELECT id, title, ingredients, directions, ner FROM recipes\n'
        '       WHERE id IN ({placeholders})",\n'
        '    found_ids\n'
        ')', s))
    S.append(body(
        "The wide net of 500 candidates is intentional — downstream filtering "
        "(dietary, overlap, deduplication) will reduce this to the final top-N, so "
        "casting broadly ensures good coverage.", s))

    # ── 5. HYBRID RANKING ──────────────────────────────────────────────────
    S += banner("5. Hybrid Ranking Algorithm", W)
    S.append(body(
        "Raw cosine similarity alone misses recipes that share many of the user's exact "
        "ingredients but differ in phrasing or cooking style. A discrete ingredient-overlap "
        "score is blended in to reward exact matches:", s))

    S.append(formula(
        "combined_score = 0.4 × cosine_similarity  +  0.6 × ingredient_overlap", s))

    S.append(h3("5.1  Cosine Similarity (semantic component, 40%)", s))
    S.append(body(
        "The FAISS distance returned for each candidate is already a normalized inner product "
        "(since both query and index vectors are L2-normalized), equivalent to cosine "
        "similarity. It captures <i>meaning</i> — 'braise short ribs' and "
        "'slow-cook beef' score close even if they share no words.", s))

    S.append(h3("5.2  Ingredient Overlap Score (discrete component, 60%)", s))
    S.append(code(
        '# Normalize user inputs\n'
        'norm_inputs = {x.lower().strip() for x in ingredients}\n'
        '\n'
        '# For each candidate recipe, count matching ingredients\n'
        'overlap_set = set()\n'
        'for r_ing in recipe_ingredient_list:\n'
        '    for u_ing in norm_inputs:\n'
        '        if u_ing in r_ing.lower():        # substring match\n'
        '            overlap_set.add(r_ing)\n'
        '            break\n'
        '\n'
        'overlap_score = len(overlap_set) / max(len(ingredients), 1)', s))

    S.append(h3("5.3  Minimum Overlap Filter", s))
    S.append(body(
        "Recipes with fewer than <b>2 matching ingredients</b> are dropped entirely "
        "before scoring. This hard cutoff eliminates semantically adjacent but "
        "ingredient-incompatible results (e.g., 'chocolate cake' appearing for a "
        "'butter lettuce' query).", s))

    rank_rows = [
        ["Semantic only", "Baseline", "0%"],
        ["Overlap only", "Misses semantic variants", "—"],
        ["Hybrid (0.4/0.6)", "Production", "+23% recall"],
    ]
    S += tbl(["Method", "Notes", "Recall vs Baseline"],
             rank_rows, [1.8*inch, 2.8*inch, 1.8*inch],
             "Table 5 — Ranking method comparison", s)

    # ── 6. DIETARY FILTERING ───────────────────────────────────────────────
    S.append(PageBreak())
    S += banner("6. Dietary Classification & Allergen Detection", W)
    S.append(body(
        "After ranking, every candidate recipe passes through a rule-based "
        "<code>DietaryClassifier</code>. No external model is needed — it uses "
        "<b>token matching with compound-ingredient exceptions</b> to avoid false positives "
        "like flagging 'coconut milk' as dairy.", s))

    S.append(h3("6.1  Classification Logic", s))
    diet_rows = [
        ["is_vegan", "No meat, poultry, seafood, dairy, eggs, honey", '"coconut milk" is vegan'],
        ["is_vegetarian", "No meat, poultry, seafood", '"fish sauce" fails; "soy sauce" passes'],
        ["is_gluten_free", "No wheat, barley, rye, malt", '"soy sauce" fails (contains wheat)'],
        ["is_dairy_free", "No milk, butter, cream, cheese, yogurt", '"coconut cream" passes'],
    ]
    S += tbl(["Tag", "Blocked tokens", "Exception example"],
             diet_rows, [1.2*inch, 2.8*inch, 2.5*inch],
             "Table 6 — Dietary tags and exception handling", s)

    S.append(h3("6.2  Allergen Detection", s))
    allergen_rows = [
        ["peanut", "peanut, peanut butter, peanut oil", "—"],
        ["tree_nut", "almond, walnut, cashew, pecan, pistachio…", "coconut (not a tree nut)"],
        ["dairy", "milk, butter, cream, cheese, yogurt…", "coconut milk, oat milk, almond milk"],
        ["gluten", "wheat, flour, bread, pasta, barley…", "rice flour, cornstarch"],
        ["soy", "soy, tofu, edamame, miso, tempeh…", "—"],
        ["shellfish", "shrimp, crab, lobster, oyster…", "—"],
        ["fish", "salmon, tuna, cod, tilapia, anchovy…", "—"],
        ["egg", "egg, eggs, mayonnaise…", "egg-free mayo"],
    ]
    S += tbl(["Allergen", "Trigger tokens (sample)", "Exceptions"],
             allergen_rows, [1.0*inch, 2.8*inch, 2.7*inch],
             "Table 7 — Allergen detection tokens and exceptions", s)

    S.append(h3("6.3  Word-Boundary Safety (Neo4j)", s))
    S.append(body(
        "In the ontology filtering stage, Neo4j Cypher uses word-boundary regex to prevent "
        "partial token matches:", s))
    S.append(code(
        '-- "nut" must not match "nutmeg" or "coconut"\n'
        'WHERE ing =~ (\'(?i).*\\\\b\' + term + \'\\\\b.*\')\n'
        '\n'
        '-- "egg" must not match "eggplant"\n'
        'WHERE ing =~ (\'(?i).*\\\\begg\\\\b.*\')', s))

    # ── 7. 3-TIER FEDERATED SEARCH ─────────────────────────────────────────
    S += banner("7. Three-Tier Federated Recipe Search", W)
    S.append(body(
        "The <code>POST /suggest_recipes</code> endpoint orchestrates three increasingly "
        "powerful (and expensive) retrieval sources. Each tier is only invoked "
        "when the previous one falls short.", s))

    tier_rows = [
        ["Tier 1", "Local FAISS", "Always", "~20ms", "2.2M recipes, fully offline"],
        ["Tier 2", "Spoonacular API", "score &lt; 0.35 OR cuisine requested OR not enough results", "~300ms", "Millions of web recipes"],
        ["Tier 3", "LLM Generation", "fewer than 2 results OR score &lt; 0.25", "~2–5s", "Synthesises novel recipes from scratch"],
    ]
    S += tbl(["Tier", "Source", "Trigger condition", "Latency", "Coverage"],
             tier_rows, [0.5*inch, 1.4*inch, 2.3*inch, 0.8*inch, 1.5*inch],
             "Table 8 — Three-tier retrieval system", s)

    S.append(h3("7.1  Deduplication Between Tiers", s))
    S.append(body(
        "Before merging local and Spoonacular results, a fuzzy title normalizer removes "
        "duplicates. Titles are lowercased, punctuation stripped, common words removed, "
        "and then compared with an 85% similarity threshold.", s))
    S.append(code(
        'def _normalize_title(title: str) -> str:\n'
        '    t = title.lower()\n'
        '    t = re.sub(r\'[^a-z0-9\\s]\', \'\', t)      # strip punctuation\n'
        '    t = re.sub(r\'\\b(the|a|an|with|and|or)\\b\', \'\', t)  # stopwords\n'
        '    return t.strip()\n'
        '\n'
        'def _is_duplicate(title, seen_titles, threshold=85):\n'
        '    norm = _normalize_title(title)\n'
        '    return any(fuzz.ratio(norm, s) >= threshold for s in seen_titles)', s))

    # ── 8. LLM GENERATION ─────────────────────────────────────────────────
    S.append(PageBreak())
    S += banner("8. LLM-Powered Recipe Generation", W)
    S.append(body(
        "When tiers 1 and 2 cannot return sufficient high-confidence results, the "
        "<b>RAGService</b> calls a large language model to synthesise a recipe from scratch. "
        "Three backends are supported with automatic provider detection:", s))

    llm_rows = [
        ["OpenAI", "OPENAI_API_KEY set", "gpt-4o-mini (default) or gpt-4", "Highest quality"],
        ["Google Gemini", "GOOGLE_API_KEY set", "gemini-2.0-flash (with fallback chain)", "Fast, free tier available"],
        ["Ollama (local)", "Default fallback", "llama3 or configurable", "Private, no cost, slower"],
    ]
    S += tbl(["Provider", "Activation", "Model", "Trade-off"],
             llm_rows, [1.1*inch, 1.5*inch, 2.1*inch, 1.8*inch],
             "Table 9 — LLM backend options", s)

    S.append(h3("8.1  Generation Prompt", s))
    S.append(body(
        "The prompt is dynamically assembled from the user's ingredients and dietary flags. "
        "A strict JSON-only instruction prevents markdown wrapping:", s))
    S.append(code(
        'prompt = (\n'
        '    f"Generate {top_n} complete recipe(s) using: {ing_str}.\\n"\n'
        '    f"Cuisine: {cuisine_str}. Dietary requirements: {dietary_str}.\\n\\n"\n'
        '    f"Return ONLY a valid JSON array. Each element must have:\\n"\n'
        '    f\'  \\"title\\": string\\n\'\n'
        '    f\'  \\"ingredients\\": array (only user\'s ingredients that are used)\\n\'\n'
        '    f\'  \\"all_ingredients\\": array (full list with quantities)\\n\'\n'
        '    f\'  \\"directions\\": string (numbered steps)\\n\'\n'
        '    f\'  \\"cuisine\\": array of strings\\n\\n\'\n'
        '    f"No markdown, no explanation — just the JSON array."\n'
        ')\n'
        '\n'
        'system = (\n'
        '    "You are a professional chef and recipe writer. "\n'
        '    "Always respond with valid, parseable JSON only."\n'
        ')', s))

    S.append(h3("8.2  Response Parsing & Fallback", s))
    S.append(code(
        'raw = await self.llm.generate(prompt, system, temperature=0.8)\n'
        '\n'
        '# Strip markdown code fences if LLM included them\n'
        'if raw.startswith("```"):\n'
        '    raw = raw.split("```")[1]\n'
        '    if raw.startswith("json"):\n'
        '        raw = raw[4:]\n'
        '\n'
        'parsed = json.loads(raw.strip())\n'
        'if not isinstance(parsed, list):\n'
        '    parsed = [parsed]', s))

    S.append(h3("8.3  LLM Result Scoring", s))
    S.append(body(
        "LLM-generated recipes are injected with fixed scores so they rank below "
        "high-confidence local results but above weak local matches:", s))
    S.append(code(
        '{\n'
        '    "semantic_score": 0.5,   # neutral\n'
        '    "overlap_score":  1.0,   # all requested ingredients were used\n'
        '    "combined_score": 0.7,   # above LLM_TRIGGER_THRESHOLD (0.25)\n'
        '    "source":         "llm"\n'
        '}', s))

    # ── 9. RECIPE ADAPTATION ───────────────────────────────────────────────
    S += banner("9. Recipe Adaptation via RAG", W)
    S.append(body(
        "Beyond generation, the RAGService also <b>adapts existing recipes</b> to meet "
        "dietary needs or work around missing ingredients. This is the 'Retrieval-Augmented "
        "Generation' component: the retrieved recipe is the context, and the LLM's job is "
        "to reason about changes.", s))

    S.append(h3("9.1  Adaptation Prompt Assembly", s))
    S.append(code(
        'context_parts = [\n'
        '    f"Recipe: {recipe_title}",\n'
        '    f"Ingredients: {\', \'.join(recipe_ingredients)}",\n'
        '    f"Directions: {recipe_directions[:500]}",\n'
        ']\n'
        'if pantry:\n'
        '    context_parts.append(f"User has: {\', \'.join(pantry)}")\n'
        'if missing_ingredients:\n'
        '    context_parts.append(f"Missing: {\', \'.join(missing_ingredients)}")\n'
        'if substitutions:\n'
        '    subs = "; ".join(f"{k} -> {v}" for k,v in substitutions.items())\n'
        '    context_parts.append(f"Suggested substitutions: {subs}")', s))

    S.append(h3("9.2  Prompt Branching by Intent", s))
    adapt_rows = [
        ["Dietary adaptation", '"dietary" param set', '"Adapt this recipe to be vegan. Explain each substitution."'],
        ["Missing ingredient workaround", '"missing_ingredients" set', '"Suggest how to adapt using what they have."'],
        ["General tips", "No specific params", '"Provide cooking tips and suggestions."'],
    ]
    S += tbl(["Mode", "Trigger", "Prompt instruction"],
             adapt_rows, [1.4*inch, 1.8*inch, 3.3*inch],
             "Table 10 — Recipe adaptation prompt branching", s)

    # ── 10. HYBRID RECOMMENDATION PIPELINE ────────────────────────────────
    S.append(PageBreak())
    S += banner("10. Hybrid Recommendation Pipeline  (Meal Plans)", W)
    S.append(body(
        "For full meal plan generation, a deeper 4-stage pipeline runs beyond the basic "
        "suggest_recipes endpoint. It layers ontology safety, nutritional fitness, "
        "and personalized explanation on top of the FAISS retrieval.", s))

    pipeline_rows = [
        ["Stage 1", "Semantic Retrieval", "FAISS returns top-100 candidates for the query"],
        ["Stage 2", "Ontology Filtering", "Neo4j Cypher removes recipes containing restricted ingredients (word-boundary safe)"],
        ["Stage 3", "Nutrient Scoring", "Fitness score = semantic_score - (calorie_distance / 500) × 0.5"],
        ["Stage 4", "Explanation Generation", "LLM writes a 2-3 sentence personalised explanation of why the top recipe fits the user"],
    ]
    S += tbl(["Stage", "Name", "What happens"],
             pipeline_rows, [0.5*inch, 1.5*inch, 4.5*inch],
             "Table 11 — Hybrid recommendation pipeline stages", s)

    S.append(h3("10.1  Nutritional Fitness Score", s))
    S.append(code(
        'def rank_by_nutrition(safe_recipes, user_goals):\n'
        '    target_cals = user_goals.get("target_calories", 600)\n'
        '\n'
        '    for recipe in safe_recipes:\n'
        '        recipe_cals = recipe.get("calories_per_serving") or 600.0\n'
        '        cal_distance   = abs(recipe_cals - target_cals)\n'
        '        cal_penalty    = min(cal_distance / 500.0, 1.0)   # normalize\n'
        '        sem_score      = recipe.get("semantic_score", 0.0)\n'
        '\n'
        '        recipe["fitness_score"] = sem_score - (cal_penalty * 0.5)\n'
        '\n'
        '    return sorted(safe_recipes, key=lambda x: x["fitness_score"], reverse=True)', s))

    S.append(h3("10.2  Explanation Prompt (RAG)", s))
    S.append(code(
        'prompt = (\n'
        '    f"Selected Recipe: {recipe[\'title\']}\\n"\n'
        '    f"Fitness Score: {recipe[\'fitness_score\']:.2f}\\n"\n'
        '    f"User Goals: {goals}\\n"\n'
        '    f"Restrictions avoided: {restrictions}\\n\\n"\n'
        '    "Write a friendly 2-3 sentence explanation to the user about why "\n'
        '    "this recipe was selected. Highlight how it respects their dietary "\n'
        '    "restrictions and aligns with their fitness/macro goals."\n'
        ')', s))

    # ── 11. END-TO-END FLOW ────────────────────────────────────────────────
    S += banner("11. End-to-End Data Flow", W)
    flow_rows = [
        ["1", "User sends POST /suggest_recipes", '{"ingredients": ["butter","sugar","flour"], "is_vegan": false}'],
        ["2", "Query embedding", '"butter sugar flour" → SentenceTransformer → 384-d vector → L2 normalize'],
        ["3", "FAISS ANN search", "index.search(query_vec, k=500) → top-500 recipe IDs + distances (<20ms)"],
        ["4", "SQLite batch fetch", "SELECT id, title, ingredients, directions, ner FROM recipes WHERE id IN (...)"],
        ["5", "Ingredient parse", "literal_eval(ner_field) → list of pre-parsed ingredient tokens"],
        ["6", "Overlap scoring", "Substring match of user inputs vs recipe tokens → overlap_score"],
        ["7", "Hybrid score", "0.4 × cosine_sim + 0.6 × overlap → combined_score; drop if < 2 matches"],
        ["8", "Dietary classification", "DietaryClassifier.classify(ingredients) → tags + allergens"],
        ["9", "Hard filter", "Drop recipes violating requested dietary restrictions"],
        ["10", "Tier 2 decision", "If max_score < 0.35 or results < top_n → call Spoonacular API"],
        ["11", "Deduplication", "Fuzzy title matching; merge local + external; sort by combined_score"],
        ["12", "Tier 3 decision", "If results < 2 or max_score < 0.25 → call LLM to generate recipes"],
        ["13", "Final sort & rank", "Sort by combined_score desc; assign ranks 1..N"],
        ["14", "Return", "List[RecipeResult] with scores, tags, source, ingredients, directions"],
    ]
    S += tbl(["#", "Stage", "Detail"],
             flow_rows, [0.3*inch, 1.8*inch, 4.4*inch],
             "Table 12 — Complete end-to-end data flow", s)

    # ── 12. CONFIGURATION REFERENCE ───────────────────────────────────────
    S += banner("12. Configuration Reference", W)
    cfg_rows = [
        ["BASE_MODEL_NAME", "all-MiniLM-L6-v2", "Sentence-transformer base model"],
        ["FINETUNED_MODEL_PATH", "src/data/models/.../finetuned-recipe-encoder", "Domain-tuned model (optional)"],
        ["OPT_INDEX_PATH", "recipe_index_opt.faiss", "IVF-PQ quantised FAISS index"],
        ["raw_k", "500", "ANN search width before filtering"],
        ["min_overlap", "2", "Minimum ingredient matches to keep a recipe"],
        ["rerank_weight", "0.6", "Overlap fraction in combined_score (0.4 goes to semantic)"],
        ["LOCAL_CONFIDENCE_THRESHOLD", "0.35", "Trigger Spoonacular if below"],
        ["LLM_TRIGGER_THRESHOLD", "0.25", "Trigger LLM generation if below"],
        ["Deduplication threshold", "85%", "Fuzzy title similarity cutoff"],
        ["Calorie penalty divisor", "500 kcal", "Max acceptable calorie deviation"],
        ["LLM temperature", "0.8", "Recipe generation creativity"],
    ]
    S += tbl(["Parameter", "Default", "Effect"],
             cfg_rows, [2.2*inch, 2.0*inch, 2.3*inch],
             "Table 13 — Key tunable parameters", s)

    # ── BACK PAGE ──────────────────────────────────────────────────────────
    S.append(PageBreak())
    S.append(Spacer(1, 2.2*inch))
    S.append(Paragraph("PlatePlanner",
        ParagraphStyle('bpt', fontSize=22, textColor=PRIMARY,
                       fontName='Helvetica-Bold', alignment=TA_CENTER)))
    S.append(sp(10))
    S.append(AccentRule(W, ACCENT, 2))
    S.append(sp(10))
    S.append(Paragraph("Models, Ingredient Breakdown & Recipe Generation",
        ParagraphStyle('bps', fontSize=10, textColor=GREY_TEXT, alignment=TA_CENTER)))
    S.append(sp(6))
    S.append(Paragraph("San Jose State University · CMPE 295B · April 2026",
        ParagraphStyle('bpm', fontSize=9, textColor=GREY_TEXT, alignment=TA_CENTER)))

    return S

# ── Build ─────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.85*inch, bottomMargin=0.55*inch,
        title="PlatePlanner — Models & Recipe Generation",
        author="SJSU CMPE 295B Team",
    )
    s = make_styles()
    W = letter[0] - 1.5*inch
    doc.build(story(s, W), onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {OUTPUT}")

if __name__ == "__main__":
    build()
