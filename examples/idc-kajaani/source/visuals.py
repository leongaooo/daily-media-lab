"""Direct the Kajaani capacity diagram, status comparison and Blender route."""

import argparse
from html import escape
import json
from pathlib import Path
import re

from playwright.sync_api import sync_playwright

from mixed_shot import PictureState, eased_progress, render_states

TEXT, MUTED, MINT, AMBER = "#F2F7F6", "#AEC8CA", "#6AE5C5", "#F5BC70"
PANEL, STROKE, INK = "#172C39", "#40616D", "#0B1C28"


def rect(x, y, width, height, fill, stroke="none", radius=18):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
    )


def label(x, y, text, size=42, color=TEXT, weight=500, anchor="start"):
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{escape(text)}</text>'
    )


def line(x1, y1, x2, y2, color, width=4):
    return (
        f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linecap="round"/>'
    )


def svg(parts):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" '
        'viewBox="0 0 1920 1080" font-family="Microsoft YaHei, sans-serif">'
        + "".join(parts)
        + "</svg>"
    )


def stage(title, status, footer):
    return [
        '<defs><linearGradient id="scene" x2="1" y2="1">'
        '<stop stop-color="#203B49"/><stop offset="1" stop-color="#0A1925"/>'
        "</linearGradient></defs>",
        rect(0, 0, 1920, 1080, "url(#scene)", radius=0),
        line(100, 128, 1820, 128, STROKE, 2),
        rect(480, 62, 10, 33, MINT, radius=3),
        label(512, 90, "算力基础设施", 35, MINT, 700),
        label(1820, 94, status, 35, MINT, 700, "end"),
        label(100, 232, title, 74, TEXT, 700),
        line(100, 800, 1820, 800, STROKE, 2),
        label(100, 863, footer, 33, MUTED),
    ]


def hall(x, y, width, height, number, rack, accent):
    offset = 23
    return [
        f'<path d="M{x},{y} l{offset},-{offset} h{width} l-{offset},{offset} z" '
        f'fill="#436372" stroke="{STROKE}" stroke-width="3"/>',
        rect(x, y, width, height, "#233D4A", STROKE, 4),
        rect(x + 19, y + 20, 7, height - 40, accent, radius=3),
        rack.format(x=x + width // 2 - 83, y=y + 19),
        label(
            x + width / 2, y + height - 19, f"数据厅 {number}", 31, TEXT, 600, "middle"
        ),
    ]


def capacity(step, rack):
    parts = stage("首座数据中心启用", "芬兰 · 卡亚尼", "来源 XTX Markets  2026.11.24")
    parts += [
        rect(100, 320, 600, 405, INK, STROKE),
        label(155, 414, "运营方公告", 42, MINT, 680),
        label(150, 543, "11 月 24 日", 83, TEXT, 720),
        label(155, 645, "园区首座设施", 47, MUTED),
        rect(740, 320, 1080, 405, PANEL, STROKE),
    ]
    if step == 0:
        parts += hall(1170, 420, 310, 225, "示意", rack, MINT)
    else:
        parts += [
            label(840, 442, "首座设施 · IT 功率容量", 48, MINT, 650),
            label(830, 617, "22.5", 158, TEXT, 730),
            label(1280, 616, "MW", 72, MUTED, 650),
        ]
    return svg(parts)


def comparison(progress, show_future, rack):
    parts = stage(
        "一座设施，三个数据厅",
        "启用与计划",
        "来源  卡亚尼市项目说明  /  XTX Markets 启用公告",
    )
    # Zoom the hall group near its centre while leaving outer comparison cards fixed.
    scale = round(1 + 0.12 * progress, 3)
    parts += [
        rect(100, 319, 1112, 433, INK, MINT),
        rect(1246, 319, 574, 433, INK, STROKE),
        label(138, 380, "首座设施", 42, TEXT, 700),
        label(1160, 380, "已启用", 42, MINT, 700, "end"),
        '<g transform="translate(651 550) scale('
        + str(scale)
        + ') translate(-651 -550)">',
    ]
    for number, x in enumerate((202, 536, 870), 1):
        parts += hall(x, 460, 221, 188, number, rack, MINT if progress else MUTED)
    if progress > 0:
        extent = 320 * progress
        parts += [
            line(312, 430, 312 + extent, 430, MINT, 5),
            line(969 - extent, 430, 969, 430, MINT, 5),
        ]
    parts += [
        "</g>",
        label(138, 715, "3 个厅  /  合计 22.5 MW IT 容量", 40, MINT, 650),
        label(1290, 380, "第二座设施", 42, TEXT, 700),
        label(1772, 380, "计划", 42, AMBER, 700, "end"),
        rect(1288, 444, 483, 207, PANEL, STROKE),
        label(1330, 540, "2027 年", 71, AMBER if show_future else MUTED, 700),
        label(1330, 606, "计划启用", 41, MUTED, 600),
    ]
    return svg(parts)


def overlay(projection, arrived):
    parts = [
        rect(935, 29, 890, 95, INK, STROKE),
        label(965, 73, "首座设施 · 三个数据厅", 51, TEXT, 700),
        label(965, 112, "原创空间示意 · 镜头路线", 34, MINT, 660),
        rect(1070, 771, 745, 94, INK, STROKE),
        label(
            1110,
            830,
            "单厅分配及实时负载未披露" if arrived else "青色箭头指向三个数据厅",
            39,
            TEXT,
        ),
    ]
    for number, (x, y) in enumerate(projection["halls"], 1):
        parts += [
            line(x, y - 22, x, y + 12, MINT),
            rect(x - 82, y - 64, 164, 45, INK, MINT, 12),
            label(x, y - 31, f"数据厅 {number}", 31, TEXT, 660, "middle"),
        ]
    return svg(parts)


def states(job, cues, rack, projection):
    for frame in range(cues[2]):
        detail = int(frame >= cues[1])
        yield PictureState("topology", frame + 1, str(detail), capacity(detail, rack))

    for frame in range(cues[2], cues[6]):
        if frame < cues[4]:
            progress = eased_progress(frame, cues[3], 18)
        else:
            progress = 1 - eased_progress(frame, cues[4], 18)
        progress = round(progress, 2)
        show_future = frame >= cues[4]
        key = f"{progress:.2f}-{int(show_future)}"
        yield PictureState(
            "retrofit",
            frame - cues[2] + 1,
            key,
            comparison(progress, show_future, rack),
        )

    for frame in range(1, cues[8] - cues[6] + 1):
        arrived = frame > projection["arrival_frame"]
        yield PictureState(
            "route",
            frame,
            str(int(arrived)),
            overlay(projection, arrived),
            job / "raw3d" / f"{frame:04d}.png",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    job = args.job
    cues = json.loads((job / "timing.json").read_text(encoding="utf-8"))["boundaries"]
    projection = json.loads((job / "projection.json").read_text(encoding="utf-8"))
    asset = (job / "source/rack.svg").read_text(encoding="utf-8")
    asset = re.sub(r"<svg\b[^>]*>", "", asset, count=1, flags=re.DOTALL).split(
        "</svg>"
    )[0]
    # Retain the complete original SVG as an input. The nested viewBox sets its display size.
    rack = (
        '<svg x="{x}" y="{y}" width="166" height="110" viewBox="0 0 530 620">'
        + asset
        + "</svg>"
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        render_states(job, page, states(job, cues, rack, projection))
        browser.close()


if __name__ == "__main__":
    main()
