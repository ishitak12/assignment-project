import streamlit as st
import fitz  # PyMuPDF
import camelot
import pdfplumber
import tempfile
import json
import os
from collections import defaultdict

# ---------------- Helpers ----------------

def sanitize_table(table_rows):
    """Ensure all cells are strings, no None values."""
    return [[("" if cell is None else str(cell).strip()) for cell in row] for row in table_rows]


def extract_text_and_headings(page, last_section=None, last_subsection=None):
    """Extract paragraphs, sections, and sub-sections with refined detection."""
    raw = page.get_text("dict")
    blocks = raw.get("blocks", [])
    enriched = []
    for b in blocks:
        text_parts, font_sizes, font_flags = [], [], []
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                text_parts.append(span["text"])
                font_sizes.append(span["size"])
                font_flags.append(span["flags"])
        text = " ".join(text_parts).strip()
        if not text:
            continue
        largest_font = max(font_sizes) if font_sizes else 0
        is_bold = any((f & 2) != 0 for f in font_flags)
        enriched.append({
            "text": text,
            "bbox": b.get("bbox"),
            "largest_font": largest_font,
            "is_bold": is_bold
        })

    # sort by vertical position
    enriched.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

    paragraphs = []
    for b in enriched:
        txt, lf, bold = b["text"], b["largest_font"], b["is_bold"]

        # Section heading
        if lf >= 16 or (lf >= 14 and bold):
            last_section, last_subsection = txt, None
            continue

        # Sub-section heading (heuristic: medium font, bold, or short bold text)
        if (13 <= lf < 16 or (11.5 <= lf < 13 and bold)) or (len(txt.split()) <= 4 and bold):
            last_subsection = txt
            continue

        # Normal paragraph
        paragraphs.append({
            "type": "paragraph",
            "section": last_section if last_section else "Unknown",
            "sub_section": last_subsection,
            "text": txt
        })

    return paragraphs, last_section, last_subsection


def build_table_from_words(words, y_tolerance=3, col_gap=20):
    """
    Cluster words into rows by y-position and split into columns using horizontal gaps.
    """
    if not words:
        return []

    rows = defaultdict(list)
    for w in words:
        text = w.get("text", "").strip()
        if not text:
            continue
        y = round(float(w["top"]) / y_tolerance) * y_tolerance
        rows[y].append((w["x0"], text))

    table = []
    for y in sorted(rows.keys()):
        row_words = sorted(rows[y], key=lambda x: x[0])
        row, last_x = [], None
        for x, txt in row_words:
            if last_x is not None and (x - last_x) > col_gap:
                # big gap → assume new column
                row.append("")
            row.append(txt)
            last_x = x
        table.append(row)
    return table


def extract_tables(pdf_path, page_num, last_section, last_subsection):
    """Extract tables using Camelot + pdfplumber fallback + word clustering."""
    results = []
    # --- Camelot ---
    try:
        tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="lattice")
        if len(tables) == 0:
            tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor="stream")
        for t in tables:
            rows = sanitize_table(t.df.values.tolist())
            if rows:
                results.append({
                    "type": "table",
                    "section": last_section if last_section else "Unknown",
                    "sub_section": last_subsection,
                    "description": None,
                    "table_data": rows
                })
        if results:
            return results
    except Exception:
        pass

    # --- pdfplumber extract_tables ---
    try:
        with pdfplumber.open(pdf_path) as pdf:
            ptables = pdf.pages[page_num - 1].extract_tables()
            for tb in ptables:
                rows = sanitize_table(tb)
                if rows:
                    results.append({
                        "type": "table",
                        "section": last_section if last_section else "Unknown",
                        "sub_section": last_subsection,
                        "description": None,
                        "table_data": rows
                    })
        if results:
            return results
    except Exception:
        pass

    # --- Fallback: build from words ---
    try:
        with pdfplumber.open(pdf_path) as pdf:
            words = pdf.pages[page_num - 1].extract_words(x_tolerance=2, y_tolerance=2)
            table = build_table_from_words(words)
            if table:
                results.append({
                    "type": "table",
                    "section": last_section if last_section else "Unknown",
                    "sub_section": last_subsection,
                    "description": "Reconstructed from word positions",
                    "table_data": sanitize_table(table)
                })
    except Exception:
        pass

    return results


def extract_charts(page, last_section, last_subsection):
    """Detect images; mark if none are found."""
    charts = []
    imgs = page.get_images(full=True)
    if not imgs:
        charts.append({
            "type": "chart",
            "section": last_section if last_section else "Unknown",
            "sub_section": last_subsection,
            "description": "Chart (vector or non-extractable)",
            "table_data": None
        })
    else:
        for _ in imgs:
            charts.append({
                "type": "chart",
                "section": last_section if last_section else "Unknown",
                "sub_section": last_subsection,
                "description": "Chart image detected",
                "table_data": None
            })
    return charts


def parse_pdf(pdf_path):
    """Parse PDF → JSON with sections, sub-sections, tables, and charts."""
    doc = fitz.open(pdf_path)
    pages_output = []
    last_section, last_subsection = None, None

    for page_num, page in enumerate(doc, start=1):
        page_items = []
        paragraphs, last_section, last_subsection = extract_text_and_headings(
            page, last_section, last_subsection
        )
        page_items.extend(paragraphs)

        tables = extract_tables(pdf_path, page_num, last_section, last_subsection)
        page_items.extend(tables)

        charts = extract_charts(page, last_section, last_subsection)
        page_items.extend(charts)

        pages_output.append({"page_number": page_num, "content": page_items})

    return {"pages": pages_output}


# ---------------- Streamlit UI ----------------

st.title("📄 PDF → JSON Converter (with Table Reconstruction)")
st.write("Upload a PDF to extract text, sections, sub-sections, tables, and charts into structured JSON.")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.success("✅ PDF uploaded successfully!")
    result = parse_pdf(tmp_path)

    # Show preview
    st.subheader("Extracted JSON Preview (first 2 pages)")
    st.json({"pages": result["pages"][:2]})

    # Download button
    st.download_button(
        label="⬇️ Download JSON",
        data=json.dumps(result, indent=2, ensure_ascii=False),
        file_name="output.json",
        mime="application/json"
    )

    os.remove(tmp_path)
