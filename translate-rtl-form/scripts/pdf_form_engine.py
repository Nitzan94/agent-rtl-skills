# ABOUTME: Reusable PDF form engine — the primitives shared by translate / empty / redact tasks.
# ABOUTME: Translation-specific bits (maps, mirror flag) are passed IN; the engine itself is language/task-agnostic.
import io
import fitz
from PIL import Image

FONT = "helv"
ZOOM = 3.5


# ---- detection -------------------------------------------------------------
def classify_page(page):
    """Return (verdict, n_chars, n_images) — can the text layer be read/replaced?"""
    text = page.get_text()
    nchars = len(text.strip())
    nimgs = len(page.get_images(full=True))
    if nchars == 0:
        return ("SCANNED/no-text" if nimgs else "EMPTY"), nchars, nimgs
    if any('֐' <= c <= '׿' for c in text):
        return "UNICODE-Hebrew", nchars, nimgs
    try:
        hi = sum(1 for x in text.encode('latin1', 'ignore') if x >= 0x80)
    except Exception:
        hi = 0
    if hi > nchars * 0.15:
        return "LEGACY-codepage", nchars, nimgs
    return "CLEAN-ascii/latin", nchars, nimgs


# ---- extraction ------------------------------------------------------------
def extract_spans(page):
    """Every non-empty text span with bbox + size + font."""
    return [s for b in page.get_text("dict")["blocks"]
            for l in b.get("lines", []) for s in l["spans"] if s["text"].strip()]


def capture_logos(page):
    """(xref, rect) for each embedded image, to re-paste upright after a mirror."""
    return [(img[0], r) for img in page.get_images(full=True)
            for r in page.get_image_rects(img[0])]


# ---- the core mutation: empty the text, keep the graphics ------------------
def empty_form(page, spans):
    """Redact ONLY glyphs (fill=False) — boxes, lines, shading, logos all stay."""
    for s in spans:
        page.add_redact_annot(fitz.Rect(s["bbox"]), fill=False)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)


def rasterize(page, flip=False):
    """Picture of the (emptied) page; optionally flipped L<->R for RTL->LTR."""
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue()


# ---- placement -------------------------------------------------------------
def fit_text(text, maxw, start, floor=3.2):
    sz = start
    while sz > floor and fitz.get_text_length(text, FONT, sz) > maxw:
        sz -= 0.2
    return sz


def place_items(op, items, W, mirror, max_start=9.0):
    """items: (x0,y0,x1,y1,text,size) in ORIGINAL coords. mirror -> x'=W-x1, LTR."""
    laid = []
    for x0, y0, x1, y1, txt, sz in items:
        mx0 = (W - x1) if mirror else x0
        laid.append((mx0, y0, (W - x0) if mirror else x1, y1, txt, sz))
    mboxes = [(a, b, c, d) for a, b, c, d, _, _ in laid]
    for mx0, y0, mx1, y1, txt, sz in laid:
        ymid = (y0 + y1) / 2
        rlim = W - 14
        for bx0, by0, bx1, by1 in mboxes:
            if by0 - 1 <= ymid <= by1 + 1 and bx0 > mx0 + 2 and bx0 < rlim:
                rlim = bx0
        maxw = max(10, rlim - 2 - mx0)
        op.insert_text((mx0, y1 - 1.5), txt, fontname=FONT,
                       fontsize=fit_text(txt, maxw, min(sz, max_start)), color=(0, 0, 0))
