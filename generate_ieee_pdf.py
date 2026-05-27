#!/usr/bin/env python3
"""Generate a professional IEEE-style PDF from PlatePlanner_IEEE_Paper.md using ReportLab."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Image as RLImage
import re, os

OUTPUT = "PlatePlanner_IEEE_Paper.pdf"
MD_FILE = "PlatePlanner_IEEE_Paper.md"

# ── Styles ──────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    IEEE_BLUE = colors.HexColor("#003087")
    CODE_BG   = colors.HexColor("#F4F4F4")

    s = {}
    s["title"] = ParagraphStyle("title",
        parent=base["Normal"], fontSize=16, leading=20,
        alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold",
        textColor=IEEE_BLUE)
    s["authors"] = ParagraphStyle("authors",
        parent=base["Normal"], fontSize=10, leading=14,
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica")
    s["abstract_head"] = ParagraphStyle("abstract_head",
        parent=base["Normal"], fontSize=9, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceBefore=8, spaceAfter=2, textColor=IEEE_BLUE)
    s["abstract"] = ParagraphStyle("abstract",
        parent=base["Normal"], fontSize=8.5, leading=12,
        alignment=TA_JUSTIFY, leftIndent=24, rightIndent=24,
        spaceAfter=10, fontName="Helvetica")
    s["h1"] = ParagraphStyle("h1",
        parent=base["Normal"], fontSize=10, fontName="Helvetica-Bold",
        textColor=IEEE_BLUE, spaceBefore=10, spaceAfter=4,
        alignment=TA_CENTER, borderPad=(0,0,2,0))
    s["h2"] = ParagraphStyle("h2",
        parent=base["Normal"], fontSize=9.5, fontName="Helvetica-Bold",
        textColor=IEEE_BLUE, spaceBefore=8, spaceAfter=3)
    s["h3"] = ParagraphStyle("h3",
        parent=base["Normal"], fontSize=9, fontName="Helvetica-BoldOblique",
        spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#1a5276"))
    s["body"] = ParagraphStyle("body",
        parent=base["Normal"], fontSize=9, leading=13,
        alignment=TA_JUSTIFY, spaceAfter=5, fontName="Helvetica")
    s["bullet"] = ParagraphStyle("bullet",
        parent=base["Normal"], fontSize=9, leading=13,
        leftIndent=14, bulletIndent=4, spaceAfter=2, fontName="Helvetica")
    s["code"] = ParagraphStyle("code",
        parent=base["Normal"], fontSize=7.5, fontName="Courier",
        leading=11, backColor=CODE_BG, leftIndent=12, rightIndent=12,
        spaceBefore=4, spaceAfter=4, borderColor=colors.grey, borderWidth=0.5)
    s["table_caption"] = ParagraphStyle("table_caption",
        parent=base["Normal"], fontSize=8.5, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceBefore=6, spaceAfter=4, textColor=IEEE_BLUE)
    s["ref"] = ParagraphStyle("ref",
        parent=base["Normal"], fontSize=8, leading=11,
        leftIndent=18, firstLineIndent=-18, spaceAfter=2, fontName="Helvetica")
    s["kw"] = ParagraphStyle("kw",
        parent=base["Normal"], fontSize=8.5, leading=12,
        alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Oblique")
    return s

# ── Table builder ────────────────────────────────────────────────────────────
def build_table(header, rows, caption=""):
    IEEE_BLUE = colors.HexColor("#003087")
    col_count = len(header)
    col_w = [6.5 * inch / col_count] * col_count
    data = [header] + rows
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), IEEE_BLUE),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 7.5),
        ("LEADING",      (0,0), (-1,-1), 10),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#EBF5FB")]),
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#AED6F1")),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
    ]))
    items = []
    if caption:
        items.append(Paragraph(caption, make_styles()["table_caption"]))
    items.append(t)
    items.append(Spacer(1, 6))
    return KeepTogether(items)

# ── Markdown parser → flowables ──────────────────────────────────────────────
def md_inline(text):
    """Convert inline markdown (bold, italic, code) to ReportLab HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`',       r'<font name="Courier">\1</font>', text)
    text = text.replace("&", "&amp;").replace("<b>", "<b>").replace("</b>", "</b>")
    return text

def parse_md(path, styles):
    flowables = []
    in_code = False
    code_buf = []
    in_table = False
    table_rows = []
    table_caption = ""
    pending_caption = ""
    abstract_buf = []
    in_abstract = False
    section_num = 0

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip("\n")
        stripped = raw.strip()

        # ── Code blocks ──
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                code_text = "\n".join(code_buf)
                for cl in code_text.split("\n"):
                    flowables.append(Paragraph(cl.replace(" ", "&nbsp;") or "&nbsp;", styles["code"]))
                flowables.append(Spacer(1, 4))
            i += 1
            continue
        if in_code:
            code_buf.append(raw)
            i += 1
            continue

        # ── HR ──
        if stripped.startswith("---"):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#AED6F1"), spaceAfter=4))
            i += 1
            continue

        # ── Table rows ──
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # skip separator row
            if all(re.match(r"^[-:]+$", c.replace(" ","")) for c in cells if c):
                i += 1
                continue
            table_rows.append([Paragraph(md_inline(c), ParagraphStyle("tc",
                fontName="Helvetica", fontSize=7.5, leading=10)) for c in cells])
            in_table = True
            i += 1
            continue
        else:
            if in_table and table_rows:
                header = table_rows[0]
                rows   = table_rows[1:]
                # rebuild header with bold white (done in TableStyle)
                header_plain = [Paragraph(re.sub(r'\*\*(.+?)\*\*', r'\1', 
                    (c.text if hasattr(c,'text') else str(c))),
                    ParagraphStyle("th", fontName="Helvetica-Bold",
                        fontSize=7.5, leading=10, textColor=colors.white)) for c in header]
                flowables.append(build_table(header_plain, rows, table_caption))
                table_rows = []
                in_table = False
                table_caption = ""

        # ── Headings ──
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title_text = stripped[2:]
            flowables.append(Paragraph(md_inline(title_text), styles["title"]))
            i += 1
            continue
        if stripped.startswith("## "):
            text = stripped[3:]
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(md_inline(text), styles["h1"]))
            flowables.append(HRFlowable(width="100%", thickness=1,
                color=colors.HexColor("#003087"), spaceAfter=4))
            i += 1
            continue
        if stripped.startswith("### "):
            text = stripped[4:]
            flowables.append(Paragraph(md_inline(text), styles["h2"]))
            i += 1
            continue
        if stripped.startswith("#### "):
            text = stripped[5:]
            flowables.append(Paragraph(md_inline(text), styles["h3"]))
            i += 1
            continue

        # ── Table caption (bold line before table) ──
        if re.match(r'^\*\*Table [IVX\d]+', stripped):
            table_caption = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            i += 1
            continue

        # ── Abstract detection ──
        if stripped == "## Abstract" or stripped.startswith("## Abstract"):
            in_abstract = True
            flowables.append(Paragraph("Abstract", styles["abstract_head"]))
            i += 1
            continue

        # ── Author lines ──
        if stripped.startswith("**Authors:**") or stripped.startswith("- Sandilya") or \
           stripped.startswith("- Sai Priyanka") or stripped.startswith("- Pavan") or \
           stripped.startswith("- Sai Dheeraj"):
            flowables.append(Paragraph(md_inline(stripped.lstrip("- ")), styles["authors"]))
            i += 1
            continue
        if stripped.startswith("**Advisor:**"):
            flowables.append(Paragraph(md_inline(stripped), styles["authors"]))
            flowables.append(Spacer(1, 8))
            i += 1
            continue

        # ── Keywords ──
        if stripped.startswith("**Keywords:**"):
            flowables.append(Paragraph(md_inline(stripped), styles["kw"]))
            i += 1
            continue

        # ── Bullet points ──
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            flowables.append(Paragraph("• " + md_inline(text), styles["bullet"]))
            i += 1
            continue
        if re.match(r'^\d+\. ', stripped):
            text = re.sub(r'^\d+\. ', '', stripped)
            flowables.append(Paragraph(md_inline(text), styles["bullet"]))
            i += 1
            continue

        # ── Fig captions ──
        if stripped.startswith("**Fig."):
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(md_inline(stripped), styles["table_caption"]))
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # ── Image embed placeholder ──
        if stripped.startswith("*(See generated"):
            i += 1
            continue

        # ── Empty line ──
        if not stripped:
            if in_abstract:
                pass
            else:
                flowables.append(Spacer(1, 4))
            i += 1
            continue

        # ── Regular paragraph ──
        if in_abstract:
            abstract_buf.append(stripped)
            if not lines[i+1].strip() if i+1 < len(lines) else True:
                flowables.append(Paragraph(" ".join(abstract_buf), styles["abstract"]))
                abstract_buf = []
                in_abstract = False
        else:
            flowables.append(Paragraph(md_inline(stripped), styles["body"]))

        i += 1

    return flowables

# ── Header/Footer ─────────────────────────────────────────────────────────────
class IEEEDoc(SimpleDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename,
            pagesize=letter,
            leftMargin=0.85*inch, rightMargin=0.85*inch,
            topMargin=0.9*inch, bottomMargin=0.9*inch,
        )
    def handle_pageBegin(self):
        super().handle_pageBegin()
    def afterPage(self):
        c = self.canv
        c.saveState()
        IEEE_BLUE = colors.HexColor("#003087")
        # Header bar
        c.setFillColor(IEEE_BLUE)
        c.rect(0.85*inch, letter[1]-0.72*inch, 6.8*inch, 0.02*inch, fill=1, stroke=0)
        c.setFont("Helvetica", 7)
        c.setFillColor(IEEE_BLUE)
        c.drawString(0.85*inch, letter[1]-0.68*inch,
            "PlatePlanner: AI-Powered Meal Planning with GNN-Based Ingredient Substitution")
        c.drawRightString(letter[0]-0.85*inch, letter[1]-0.68*inch,
            "CMPE 295B — San José State University, 2026")
        # Footer
        c.setFillColor(IEEE_BLUE)
        c.rect(0.85*inch, 0.65*inch, 6.8*inch, 0.02*inch, fill=1, stroke=0)
        c.setFont("Helvetica", 7)
        c.drawString(0.85*inch, 0.5*inch,
            "Chimalamarri, Bonkuri, Devarapalli, Gollu — San José State University")
        page_num = self.canv.getPageNumber()
        c.drawRightString(letter[0]-0.85*inch, 0.5*inch, f"Page {page_num}")
        c.restoreState()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    styles = make_styles()
    doc = IEEEDoc(OUTPUT)
    flowables = parse_md(MD_FILE, styles)
    doc.build(flowables, onFirstPage=lambda c,d: None, onLaterPages=lambda c,d: None)
    # Re-build with header/footer using a custom canvas
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import letter

    class Canvas2(IEEEDoc):
        pass

    doc2 = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.9*inch, bottomMargin=0.9*inch,
    )

    def on_page(canvas, doc):
        IEEE_BLUE = colors.HexColor("#003087")
        canvas.saveState()
        canvas.setFillColor(IEEE_BLUE)
        canvas.rect(0.85*inch, letter[1]-0.72*inch, 6.8*inch, 0.02*inch, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(IEEE_BLUE)
        canvas.drawString(0.85*inch, letter[1]-0.68*inch,
            "PlatePlanner: AI-Powered Meal Planning | CMPE 295B, San José State University, 2026")
        canvas.setFillColor(IEEE_BLUE)
        canvas.rect(0.85*inch, 0.62*inch, 6.8*inch, 0.02*inch, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(0.85*inch, 0.48*inch,
            "Chimalamarri · Bonkuri · Devarapalli · Gollu")
        canvas.drawRightString(letter[0]-0.85*inch, 0.48*inch,
            f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc2.build(flowables, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF saved → {OUTPUT}")

if __name__ == "__main__":
    main()
