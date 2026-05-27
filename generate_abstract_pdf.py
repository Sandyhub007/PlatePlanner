from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

OUTPUT_PATH = "/Users/sandilyachimalamarri/Plateplanner/Fa25-4 Abstract.pdf"

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=letter,
    leftMargin=1.25 * inch,
    rightMargin=1.25 * inch,
    topMargin=1.25 * inch,
    bottomMargin=1.25 * inch,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title",
    parent=styles["Normal"],
    fontName="Times-Bold",
    fontSize=14,
    leading=18,
    alignment=TA_CENTER,
    spaceAfter=6,
)

authors_style = ParagraphStyle(
    "Authors",
    parent=styles["Normal"],
    fontName="Times-Roman",
    fontSize=11,
    leading=15,
    alignment=TA_CENTER,
    spaceAfter=4,
)

label_style = ParagraphStyle(
    "Label",
    parent=styles["Normal"],
    fontName="Times-Bold",
    fontSize=11,
    leading=14,
    alignment=TA_CENTER,
    spaceAfter=6,
    spaceBefore=18,
)

abstract_style = ParagraphStyle(
    "Abstract",
    parent=styles["Normal"],
    fontName="Times-Roman",
    fontSize=11,
    leading=16,
    alignment=TA_JUSTIFY,
    firstLineIndent=0,
)

story = []

# Title
story.append(Paragraph(
    "Plate Planner: An AI-Powered Graph-Enhanced Meal Planning<br/>and Recipe Recommendation System",
    title_style
))

story.append(Spacer(1, 0.15 * inch))

# Team members
story.append(Paragraph(
    "Sandilya Chimalamarri, Sai Priyanka Bonkuri, Pavan Charith Devarapalli, Sai Dheeraj Gollu",
    authors_style
))

story.append(Paragraph(
    "San José State University — CMPE 295B Master's Project",
    authors_style
))

# Abstract label
story.append(Paragraph("Abstract", label_style))

# Abstract body
abstract_text = (
    "Real-world meal planning requires balancing competing objectives that extend far beyond "
    "returning relevant recipes for a single query. Users must account for what ingredients are "
    "already available in their pantry, minimize the cost of acquiring new items, reduce food waste "
    "from unused perishables, and ensure that ingredient substitutions are feasible when exact "
    "matches are unavailable. Existing recipe retrieval systems predominantly optimize for "
    "single-recipe relevance, neglecting these week-level planning constraints. In this paper, we "
    "present PlatePlanner, a graph-augmented, pantry-aware semantic retrieval framework that selects "
    "multi-day meal plans while maximizing semantic relevance and minimizing incremental shopping "
    "burden and waste. Our architecture integrates a four-stage hybrid retrieval pipeline: (1) "
    "FAISS-based semantic search using SentenceTransformer embeddings over a corpus of 100K+ "
    "recipes, (2) Neo4j graph-based ontology filtering with context-aware ingredient substitution, "
    "(3) nutrient-aware mathematical ranking, and (4) retrieval-augmented generation (RAG) for "
    "explainable recommendations. Experimental evaluation demonstrates sub-100ms p95 latency, 92% "
    "user satisfaction for substitutions, 23% recall improvement over direct-only substitution, and "
    "85% user preference for hybrid scoring."
)

story.append(Paragraph(abstract_text, abstract_style))

doc.build(story)
print(f"PDF successfully created: {OUTPUT_PATH}")
