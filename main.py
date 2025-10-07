import fitz  # PyMuPDF
import pandas as pd
import os
import re
from typing import List, Dict, Any, Optional, Tuple

# -----------------------------
# Heuristics and utilities
# -----------------------------

CURRENCY_RE = re.compile(r"(?i)(₹|rs\.?|inr)\s*")
PRICE_RE = re.compile(r"(?i)(₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)")
SKU_RE = re.compile(r"(?i)(?:sku|item code|code|model)[:\s-]*([A-Z0-9][A-Z0-9\-_/]{2,})")
POSSIBLE_UNIT_RE = re.compile(r"(?i)\b(ml|l|litre|g|kg|pcs?|pack|set|cm|mm|inch|in|ft|m)\b")


def sanitize_filename(name: str) -> str:
    name = name.strip()
    # Replace invalid path characters for Windows
    return re.sub(r'[<>:"/\\|?*]+', '_', name)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _normalize_price_str(s: str) -> Tuple[Optional[str], Optional[float]]:
    m = PRICE_RE.search(s)
    if not m:
        return None, None
    currency = m.group(1).upper().replace('.', '') if m.group(1) else None
    raw = m.group(2)
    try:
        price = float(raw.replace(',', ''))
    except Exception:
        price = None
    return currency, price


def parse_text_block_to_products(text: str) -> List[Dict[str, Any]]:
    """
    Heuristically parse a text block into product rows with variants/prices.
    Returns a list of dicts possibly with repeated product_name but different variants.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    # Guess product name as the first non-price-heavy line
    product_name = None
    sku = None
    description_lines: List[str] = []

    for ln in lines[:5]:  # inspect first few lines for name / sku
        sku_match = SKU_RE.search(ln)
        if sku_match and not sku:
            sku = sku_match.group(1).strip()
        # Consider a name line if it has letters and not mostly numbers
        if product_name is None:
            if len(re.findall(r"[A-Za-z]", ln)) >= 3 and len(re.findall(r"[0-9]", ln)) <= len(ln) / 2:
                # Avoid lines that look like table headers
                if not re.search(r"(?i)price|mrp|size|variant|qty|quantity", ln):
                    product_name = ln

    if product_name is None:
        # fallback to the first line
        product_name = lines[0]

    # Collect variant-price pairs from lines
    rows: List[Dict[str, Any]] = []
    for ln in lines:
        # Gather description lines that are not obviously price lines
        if not PRICE_RE.search(ln):
            description_lines.append(ln)

        currency, price = _normalize_price_str(ln)
        if price is None:
            continue

        # Try to extract a variant from the line (part excluding price)
        # Examples: "250g - 199", "Large 499", "Red / M 549"
        variant = ln
        # Remove currency/price portion from variant text for cleanliness
        variant = PRICE_RE.sub('', variant).strip(" -:\t")
        # Further clean multiple spaces
        variant = re.sub(r"\s{2,}", " ", variant)

        unit = None
        m_unit = POSSIBLE_UNIT_RE.search(variant)
        if m_unit:
            unit = m_unit.group(1)

        rows.append({
            "product_name": product_name,
            "sku": sku,
            "variant": variant if variant else None,
            "unit": unit,
            "price": price,
            "currency": currency or None,
            # description will be pruned later to a short snippet
            "description": None,
        })

    # If no price rows were detected, yield one row with just name / sku / description
    if not rows:
        desc = " ".join(lines)
        rows.append({
            "product_name": product_name,
            "sku": sku,
            "variant": None,
            "unit": None,
            "price": None,
            "currency": None,
            "description": desc[:400],
        })
    else:
        # Fill common description with first 2-3 lines as snippet
        desc_snippet = " ".join(description_lines[:3])[:400]
        for r in rows:
            r["description"] = desc_snippet

    return rows


def extract_data_from_pdf(pdf_path: str, output_dir: str) -> Optional[str]:
    """
    Extracts product-like rows and images from a PDF and saves per-PDF CSV.
    Returns CSV path or None if nothing found.
    """
    # Create output directory for the current PDF
    pdf_filename = sanitize_filename(os.path.splitext(os.path.basename(pdf_path))[0].strip())
    pdf_output_dir = os.path.join(output_dir, pdf_filename)
    images_dir = os.path.join(pdf_output_dir, "images")
    ensure_dir(images_dir)

    doc = fitz.open(pdf_path)
    all_rows: List[Dict[str, Any]] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        # Gather blocks in reading order with positions
        try:
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])
        except Exception:
            # Fallback to raw text only
            blocks = []

        # Extract images with positions when possible
        image_entries: List[Dict[str, Any]] = []
        for b in blocks:
            if b.get("type") == 1:
                # image block
                bbox = tuple(b.get("bbox", (0, 0, 0, 0)))  # type: ignore
                xref = b.get("image")  # In PyMuPDF dict, this is often the xref
                if xref is None:
                    continue
                try:
                    base_image = doc.extract_image(int(xref))
                    img_bytes = base_image.get("image")
                    img_ext = base_image.get("ext", "png")
                    image_filename = f"p{page_num + 1}_x{xref}.{img_ext}"
                    image_path = os.path.join(images_dir, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(img_bytes)
                    image_entries.append({
                        "xref": int(xref),
                        "bbox": bbox,
                        "path": os.path.relpath(image_path, output_dir),
                    })
                except Exception:
                    # ignore image extraction errors; continue
                    continue

        # If no image blocks were found in dict, fallback to page.get_images (no positions)
        if not image_entries:
            img_list = page.get_images(full=True)
            for idx, img in enumerate(img_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image.get("image")
                    img_ext = base_image.get("ext", "png")
                    image_filename = f"p{page_num + 1}_{idx + 1}.{img_ext}"
                    image_path = os.path.join(images_dir, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(img_bytes)
                    image_entries.append({
                        "xref": int(xref),
                        "bbox": None,
                        "path": os.path.relpath(image_path, output_dir),
                    })
                except Exception:
                    continue

        # Parse text blocks into product rows
        text_blocks: List[Tuple[Tuple[float, float, float, float], str]] = []
        if blocks:
            for b in blocks:
                if b.get("type") == 0:
                    bbox = tuple(b.get("bbox", (0, 0, 0, 0)))  # type: ignore
                    # Concatenate spans / lines
                    txt_lines: List[str] = []
                    for line in b.get("lines", []) or []:
                        parts = []
                        for span in line.get("spans", []) or []:
                            t = span.get("text", "")
                            if t:
                                parts.append(t)
                        if parts:
                            txt_lines.append("".join(parts))
                    text_content = "\n".join(txt_lines).strip()
                    if text_content:
                        text_blocks.append((bbox, text_content))
        else:
            # Fallback: simple text
            text_content = page.get_text("text") or ""
            if text_content.strip():
                text_blocks.append(((0, 0, 0, 0), text_content))

        # Convert text blocks to rows
        page_rows: List[Dict[str, Any]] = []
        for bbox, text in text_blocks:
            parsed = parse_text_block_to_products(text)
            for r in parsed:
                r["page"] = page_num + 1
                r["pdf"] = os.path.basename(pdf_path)
                r["image_path"] = None  # assign below via proximity
                r["text_bbox"] = bbox
                page_rows.append(r)

        # Assign nearest image to each row based on bbox centers
        for r in page_rows:
            tb = r.get("text_bbox")
            if not tb or tb == (0, 0, 0, 0):
                # No bbox info; if any images exist on page, attach the first one
                if image_entries:
                    r["image_path"] = image_entries[0]["path"]
                continue
            tcenter = _center(tb)  # type: ignore
            best = None
            best_d = None
            for img in image_entries:
                ib = img.get("bbox")
                if not ib or ib == (0, 0, 0, 0):
                    # cannot compute distance, skip for now
                    continue
                icenter = _center(ib)  # type: ignore
                d = _distance(tcenter, icenter)
                if best_d is None or d < best_d:
                    best_d = d
                    best = img
            if best:
                r["image_path"] = best["path"]

        # Cleanup temp bbox
        for r in page_rows:
            r.pop("text_bbox", None)

        all_rows.extend(page_rows)

    doc.close()

    if not all_rows:
        return None

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(all_rows, columns=[
        "pdf", "page", "product_name", "sku", "variant", "unit", "price", "currency", "description", "image_path"
    ])
    csv_filename = f"{pdf_filename}.csv"
    csv_path = os.path.join(pdf_output_dir, csv_filename)
    ensure_dir(pdf_output_dir)
    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    except PermissionError:
        # If the file is open in another program, write to an alternative name
        alt_path = os.path.join(pdf_output_dir, f"{pdf_filename}_new.csv")
        df.to_csv(alt_path, index=False, encoding="utf-8-sig")
        csv_path = alt_path

    return csv_path


def main():
    """Process all PDFs in the ../data directory and emit one CSV per PDF."""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    ensure_dir(output_dir)

    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in the data directory.")
        return

    print(f"Found {len(pdf_files)} PDF files to process.")
    for pdf_file in pdf_files:
        pdf_path = os.path.join(data_dir, pdf_file)
        print(f"Processing {pdf_file}...")
        try:
            csv_path = extract_data_from_pdf(pdf_path, output_dir)
            if csv_path:
                print(f"Successfully created CSV: {csv_path}")
            else:
                print(f"No data extracted from {pdf_file}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")


if __name__ == "__main__":
    main()
