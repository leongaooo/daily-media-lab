"""Render the 2D camera states and place Blender-derived labels into the same canvas."""

import argparse
import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from mixed_shot import PictureState, render_states, verify_motion_windows

BG = "#101D29"
CARD = "#1A2C3A"
LINE = "#456174"
TEXT = "#F2F6F3"
MUTED = "#B7CAD3"
MINT = "#64E9CA"
AMBER = "#FFD291"


def rect(x, y, w, h, fill, stroke="none", width=2, radius=22):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{width}" rx="{radius}"/>'
    )


def label(x, y, value, size=42, color=TEXT, weight=500, anchor="start"):
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(value)}</text>'
    )


def line(x1, y1, x2, y2, color, width=4, dash=""):
    return (
        f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" '
        f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
        f'stroke-dasharray="{dash}"/>'
    )


def svg(content):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" '
        'viewBox="0 0 1920 1080" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">'
        + "".join(content)
        + "</svg>"
    )


def header(title, status, source, color=MINT, footer=""):
    return [
        rect(0, 0, 1920, 1080, BG, radius=0),
        label(96, 119, "算力基础设施", 32, MINT, 700),
        line(96, 144, 1824, 144, LINE, 2),
        label(96, 244, title, 66, TEXT, 700),
        label(1824, 237, status, 40, color, 700, "end"),
        line(96, 757, 1824, 757, LINE, 2),
        label(96, 830, source, 32, MUTED),
        label(1824, 830, footer, 34, color, 600, "end"),
    ]


def node(x, y, title, color, border):
    return [
        rect(x, y, 422, 164, CARD, border, 4),
        label(x + 211, y + 104, title, 51, color, 700, "middle"),
    ]


def topology(phase):
    parts = header(
        "端网协同的两个节点", "拟议 · 测试结果待核", "来源：ODCC 工作组会议动态", AMBER
    )
    edge = MINT if phase == 1 else LINE
    parts += [line(580, 445, 1340, 445, edge, 7, "16 17")]
    parts += node(158, 363, "算力节点", TEXT, MINT if phase < 2 else LINE)
    parts += node(1340, 363, "交换节点", TEXT, MINT if phase < 2 else LINE)
    parts += [
        rect(727, 359, 466, 70, BG),
        label(
            960, 408, "拟议交互规则", 46, MINT if phase == 1 else MUTED, 700, "middle"
        ),
        line(960, 470, 960, 557, AMBER if phase == 2 else LINE, 5, "8 15"),
        rect(687, 557, 546, 144, CARD, AMBER if phase == 2 else LINE, 4),
        label(
            960, 620, "一致性测试集", 48, AMBER if phase == 2 else MUTED, 680, "middle"
        ),
        label(960, 669, "拟议配套", 33, AMBER if phase == 2 else MUTED, 500, "middle"),
    ]
    return svg(parts)


def rack(x, y, color, filled=True, width=50, height=104):
    part = [rect(x, y, width, height, color if filled else CARD, color, 3, 5)]
    if filled:
        for delta in (23, 45, 67):
            part.append(line(x + 12, y + delta, x + width - 12, y + delta, BG, 3))
    return part


def retrofit(stage, zoom, action):
    parts = header(
        "旧机房改造参考",
        "厂商参考设计",
        "来源：施耐德电气 RD120",
        AMBER,
        "现场电力 · 冷水 · 空间 · 联调待核",
    )
    parts += [
        rect(126, 346, 794, 346, CARD, AMBER if stage == "remove" else LINE, 4),
        rect(1000, 346, 794, 346, CARD, MINT if stage == "install" else LINE, 4),
        label(174, 413, "旧机房条件", 46, TEXT, 700),
        label(1048, 413, "参考配置", 46, TEXT, 700),
        line(174, 444, 862, 444, LINE, 2),
        line(1048, 444, 1736, 444, LINE, 2),
    ]
    # Scale each equipment group around its own anchor. The comparison and its
    # condition labels stay registered, including while the inserts are enlarged.
    scale = 1 + 0.32 * zoom
    for side, anchor in (("old", 290), ("new", 1355)):
        transform = (
            f"translate({anchor} 527) scale({scale:.5f}) translate({-anchor} -527)"
        )
        parts.append(f'<g transform="{transform}">')
        if side == "old":
            for x in (178, 262, 346):
                parts += rack(x, 475, LINE, False)
            if stage in ("before", "remove", "result"):
                opacity = 1 - action if stage == "remove" else 1
                shift = -22 * action if stage == "remove" else 0
                parts.append(
                    f'<g opacity="{opacity:.4f}" transform="translate(0 {shift:.3f})">'
                )
                for x in (178, 262, 346):
                    parts += rack(x, 475, AMBER)
                parts.append("</g>")
        else:
            for index in range(10):
                x = 1102 + index * 59
                parts += rack(x, 475, LINE, False, 40)
                if stage in ("install", "result"):
                    opacity = action if stage == "install" else 1
                    shift = 22 * (1 - action) if stage == "install" else 0
                    parts.append(
                        f'<g opacity="{opacity:.4f}" transform="translate(0 {shift:.3f})">'
                    )
                    parts += rack(x, 475, MINT, True, 40)
                    parts.append("</g>")
        parts.append("</g>")
    old_text = {
        "before": "3 组旧机柜",
        "remove": "移除 3 组旧机柜",
        "install": "原位已清空",
        "result": "3 组旧机柜",
    }[stage]
    populated = stage in ("install", "result")
    parts += [
        label(174, 627, old_text, 42, AMBER if stage == "remove" else TEXT, 700),
        label(174, 674, "4 条电力链 · 原平均 20 kW／柜", 37, MUTED, 550),
        label(1048, 648, "10 套 Helios", 42, MINT if populated else TEXT, 700),
        label(1736, 647, "720 张 GPU", 39, MINT if populated else MUTED, 680, "end"),
    ]
    return svg(parts)


def route_labels(projection, arrived):
    parts = header(
        "计算模块进场示意",
        "路径示意",
        "来源：Fluidstack Blackbird 产品说明",
        MINT,
        "现场接口待核",
    )
    parts[0] = rect(0, 0, 1920, 1080, "none", radius=0)
    parts.insert(5, rect(0, 789, 1920, 115, BG, radius=0))
    parts[3] = label(96, 211, "计算模块进场示意", 58, TEXT, 700)
    parts[4] = label(1824, 204, "路径示意", 40, MINT, 700, "end")
    parts[6] = line(96, 790, 1824, 790, LINE, 2)
    parts[7] = label(96, 854, "来源：Fluidstack Blackbird 产品说明", 32, MUTED)
    parts[8] = label(1824, 854, "现场接口待核", 34, AMBER, 600, "end")
    for name, caption, dx, dy in (
        ("entrance", "进场", -144, 67),
        ("turn", "转向", 72, 62),
        ("receiving", "已到接收位" if arrived else "接收位", 178, -49),
    ):
        x, y = projection[name]
        tx, ty = x + dx, y + dy
        width = 201 if arrived and name == "receiving" else 139
        parts += [
            line(x, y, tx, ty, MINT, 3),
            rect(tx - width / 2, ty - 30, width, 60, BG, MINT, 2, 14),
            label(tx, ty + 13, caption, 35, TEXT, 650, "middle"),
        ]
    return svg(parts)


def smooth_step(t):
    return t * t * (3 - 2 * t)


def states(boundaries):
    cue = boundaries
    node_hold = min(22, max(12, (cue[1] - cue[0]) // 6))
    for frame in range(cue[6]):
        if frame < cue[2]:
            phase = 0 if frame < node_hold else 1 if frame < cue[1] else 2
            yield "topology", frame + 1, topology(phase), f"topology-{phase}"
            continue

        local = frame - cue[2] + 1
        ramp = 15
        if frame < cue[3] - ramp:
            stage, step = "before", 0
        elif frame < cue[3]:
            stage, step = "before", frame - (cue[3] - ramp) + 1
        elif frame < cue[4]:
            stage, step = "remove", ramp
        elif frame < cue[5]:
            stage, step = "install", ramp
        else:
            stage, step = "result", max(0, ramp - (frame - cue[5] + 1))
        action = 0
        if stage == "remove":
            action = min(12, frame - cue[3] + 1)
        elif stage == "install":
            action = min(12, frame - cue[4] + 1)
        art = retrofit(stage, smooth_step(step / ramp), smooth_step(action / 12))
        yield "retrofit", local, art, f"{stage}-{step:02d}-{action:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--phase", choices=("2d", "3d", "all"), default="all")
    args = parser.parse_args()
    job = args.job
    cue = json.loads((job / "timing.json").read_text(encoding="utf-8"))["boundaries"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser)
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1
        )
        if args.phase in ("2d", "all"):
            render_states(
                job,
                page,
                (
                    PictureState(shot, frame, name, art)
                    for shot, frame, art, name in states(cue)
                ),
            )

        if args.phase in ("3d", "all"):
            projection = json.loads(
                (job / "projection.json").read_text(encoding="utf-8")
            )
            arrival = projection["arrival_frame"]
            artwork = {
                "travel": route_labels(projection, False),
                "arrived": route_labels(projection, True),
            }

            def route_states():
                for frame in range(1, cue[8] - cue[6] + 1):
                    key = "arrived" if frame - 1 >= arrival else "travel"
                    plate = job / "raw3d" / f"{frame:04d}.png"
                    yield PictureState("route", frame, key, artwork[key], plate)

            render_states(job, page, route_states(), protected_y=904)
            verify_motion_windows(job / "frames/route", [(1, arrival + 1)])
        browser.close()


if __name__ == "__main__":
    main()
