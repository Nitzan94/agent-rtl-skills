---
name: translate-rtl-form
description: >
  Translate filled, text-based RTL PDF forms while preserving the original boxes,
  lines, logos, and numbers. Use for Hebrew/Arabic payslips, certificates, tax
  forms, invoices, and official forms that need an English/LTR version with the same
  layout. Not for scanned PDFs, prose PDFs, or authoring new RTL documents.
---

# Translate an RTL PDF Form In Place (RTL → LTR mirror)

Translate a filled PDF form by emptying ONLY its text and refilling the translation.
The original form — boxes, shading, lines, logos, every number — stays. For a
right-to-left source (Hebrew/Arabic) going to English, MIRROR the whole layout so it
reads left-to-right (labels left, values right, columns L→R). This **edits the
original file**; it does NOT rebuild the form.

## Why this approach (and what it rejects)
Two tempting approaches are wrong, in order of temptation:
1. **Rebuild the form from scratch** (e.g. in HTML) — loses fidelity to the original;
   the output should BE the same form, not a lookalike.
2. **Translate in place at the original RTL coordinates** — English placed at RTL
   positions reads backwards. You must mirror to LTR.

The proven path: **empty the text → rasterize the emptied form → flip it L↔R →
re-paste logos upright → write the translated text on top, fitted to each cell.** The
background is a literal picture of the real form, so fidelity is guaranteed.

## Inputs
- `source`: path to the source PDF.
- `target_language`: language to translate into (default: English).

## Setup
PyMuPDF + Pillow via `uv` (no system pip needed):
```
uv run --with PyMuPDF --with pillow python <your-script>.py
```
View output with a PDF-rendering read (renders pages visually). Never trust "it ran".

## Files in this skill
- `scripts/pdf_form_engine.py` — the reusable, language-agnostic engine:
  `classify_page`, `extract_spans`, `span_dump`, `recover_legacy_text`,
  `capture_logos`, `empty_form`, `rasterize`, `fit_text`, `place_items`. Import it;
  don't reinvent it.
- `scripts/example_translate.py` — a runnable, SYNTHETIC demo of the full engine
  pipeline (build sample → classify → extract → empty → mirror-flip → refill from a
  map → report misses). It uses placeholder Latin labels and a generated form so it
  runs with no font deps or PII; the RTL encoding-detection/decoding is documented in
  the steps below. Copy it as your starting point and swap in your real source + map.

## Steps

### 1. Get the source PDF and classify it
Open it, note page count, and run `classify_page` per page:
- **Real Unicode** Hebrew (U+0590–U+05FF) / Arabic (U+0600–U+06FF) — use directly.
- **Legacy codepage read as Latin-1** (gibberish like `êåúî`) — recover with
  `t.encode('latin1').decode(cp)` where `cp` is `cp1255` (Hebrew) or `cp1256`
  (Arabic), then reverse for logical order.
- **No text + images present** → `SCANNED/no-text`: scanned / no text layer.
  **STOP and tell the user** — this skill can't do scanned PDFs (that needs OCR).
**Success**: page count known; encoding identified or scanned-PDF refusal surfaced.

### 2. Extract spans + build the translation map
Collect every text span (text + bbox + size). Start with `span_dump(page,
codepage="cp1255")` for Hebrew legacy PDFs or `span_dump(page, codepage="cp1256")`
for Arabic legacy PDFs; omit `codepage` for real Unicode PDFs. This dump gives text,
decoded text, bbox, mirrored x, font, and size for manual maps and corrections.

Classify source-language spans vs numbers. For phrase reconstruction, cluster by line
(same y, ≤3px) + small x-gap (≤14px) so header phrases merge but table columns stay
separate; reconstruct each phrase in **logical** order (RTL extraction often returns
visual/reversed order, and some PDFs glue a label and adjacent value into one span).
Map each phrase → `target_language`:
- **Map by decoded phrase → dictionary** (`DICT`) — robust; reports misses when a
  cluster has no entry. Prefer this when the form may vary.
- Map by first-seen **index** only for a frozen, known source (brittle: one
  added/removed span shifts every mapping — see gotchas).
Carry numbers embedded inside a source span into the translation. Report any
unmapped cluster under a `MISSES:` line — never drop silently.
**Success**: every cluster mapped or misses listed; print to sanity-check.

### 3. Capture logos
`capture_logos(page)` → (xref, rect) per image, so they can be re-pasted upright
after the mirror.

### 4. Empty the form
`empty_form(page, spans)` — redacts ALL glyphs with `fill=False`, keeping shaded
backgrounds, lines, and logos; removes only text.
**Success**: page has graphics + logos, no text.

### 5. Mirror the form (RTL→LTR)
`rasterize(page, flip=True)` → flipped PNG; place as the new page background. Then
re-paste each logo upright at its mirrored rect `[W-x1, y0, W-x0, y1]` (covers the
backwards copy in the raster).
**Skip the flip** (place text at original positions) only if target and source share
direction.

### 6. Refill the text (LTR, fit-to-cell)
`place_items(op, items, W, mirror=True)` places each item at mirrored x' = `W - x1`,
left-aligned, font shrunk to the gap to the nearest content on the right (floor ~3.4).
Numbers use their original text; phrases use the translation. Flowing paragraph
regions: place as whole translated text blocks (`insert_textbox`, check return ≥ 0).
**Success**: 0 misses; text reads L→R; nothing overlaps.

### 7. Enlarge if dense
If cells are too small to read, scale the finished page up (~1.5×) by drawing it onto
a larger page with `show_pdf_page`. Keeps layout + order, just bigger.

### 8. Render and VISUALLY verify — iterate
Render the output and look at every page: overlaps, missing/garbled text, displaced
numbers, untranslated spans, reversed numeric sequences (see gotchas). Fix and re-run
until clean. **Show the user before delivering.**

### 9. Deliver
Save the final PDF(s). If you deliver by email or another channel, confirm with the
owner first, and ask the reviewer to mark issues by field/page.

### 10. Review-round corrections loop
When the reviewer returns a punch-list, don't eyeball-nudge:
- **Confirm WHICH file each note is about** — disambiguate by field names/values that
  only exist on one template.
- **Dump the ground truth**: source spans sorted by (y, x) with text, bbox,
  mirrored-x `W-x1`, size; and the index→map (or decoded-phrase→map) table.
- **Classify each note**: *wording* → edit the one map string; *layout* (value in the
  wrong cell, two fields glued) → SUPPRESS the offending span(s) and re-place the
  pieces with an explicit `(text, mirrored-x, baseline-y, size)` list read off the dump.
- Re-render and visually confirm EVERY item each round before replying.

## Gotchas
- **Mirror reverses already-LTR runs.** Numeric sequences that read left-to-right in
  the source (e.g. a months header `1…12`) come out reversed (`12…1`). Detect
  purely-numeric horizontal runs and re-place them un-mirrored.
- **RTL extraction returns VISUAL (reversed) order** — re-map to logical, don't copy.
  Cross-check leave/balance rows with `prev + credit = new`.
- **Some PDFs glue label + value into one span** (for example, a Hebrew label plus an
  English or numeric value). Treat the glued string as the source key, or suppress the
  glued span and re-place the label/value manually from `span_dump`.
- **`pip` may be unavailable** — use `uv run --with ...` (no venv dance).
- **White-fill redaction punches holes in shaded headers** — use `fill=False`.
- **Target language is usually longer** than RTL source — expect to shrink fonts or
  enlarge the page. A duplicated token means a suffix is in both the translation
  string and an original number span; drop one.
- **Index-mapping is brittle.** It rests on `len(spans) == len(map)`; one added/
  removed/merged span shifts every mapping. Prefer the dictionary path when the
  source may change.
- **One map per template.** Different employers/forms need their own map but share the
  same engine. The map is throwaway per document; the engine is the reusable asset.
- **Fit-size self-box trap.** If you shift an item's x then compute its width against
  the un-shifted boxes, the scan for "nearest content to the right" can catch the
  item's OWN box → width collapses → font shrinks to floor. Compute the gap at the
  ORIGINAL x, render at the shifted x.
