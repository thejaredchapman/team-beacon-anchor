"""Render EXECUTIVE-SUMMARY.md as a one-page PDF (letter). Fails if it doesn't fit on one page."""
import re
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / "EXECUTIVE-SUMMARY.md", HERE / "EXECUTIVE-SUMMARY.pdf"
INK, MUTED, TEAL, LINE = HexColor("#13222b"), HexColor("#4d5f69"), HexColor("#0d6b67"), HexColor("#c9d4d8")

title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INK)
sub = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=4)
h2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=TEAL, spaceBefore=5, spaceAfter=2)
body = ParagraphStyle("b", fontName="Helvetica", fontSize=8.3, leading=10.6, textColor=INK)
bullet = ParagraphStyle("bl", parent=body, leftIndent=11, bulletIndent=2)
cell = ParagraphStyle("c", parent=body, fontSize=7.8, leading=9.8)
sub_bullet = ParagraphStyle("sb", parent=body, leftIndent=24, bulletIndent=14)
indented = ParagraphStyle("in", parent=body, leftIndent=11)


def inline(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", s)


def build():
    lines = SRC.read_text().splitlines()
    story, table_rows = [], []
    for ln in lines + [""]:
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                table_rows.append([Paragraph(inline(c), cell) for c in cells])
            continue
        if table_rows:
            t = Table(table_rows, colWidths=[255, 255])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE), ("BACKGROUND", (0, 0), (-1, 0), HexColor("#eef4f5")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story += [t, Spacer(1, 3)]
            table_rows = []
        if not ln.strip():
            continue
        if ln.startswith("# "):
            story.append(Paragraph(inline(ln[2:]), title))
        elif ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:]), h2))
        elif re.match(r"^\d+\. ", ln):
            n, rest = ln.split(". ", 1)
            story.append(Paragraph(inline(rest), bullet, bulletText=f"{n}."))
        elif ln.startswith("- "):
            story.append(Paragraph(inline(ln[2:]), bullet, bulletText="•"))
        elif re.match(r"^\s+- ", ln):
            story.append(Paragraph(inline(ln.strip()[2:]), sub_bullet, bulletText="–"))
        elif ln.startswith("   "):
            story.append(Paragraph(inline(ln.strip()), indented))
        elif ln.startswith("**Orange County"):
            story.append(Paragraph(inline(ln), sub))
        else:
            story.append(Paragraph(inline(ln), body))
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=46, rightMargin=46, topMargin=38, bottomMargin=34,
                            title="Executive summary: IHH prototypes", author="OC Claude Impact Lab team")
    pages = []
    doc.build(story, onLaterPages=lambda c, d: pages.append(d.page), onFirstPage=lambda c, d: pages.append(d.page))
    from pypdf import PdfReader
    n = len(PdfReader(str(OUT)).pages)
    assert n == 1, f"Executive summary runs to {n} pages; shorten it."
    print("wrote", OUT.name, "(1 page)")


if __name__ == "__main__":
    build()
