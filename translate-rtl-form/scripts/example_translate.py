# ABOUTME: Synthetic, runnable end-to-end demo of the form engine — empty -> mirror -> refill.
# ABOUTME: Uses a generated sample form with placeholder labels (no real PII, no font deps) to show the pipeline.
#
# Real usage: replace `build_sample()` with `fitz.open("your_source.pdf")`, classify it
# (Hebrew/Arabic/legacy/scanned) per the SKILL steps, build a DICT that maps each decoded
# source phrase -> target language, and keep mirror=True for RTL->LTR. The MECHANICS below
# (extract -> empty -> rasterize(flip) -> re-paste logos -> place_items) are exactly what a
# real translation run does; only the source and the map change.
import fitz
from pdf_form_engine import (classify_page, extract_spans, capture_logos,
                             empty_form, rasterize, place_items, span_dump,
                             mirror_rect)

OUT_BLANK = "demo_emptied.pdf"
OUT_FINAL = "demo_translated.pdf"

# A throwaway translation map. In a real run this maps decoded source phrases (Hebrew/
# Arabic, in logical order) -> target language. Here we map placeholder field labels.
DICT = {
    "SHEM":    "Name",
    "KTOVET":  "Address",
    "MISPAR":  "Employee No.",
    "SKHAR":   "Salary",
}


def build_sample(path):
    """Generate a tiny sample form: a border, two ruled rows, labels + numbers."""
    doc = fitz.open()
    page = doc.new_page(width=300, height=160)
    page.draw_rect(fitz.Rect(10, 10, 290, 150), color=(0, 0, 0), width=1)
    page.draw_line(fitz.Point(10, 50), fitz.Point(290, 50), color=(0.6, 0.6, 0.6))
    page.draw_line(fitz.Point(10, 90), fitz.Point(290, 90), color=(0.6, 0.6, 0.6))
    # label + value pairs (value is a number that must be preserved verbatim)
    page.insert_text((20, 35),  "SHEM",   fontname="helv", fontsize=11)
    page.insert_text((150, 35), "12345",  fontname="helv", fontsize=11)
    page.insert_text((20, 75),  "KTOVET", fontname="helv", fontsize=11)
    page.insert_text((150, 75), "Tel Aviv 6789", fontname="helv", fontsize=11)
    page.insert_text((20, 115), "SKHAR",  fontname="helv", fontsize=11)
    page.insert_text((150, 115), "9,500", fontname="helv", fontsize=11)
    doc.save(path)
    doc.close()


def translate(src, mirror=True):
    doc = fitz.open(src)
    out = fitz.open()
    misses = []
    for page in doc:
        W, H = page.rect.width, page.rect.height
        print("classify:", classify_page(page)[0])
        spans = extract_spans(page)
        print("spans:", len(span_dump(page)))

        # build placement items: translate label spans, pass numbers through verbatim
        items = []
        for s in spans:
            x0, y0, x1, y1 = s["bbox"]
            txt = s["text"].strip()
            if txt in DICT:
                txt = DICT[txt]
            elif txt.isalpha():           # an untranslated word -> record a MISS
                misses.append(txt)
            items.append((x0, y0, x1, y1, txt, s["size"]))

        logos = capture_logos(page)
        empty_form(page, spans)
        png = rasterize(page, flip=mirror)

        op = out.new_page(width=W, height=H)
        op.insert_image(op.rect, stream=png)
        for xref, r in logos:
            op.insert_image(mirror_rect(W, r), pixmap=fitz.Pixmap(doc, xref))
        place_items(op, items, W, mirror=mirror)

    out.save(OUT_FINAL, garbage=4, deflate=True)
    print(f"Saved {OUT_FINAL} (mirror={mirror})")
    print("MISSES:", misses or "none")


if __name__ == "__main__":
    build_sample("demo_source.pdf")
    translate("demo_source.pdf", mirror=True)
