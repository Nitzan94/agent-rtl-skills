---
name: rtl-authoring
description: Author correct right-to-left (Hebrew / Arabic) content — HTML/CSS, PDF, Markdown, UI copy — handling the bidi algorithm, mixed LTR runs (numbers, English, code, URLs), punctuation and bracket mirroring, fonts, and Arabic shaping. Use when producing NEW RTL output or fixing RTL that renders backwards, with flipped numbers/parentheses, or mojibake.
when_to_use: >
  Use when you are PRODUCING or FIXING right-to-left content (Hebrew or Arabic):
  an HTML page/email, a generated PDF, a Markdown doc, UI strings, or a report
  that must read RTL. Especially when the output renders backwards, numbers or
  punctuation jump to the wrong side, parentheses/brackets look reversed, English
  or code embedded in Hebrew breaks the line, or Arabic letters come out isolated
  (unjoined). Trigger phrases: "write this in Hebrew/Arabic", "make this RTL",
  "the Hebrew is backwards", "numbers are in the wrong place", "parentheses are
  flipped", "render Hebrew PDF", "RTL email/invoice/doc". NOT for translating an
  existing fixed-layout PDF form — that's the `empty-and-fill-pdf` skill.
---

# RTL Authoring (Hebrew / Arabic)

Produce content that reads correctly right-to-left. The hard part is almost never
"make it right-aligned" — it's the **bidirectional (bidi) interaction** between RTL
text and the LTR runs embedded in it (numbers, currency, English words, code, URLs,
dates). Get the model below right and 90% of "RTL is broken" complaints vanish.

## The one mental model that fixes most bugs

You store text in **logical order** (the order you'd type/read it). The renderer
applies the **Unicode Bidi Algorithm (UBA)** to compute **visual order** at display
time. You almost never reorder characters yourself — you give the engine the right
*signals* so its reordering is correct.

- **Strong RTL** chars (Hebrew, Arabic) flow right-to-left.
- **Strong LTR** chars (Latin letters) flow left-to-right.
- **Weak/neutral** chars (digits, spaces, `. , : ; ( ) [ ] / - + %` , punctuation)
  take direction from their **surroundings** — this is where things break. A colon
  or a parenthesis next to Hebrew gets pulled RTL and lands on the "wrong" side.

The fix is almost always **isolation**: tell the engine "this run is its own
direction, don't let the neighbours bleed in."

## Bracket & punctuation mirroring (the #1 surprise)

In an RTL context the engine **mirrors** `(`, `)`, `[`, `]`, `{`, `}`, `<`, `>`.
Type them **logically** — type `(74)` and in RTL it renders as `(74)` correctly
mirrored; do NOT pre-swap to `)74(` to "fix" it (that double-flips). Same for a
trailing `:` or `.` — type it where you'd read it; let UBA place it.

If a number/parenthesis still lands wrong, the run isn't isolated — see below.

## HTML / CSS — the primary, easiest correct path

```html
<html dir="rtl" lang="he">   <!-- set dir on the root; lang for fonts/hyphenation -->
```
- Set **`dir="rtl"`** on the element (or `<html>`). This is the real switch —
  `text-align: right` alone is NOT RTL (it right-aligns LTR text; punctuation and
  wrapping stay wrong).
- Use **CSS logical properties** so the layout mirrors automatically:
  `margin-inline-start`, `padding-inline-end`, `inset-inline-start`,
  `border-inline-*`, `text-align: start/end` — NOT `left`/`right`.
- **Isolate embedded LTR runs** (English words, code, URLs, emails, phone numbers,
  long number+unit strings):
  - HTML: wrap in `<bdi>…</bdi>` (auto-isolate) or `<span dir="ltr">…</span>`.
  - CSS: `unicode-bidi: isolate` (or `isolate-override` to also force direction).
  - Bare control chars when you can't add markup: `&rlm;` (RLM) / `&lrm;` (LRM),
    or isolates `&#x2066;…&#x2069;` (LRI/PDI).
- `<bdo dir="ltr">` only when you must *force* visual order (rare; debugging).

Mixed example that renders correctly:
```html
<p dir="rtl">המחיר הוא <bdi>120 ₪</bdi> עבור <bdi>ChatGPT Plus</bdi> (לחודש).</p>
```

## Generated PDFs — know what does bidi and what doesn't

This is where Hebrew/Arabic most often comes out **reversed or unjoined**, because
many libraries place glyphs with **no bidi and no shaping**.

- **Glyph-placement libs (PyMuPDF `insert_text`, bare ReportLab `drawString`)** do
  NOT run UBA and do NOT shape Arabic. Output = backwards / isolated letters. Avoid
  for RTL body text.
- **Best path: author HTML and render to PDF** — `weasyprint`, Playwright/`page.pdf()`,
  or `wkhtmltopdf`. The browser engine does bidi + shaping for free. Easiest correct
  result.
- **If you must go programmatic:** ReportLab **+ `python-bidi`** (reorders logical→
  visual) **+ `arabic-reshaper`** (Arabic contextual forms). Hebrew needs python-bidi
  but NOT reshaping; Arabic needs both.
- **Editing an existing fixed-layout form** (not authoring): that's a different
  problem — use the `empty-and-fill-pdf` skill (empty → mirror → refill).

## Fonts

- The font must actually contain Hebrew/Arabic glyphs — many "nice" Latin fonts
  don't, and you get tofu (□) or a silent fallback. Verify coverage.
- Good web/system choices: Hebrew — Rubik, Heebo, Assistant, Noto Sans Hebrew, Arial.
  Arabic — Noto Naskh/Sans Arabic, Cairo, Amiri, Tajawal.
- **Arabic is cursive**: letters change shape by position (initial/medial/final/
  isolated). The font + a shaping-aware renderer handle this; in a non-shaping
  context (some PDF libs) you must `arabic-reshaper` first or letters stay isolated.

## Markdown

- Markdown has no direction attribute. For RTL, wrap blocks in HTML:
  `<div dir="rtl"> … </div>`. Many renderers (incl. some GitHub contexts) **strip**
  the `dir` attribute — verify in the actual target, and if stripped, fall back to a
  real HTML doc.
- Code fences stay LTR (correct) — don't wrap code in RTL.

## Terminals / CLI

RTL in terminal emulators is unreliable (most don't implement UBA). Don't promise
correct RTL in CLI output; render to HTML/PDF/file instead and open it.

## Verification — always render, then check these

Open the actual output (browser / PDF viewer / Read the PDF) and scan for:
- [ ] Whole paragraph reads right-to-left, wraps from the right.
- [ ] **Numbers** read left-to-right and sit on the correct side of their label.
- [ ] **Parentheses/brackets** open and close the right way around their content.
- [ ] Trailing **`:` / `.`** are on the correct (left) end of the line.
- [ ] Embedded **English / code / URLs / emails** are intact and not reversed.
- [ ] **Arabic** letters are **joined** (cursive), not isolated.
- [ ] No **tofu** (□) — font covers the script.

## Gotchas
- **`text-align: right` ≠ RTL.** It only moves the block; bidi, wrapping, and
  punctuation placement need `dir="rtl"`.
- **Don't manually reverse strings** to "fix" backwards text — you're fighting the
  bidi engine; the real cause is a missing `dir`/isolation. Reversing double-breaks
  it the moment any number or English appears.
- **Numbers next to Hebrew drift** because digits are weak — isolate the run
  (`<bdi>`) or add `&rlm;`/`&lrm;`.
- **Arabic from a non-shaping pipeline comes out isolated** — reshape before placing.
- **`dir` stripped by sanitizers** (email clients, Markdown renderers) — test in the
  real target; some need inline `style="direction:rtl"` or a wrapping table.
- **Copy-paste from a PDF reverses RTL** (visual→logical) — never trust pasted Hebrew
  as a source of logical order; re-key or extract programmatically.
- **Mixed-direction UI**: mirror layout with logical CSS properties, but keep
  inherently-LTR data (phone numbers, IBANs, code, version strings) isolated LTR.
