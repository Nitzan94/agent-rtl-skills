#!/usr/bin/env python3
"""No-API evaluation gate for the RTL skill bundle.

This is a small, deterministic stand-in for a SkillOpt-style validation split:
generate public synthetic fixtures, exercise the reusable engine, and fail fast on
regressions in skill metadata, guidance, and PDF primitives.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / "translate-rtl-form" / "scripts" / "pdf_form_engine.py"


class CheckFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def load_engine():
    spec = importlib.util.spec_from_file_location("pdf_form_engine", ENGINE_PATH)
    require(spec is not None and spec.loader is not None, "cannot load pdf_form_engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pdf_form_engine"] = module
    spec.loader.exec_module(module)
    return module


def split_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    require(text.startswith("---\n"), f"{path} missing YAML frontmatter")
    _, raw, body = text.split("---", 2)
    meta: dict[str, str] = {}
    current: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            current = key.strip()
            meta[current] = value.strip().strip('"')
        elif current == "description":
            meta[current] = (meta[current] + " " + line.strip()).strip()
    return meta, body


def check_skill_metadata() -> None:
    expected = {
        "rtl-authoring": ROOT / "rtl-authoring" / "SKILL.md",
        "translate-rtl-form": ROOT / "translate-rtl-form" / "SKILL.md",
    }
    for name, path in expected.items():
        meta, body = split_frontmatter(path)
        require(meta.get("name") == name, f"{name}: wrong frontmatter name")
        require("description" in meta and len(meta["description"]) >= 80, f"{name}: weak description")
        require(len(meta["description"]) <= 520, f"{name}: description too long")
        require("when_to_use" not in meta, f"{name}: unsupported when_to_use key")
        require(len(body.strip()) > 500, f"{name}: body too short")


def check_skill_guidance() -> None:
    rtl = (ROOT / "rtl-authoring" / "SKILL.md").read_text(encoding="utf-8")
    form = (ROOT / "translate-rtl-form" / "SKILL.md").read_text(encoding="utf-8")

    for needle in [
        'dir="rtl"',
        "<bdi>",
        "unicode-bidi",
        "white-space: nowrap",
        "headless Chrome",
        "python-bidi",
        "arabic-reshaper",
        "translate-rtl-form",
    ]:
        require(needle in rtl, f"rtl-authoring missing guidance: {needle}")

    for needle in [
        "classify_page",
        "span_dump",
        "recover_legacy_text",
        "is_numeric_like",
        "mirror_rect",
        "UNICODE-Arabic",
        "fill=False",
        "SCANNED/no-text",
        "glue",
        "re-paste",
        "MISSES",
    ]:
        require(needle in form, f"translate-rtl-form missing guidance: {needle}")


def make_text_pdf(fitz, path: Path, *, texts: list[tuple[tuple[float, float], str]], fontfile: str | None = None) -> None:
    doc = fitz.open()
    page = doc.new_page(width=360, height=180)
    fontname = "helv"
    if fontfile:
        page.insert_font(fontname="testfont", fontfile=fontfile)
        fontname = "testfont"
    page.draw_rect(fitz.Rect(12, 12, 348, 168), color=(0, 0, 0), width=1)
    for y in [58, 104]:
        page.draw_line(fitz.Point(12, y), fitz.Point(348, y), color=(0.65, 0.65, 0.65), width=0.8)
    for point, text in texts:
        page.insert_text(point, text, fontname=fontname, fontsize=12)
    doc.save(path)
    doc.close()


def make_scanned_pdf(fitz, Image, path: Path) -> None:
    img = Image.new("RGB", (240, 120), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = fitz.open()
    page = doc.new_page(width=240, height=120)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)
    doc.close()


def check_engine_primitives(tmp: Path) -> None:
    engine = load_engine()
    import fitz
    from PIL import Image

    require(engine.has_rtl("שלום") is True, "has_rtl misses Hebrew")
    require(engine.has_rtl("مرحبا") is True, "has_rtl misses Arabic")
    require(engine.has_rtl("hello 123") is False, "has_rtl false positive")
    require(engine.is_numeric_like("1") is True, "numeric helper misses integer")
    require(engine.is_numeric_like("9,500") is True, "numeric helper misses comma number")
    require(engine.is_numeric_like("2026-06-22") is True, "numeric helper misses date-like run")
    require(engine.is_numeric_like("Tel Aviv 6789") is False, "numeric helper false positive")
    mirrored = engine.mirror_rect(300, (20, 10, 80, 40))
    require(tuple(round(v, 1) for v in mirrored) == (220.0, 10.0, 280.0, 40.0), "mirror_rect tuple failed")

    visual_hebrew = "םולש"
    mojibake = visual_hebrew.encode("cp1255").decode("latin1")
    require(engine.recover_legacy_text(mojibake, "cp1255") == "שלום", "legacy Hebrew recovery failed")

    ascii_pdf = tmp / "ascii-form.pdf"
    make_text_pdf(
        fitz,
        ascii_pdf,
        texts=[
            ((20, 38), "SHEM"),
            ((150, 38), "12345"),
            ((20, 84), "KTOVET"),
            ((150, 84), "Tel Aviv 6789"),
            ((20, 130), "SKHAR"),
            ((150, 130), "9,500"),
        ],
    )
    doc = fitz.open(ascii_pdf)
    page = doc[0]
    require(engine.classify_page(page)[0] == "CLEAN-ascii/latin", "ASCII form classification failed")
    require(len(engine.extract_spans(page)) == 6, "ASCII form span count changed")

    hebrew_pdf = tmp / "hebrew-glued-form.pdf"
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/ArialHB.ttc",
    ]
    fontfile = next((p for p in font_candidates if Path(p).exists()), None)
    make_text_pdf(
        fitz,
        hebrew_pdf,
        texts=[
            ((270, 38), "שם"),
            ((40, 38), "12345"),
            ((250, 84), "כתובת"),
            ((40, 84), "Tel Aviv 6789"),
        ],
        fontfile=fontfile,
    )
    hdoc = fitz.open(hebrew_pdf)
    hpage = hdoc[0]
    require(engine.classify_page(hpage)[0] == "UNICODE-Hebrew", "Hebrew form classification failed")
    dump = engine.span_dump(hpage)
    require(dump and {"idx", "text", "decoded", "bbox", "mirror_x", "size", "font"} <= set(dump[0]), "span_dump shape changed")

    arabic_pdf = tmp / "arabic-form.pdf"
    make_text_pdf(
        fitz,
        arabic_pdf,
        texts=[
            ((250, 38), "اسم"),
            ((40, 38), "12345"),
            ((235, 84), "عنوان"),
            ((40, 84), "Dubai 6789"),
        ],
        fontfile=fontfile,
    )
    adoc = fitz.open(arabic_pdf)
    require(engine.classify_page(adoc[0])[0] == "UNICODE-Arabic", "Arabic form classification failed")

    scanned_pdf = tmp / "scanned.pdf"
    make_scanned_pdf(fitz, Image, scanned_pdf)
    sdoc = fitz.open(scanned_pdf)
    require(engine.classify_page(sdoc[0])[0] == "SCANNED/no-text", "scanned PDF refusal signal failed")

    spans = engine.extract_spans(page)
    items = []
    mapping = {"SHEM": "Name", "KTOVET": "Address", "SKHAR": "Salary"}
    for span in spans:
        x0, y0, x1, y1 = span["bbox"]
        text = mapping.get(span["text"].strip(), span["text"].strip())
        items.append((x0, y0, x1, y1, text, span["size"]))

    engine.empty_form(page, spans)
    png = engine.rasterize(page, flip=True)
    out = fitz.open()
    op = out.new_page(width=page.rect.width, height=page.rect.height)
    op.insert_image(op.rect, stream=png)
    engine.place_items(op, items, page.rect.width, mirror=True)
    out_path = tmp / "translated.pdf"
    out.save(out_path)
    out.close()
    translated = fitz.open(out_path)[0].get_text()
    for expected in ["Name", "Address", "Salary", "12345", "Tel Aviv 6789", "9,500"]:
        require(expected in translated, f"translated output missing {expected!r}")


def check_authoring_static_fixture(tmp: Path) -> None:
    html = tmp / "rtl-authoring-fixture.html"
    html.write_text(
        """<!doctype html>
<html dir="rtl" lang="he">
<meta charset="utf-8">
<style>
.ltr { direction: ltr; unicode-bidi: isolate; white-space: nowrap; }
</style>
<p>המחיר הוא <bdi>120 ₪</bdi> עבור <bdi>ChatGPT Plus</bdi> (לחודש).</p>
<p>הקישור הוא <span class="ltr">https://example.com/a?x=1&y=2</span>.</p>
""",
        encoding="utf-8",
    )
    text = html.read_text(encoding="utf-8")
    for needle in ['dir="rtl"', 'lang="he"', "<bdi>", "unicode-bidi: isolate", "white-space: nowrap"]:
        require(needle in text, f"authoring fixture missing {needle}")


def run() -> int:
    checks = [
        ("skill metadata", lambda tmp: check_skill_metadata()),
        ("skill guidance", lambda tmp: check_skill_guidance()),
        ("engine primitives", check_engine_primitives),
        ("authoring static fixture", check_authoring_static_fixture),
    ]
    with tempfile.TemporaryDirectory(prefix="rtl-skill-evals-") as tmp_raw:
        tmp = Path(tmp_raw)
        for label, check in checks:
            try:
                check(tmp)
                print(f"PASS {label}")
            except Exception as exc:
                print(f"FAIL {label}: {exc}")
                return 1
    return 0


if __name__ == "__main__":
    if not ENGINE_PATH.exists():
        print(f"FAIL missing engine: {ENGINE_PATH}")
        raise SystemExit(1)
    raise SystemExit(run())
