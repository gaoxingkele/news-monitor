"""Convert Markdown comparison reports to PDF using fpdf2 with CJK support."""
from __future__ import annotations

import os
import re
import sys
import warnings
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fpdf import FPDF

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
REPORTS = [
    ("output/reports/search_comparison_uy.md", "output/reports/search_comparison_uy.pdf"),
    ("output/reports/search_comparison_py.md", "output/reports/search_comparison_py.pdf"),
]


def md_to_pdf(md_path: str, pdf_path: str) -> None:
    content = Path(md_path).read_text(encoding="utf-8")
    lines = content.split("\n")

    pdf = FPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=12)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            pdf.add_font("CJK", "", FONT_PATH, uni=True)
        except TypeError:
            pdf.add_font("CJK", "", FONT_PATH)

    pdf.add_page()

    # Table state
    in_table = False
    table_rows: list[list[str]] = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        # Calculate column widths
        n_cols = max(len(r) for r in table_rows)
        usable = pdf.w - pdf.l_margin - pdf.r_margin
        col_w = usable / n_cols if n_cols else usable

        # Render header
        if table_rows:
            pdf.set_font("CJK", size=8)
            pdf.set_fill_color(230, 230, 230)
            for cell in table_rows[0]:
                pdf.cell(col_w, 5, cell.strip(), border=1, fill=True, align="C")
            pdf.ln()

        # Render data rows (skip separator row)
        pdf.set_fill_color(255, 255, 255)
        for row in table_rows[1:]:
            if all(c.strip().replace("-", "").replace("|", "") == "" for c in row):
                continue  # skip separator
            for i, cell in enumerate(row):
                align = "L" if i == 0 else "C"
                pdf.cell(col_w, 5, cell.strip(), border=1, align=align)
            pdf.ln()

        pdf.ln(2)
        in_table = False
        table_rows = []

    for line in lines:
        stripped = line.strip()

        # Table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip pure separator rows like |---|---|
            if all(re.match(r"^[:\-]+$", c) for c in cells):
                in_table = True
                continue
            table_rows.append(cells)
            in_table = True
            continue
        elif in_table:
            flush_table()

        # Headings
        if stripped.startswith("# ") and not stripped.startswith("## "):
            pdf.set_font("CJK", size=16)
            pdf.multi_cell(0, 9, stripped[2:], align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        elif stripped.startswith("## "):
            pdf.ln(2)
            pdf.set_font("CJK", size=12)
            pdf.set_fill_color(240, 240, 240)
            pdf.multi_cell(0, 7, stripped[3:], align="L", new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.ln(2)
        elif stripped.startswith("### "):
            pdf.ln(1)
            pdf.set_font("CJK", size=10)
            pdf.multi_cell(0, 6, stripped[4:], align="L", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif stripped.startswith("---"):
            y = pdf.get_y()
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(2)
        elif stripped == "":
            pdf.ln(1)
        elif stripped.startswith("- "):
            pdf.set_font("CJK", size=8)
            pdf.set_x(pdf.l_margin + 3)
            pdf.multi_cell(0, 4.5, "• " + stripped[2:], new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("  http"):
            # URL under a bullet point
            pdf.set_font("CJK", size=7)
            pdf.set_text_color(30, 100, 200)
            pdf.set_x(pdf.l_margin + 6)
            pdf.multi_cell(0, 4, stripped, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        elif stripped.startswith("http"):
            pdf.set_font("CJK", size=7)
            pdf.set_text_color(30, 100, 200)
            pdf.multi_cell(0, 4, stripped, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        elif stripped.startswith("**") and stripped.endswith("**"):
            # Bold line
            text = stripped.strip("*")
            pdf.set_font("CJK", size=9)
            pdf.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("> "):
            pdf.set_font("CJK", size=8)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(0, 4.5, stripped[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        else:
            # Clean markdown bold markers for plain text
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
            pdf.set_font("CJK", size=9)
            pdf.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")

    # Flush any remaining table
    if in_table:
        flush_table()

    pdf.output(pdf_path)
    print(f"PDF written: {pdf_path}")


if __name__ == "__main__":
    for md, pdf in REPORTS:
        if Path(md).exists():
            print(f"\nConverting {md} ...")
            md_to_pdf(md, pdf)
        else:
            print(f"Not found: {md}")
