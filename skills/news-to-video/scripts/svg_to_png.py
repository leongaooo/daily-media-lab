"""Rasterize and check the approved 720x480 primitive SVG subset; no downloads."""

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from color_utils import contrast

ATTRS = {
    "rect": {"x", "y", "width", "height", "rx", "fill"},
    "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-width"},
    "polygon": {"points", "fill"},
    "text": {"x", "y", "font-family", "font-size", "text-anchor", "fill"},
}


def color(value):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError("Colors must be explicit #RRGGBB values")
    return value


def rasterize(source, output, font_path, background, panel, report_path=None):
    raw = Path(source).read_text(encoding="utf-8-sig")
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise ValueError("DTD and entities are unsupported")
    root = ET.fromstring(raw)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Expected SVG namespace on root")
    if set(root.attrib) - {"width", "height", "viewBox"}:
        raise ValueError("Unsupported root attribute")
    if (root.get("width"), root.get("height"), root.get("viewBox")) != (
        "720",
        "480",
        "0 0 720 480",
    ):
        raise ValueError("Expected 720x480 canvas and matching viewBox")
    background, panel = color(background), color(panel)
    font_path = Path(font_path)
    if not font_path.is_file():
        raise ValueError("A readable Chinese font file is required")
    image = Image.new("RGBA", (1440, 960))
    draw = ImageDraw.Draw(image)
    text_ratios = []

    def n(el, key, default=None):
        value = float(el.get(key, default))
        if not math.isfinite(value):
            raise ValueError("Nonfinite coordinate")
        return value

    def inside(box):
        if box[0] < 0 or box[1] < 0 or box[2] > 1440 or box[3] > 960:
            raise ValueError("Element exceeds canvas")

    for el in root:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ATTRS or not el.tag.startswith("{http://www.w3.org/2000/svg}"):
            raise ValueError(f"Unsupported element: {tag}")
        if list(el) or set(el.attrib) - ATTRS[tag]:
            raise ValueError(f"Unsupported children or attributes: {tag}")
        fill = color(el.get("stroke" if tag == "line" else "fill", "#F5F4ED"))
        if tag == "rect":
            x, y, w, h = [n(el, k) * 2 for k in ("x", "y", "width", "height")]
            radius = n(el, "rx", 0) * 2
            if min(w, h) <= 0 or radius < 0:
                raise ValueError("Invalid rectangle dimensions")
            box = (x, y, x + w, y + h)
            inside(box)
            draw.rounded_rectangle(box, radius=radius, fill=fill)
        elif tag == "line":
            pts = [n(el, k) * 2 for k in ("x1", "y1", "x2", "y2")]
            width = n(el, "stroke-width", 6) * 2
            if width <= 0:
                raise ValueError("Line width must be positive")
            inside(
                (
                    min(pts[0], pts[2]) - width / 2,
                    min(pts[1], pts[3]) - width / 2,
                    max(pts[0], pts[2]) + width / 2,
                    max(pts[1], pts[3]) + width / 2,
                )
            )
            draw.line(pts, fill=fill, width=round(width))
        elif tag == "polygon":
            pts = [
                tuple(float(v) * 2 for v in pair.split(","))
                for pair in el.get("points", "").split()
            ]
            if len(pts) < 3 or any(
                len(pt) != 2 or not all(math.isfinite(v) for v in pt) for pt in pts
            ):
                raise ValueError("Expected at least three finite polygon points")
            inside(
                (
                    min(x for x, y in pts),
                    min(y for x, y in pts),
                    max(x for x, y in pts),
                    max(y for x, y in pts),
                )
            )
            draw.polygon(pts, fill=fill)
        else:
            if el.get("text-anchor") != "middle" or not el.text or not el.text.strip():
                raise ValueError("Expected nonempty text with middle anchor")
            size = n(el, "font-size")
            if size < 27:
                raise ValueError(
                    "Labels below 27px require redesign for phone readability"
                )
            font = ImageFont.truetype(str(font_path), round(size * 2))
            xy = (n(el, "x") * 2, n(el, "y") * 2)
            inside(draw.textbbox(xy, el.text, font=font, anchor="ms"))
            ratio = min(contrast(fill, background), contrast(fill, panel))
            if ratio < 4.5:
                raise ValueError("Text contrast below 4.5:1 on scene or panel")
            text_ratios.append(ratio)
            draw.text(xy, el.text, font=font, fill=fill, anchor="ms")
    if not text_ratios or image.getbbox() is None:
        raise ValueError("Expected visible diagram with labels")
    output = Path(output)
    if Path(source).resolve() == output.resolve():
        raise ValueError("Source and output must differ")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")
    report = dict(
        passed=True,
        source=str(source),
        png=str(output),
        size=[1440, 960],
        min_text_contrast=min(text_ratios),
        font=str(font_path),
        external_dependencies=False,
        embedded_animation=False,
        composition_verified=False,
        scope="SVG source primitives, glyph bounds and contrast only; review final Editorial frames",
        requires_review=[
            "semantic correctness",
            "phone readability",
            "actual platform controls",
        ],
    )
    Path(report_path or output.with_suffix(".validation.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg")
    parser.add_argument("--output", required=True)
    parser.add_argument("--font", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    print(
        json.dumps(
            rasterize(
                args.svg,
                args.output,
                args.font,
                args.background,
                args.panel,
                args.report,
            ),
            ensure_ascii=False,
        )
    )
