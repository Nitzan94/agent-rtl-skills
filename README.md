# RTL Skills — publishable bundle

Two Claude Code skills for working with right-to-left (Hebrew / Arabic) content.
PII-free and rescoped from a private payslip-translation project for public release.

## What's here

- **`rtl-authoring/`** — *Produce* correct RTL content (HTML/CSS, generated PDFs,
  Markdown, UI copy). Covers the bidi algorithm, mixed LTR runs (numbers, English,
  code, URLs), bracket/punctuation mirroring, fonts, and Arabic shaping. This is the
  "why is RTL so painful" skill: it front-loads the gotchas that cost you three
  failed attempts to discover.

- **`translate-rtl-form/`** — *Translate* an existing filled PDF form into English
  (or another language) while keeping the **exact original form** — empty only the
  text, flip the layout RTL→LTR, refill fitted-to-cell. Numbers, boxes, lines, and
  logos stay. Includes a reusable engine (`scripts/pdf_form_engine.py`) and a
  runnable synthetic demo (`scripts/example_translate.py`).

The two are complementary and have deliberately non-overlapping triggers: one
**authors** new RTL, the other **edits** an existing fixed-layout form.

## Who it's for

Hebrew/Arabic-speaking developers and Claude Code users who repeatedly need:
- English versions of official RTL forms (visa, mortgage-abroad, employer, embassy), or
- to generate Hebrew/Arabic docs/emails/PDFs that don't come out backwards.

Honest scope: `translate-rtl-form` is **semi-manual** — one translation map per form
template, with a visual-verify-and-iterate loop. It is not a one-click "drop a PDF,
get English" tool. The engine is the reusable asset; the per-form map is throwaway.

## Known limitations (`translate-rtl-form`)

Validated on a real, dense government form (Israeli Form 106). It produced a readable
English LTR version in one pass — and surfaced the inherent rough edges to expect:

- **One translation map per form template.** The engine is reusable; the map is
  throwaway and hand-built per form. This is not a drop-in, zero-config converter.
- **Long flowing paragraphs / badly-glued spans can be missed.** They're reported as
  MISSES (never dropped silently) — you place them manually from the coordinate dump.
- **Already-LTR numeric runs reverse under the mirror** (e.g. a `1…12` months header
  becomes `12…1`). Detect purely-numeric horizontal runs and re-place them un-mirrored.
- **Form template marker glyphs pass through as text** (e.g. repeated row markers) and
  can clutter; filter them per form if needed.
- **Field/reference codes are preserved verbatim** (correct, but can look cryptic).
- **Scanned / image-only PDFs are refused** — they have no text layer (needs OCR).

In short: it gets you a faithful, ~90%-there English form fast; the last mile is a
short visual-verify-and-iterate loop, which the skill documents.

## Requirements

- Claude Code (these are skills, run by the agent).
- Python with `uv` for the PDF engine: `uv run --with PyMuPDF --with pillow python ...`

## Try the engine demo

```
cd translate-rtl-form/scripts
uv run --with PyMuPDF --with pillow python example_translate.py
# -> demo_translated.pdf : sample form emptied, mirrored, refilled from a map
```

## Installing locally

Copy either folder into your skills directory (e.g. `~/.claude/skills/`), or publish
the whole bundle to a git repo / skill marketplace. Each folder is a self-contained
skill (`SKILL.md` + any `scripts/`).

## Provenance

Distilled from a real Hebrew→English payslip-translation project. All personal data
(names, addresses, salaries, employers) has been removed; examples are synthetic.
