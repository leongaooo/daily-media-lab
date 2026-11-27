"""Author the revised 2D shots on the existing integer-frame narration timeline."""

from visuals import AMBER, BG, CARD, LINE, MINT, MUTED, TEXT
import visuals as base


def path(d, stroke, width=3, fill="none", extra=""):
    return (
        f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round" {extra}/>'
    )


def dot(x, y, size, fill, stroke="none"):
    return f'<circle cx="{x}" cy="{y}" r="{size}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'


def phase_progress(frame, origin, duration):
    progress = min(1, max(0, (frame - origin) / duration))
    return base.smooth_step(progress)


def stage(title, status, source, footer):
    parts = base.header(title, status, source, AMBER, footer)
    parts[0] = base.rect(0, 0, 1920, 1080, "url(#field)", radius=0)
    parts[3] = base.label(96, 231, title, 67, TEXT, 700)
    parts[4] = base.label(1824, 224, status, 43, AMBER, 700, "end")
    parts[5] = base.line(96, 793, 1824, 793, LINE, 2)
    parts[6] = base.label(96, 857, source, 38, MUTED)
    parts[7] = base.label(1824, 857, footer, 40, AMBER, 650, "end")
    parts.insert(
        0,
        """<defs>
      <linearGradient id="field" x2="1" y2="1" gradientUnits="objectBoundingBox">
        <stop stop-color="#1A2D3A"/><stop offset="1" stop-color="#101D29"/>
      </linearGradient>
      <linearGradient id="top" x2="0" y2="1">
        <stop stop-color="#7695A4"/><stop offset="1" stop-color="#365768"/>
      </linearGradient>
      <linearGradient id="front" x2="0" y2="1">
        <stop stop-color="#35566A"/><stop offset="1" stop-color="#182935"/>
      </linearGradient>
      <pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">
        <path d="M44 0H0V44" fill="none" stroke="#263F4D" stroke-width="1"/>
      </pattern>
    </defs>""",
    )
    return parts


def chassis(width, height, depth, accent):
    # All components share a front face and a top-right oblique projection.
    return [
        f'<ellipse cx="{width * .52}" cy="{height + 5}" rx="{width * .58}" ry="{depth * .37}" fill="#0B1720"/>',
        path(
            f"M0,0 l{depth},-{depth/2} h{width} l-{depth},{depth/2}z",
            "#7C9EAE",
            2,
            "url(#top)",
        ),
        path(
            f"M{width},0 l{depth},-{depth/2} v{height} l-{depth},{depth/2}z",
            "#5B7A8B",
            2,
            "#294453",
        ),
        base.rect(0, 0, width, height, "url(#front)", "#86A9B8", 2, 4),
        base.line(4, 4, width - 4, 4, accent, 3),
    ]


def topology_device(x, y, kind, accent):
    width, height, depth = (250, 44, 56)
    part = [f'<g transform="translate({x} {y})">']
    if kind == "compute":
        for level in (100, 50, 0):
            part.append(f'<g transform="translate(0 {level})">')
            part += chassis(width, height, depth, accent)
            for bay in (18, 73, 128):
                part.append(base.rect(bay, 13, 46, 21, "#152632", "#567485", 2, 3))
            part += [
                base.line(190, 17, 224, 17, "#9EB9C4", 3),
                dot(225, 28, 3, accent),
                "</g>",
            ]
    else:
        part += chassis(width, 66, depth, accent)
        for port in range(8):
            port_x = 18 + port * 28
            part += [
                base.rect(port_x, 20, 20, 22, "#0B1B25", "#6B8794", 2, 2),
                base.line(port_x + 5, 25, port_x + 15, 25, accent, 2),
            ]
        part.append(base.line(20, 53, 229, 53, "#496B7C", 2))
    return part + ["</g>"]


def topology(frame, cue):
    relation = phase_progress(frame, min(22, cue[1] // 6), 24)
    test = phase_progress(frame, cue[1], 24)
    parts = stage(
        "端网协同拟议拓扑",
        "拟议 · 测试结果待核",
        "来源　ODCC 工作组会议动态",
        "设备为通用示意",
    )
    parts += [
        base.rect(96, 272, 1728, 492, "#12252F", "#344F60", 2, 26),
        base.rect(98, 274, 1724, 488, "url(#grid)", radius=24),
        base.label(386, 345, "算力节点", 54, TEXT, 700, "middle"),
        base.label(1534, 345, "交换节点", 54, TEXT, 700, "middle"),
        *topology_device(252, 390, "compute", MINT),
        *topology_device(1382, 425, "switch", MINT),
        base.label(
            960,
            406,
            "拟议交互规则",
            54,
            MINT if relation > 0.5 else MUTED,
            700,
            "middle",
        ),
        base.line(565, 458, 1375, 458, "#658593", 6, "15 15"),
        dot(565, 458, 9, BG, MINT),
        dot(1375, 458, 9, BG, MINT),
        base.line(960, 488, 960, 596, "#718798", 5, "9 13"),
        base.rect(672, 601, 576, 123, "#243542", AMBER if test > 0.1 else LINE, 3, 23),
        base.label(
            960, 650, "一致性测试集", 49, AMBER if test > 0.1 else TEXT, 700, "middle"
        ),
        base.label(960, 699, "拟议配套", 41, MUTED, 600, "middle"),
    ]
    if relation:
        # from center outwards, without signifying a traffic direction
        span = 405 * relation
        parts += [
            base.line(
                970 - span,
                458,
                970 + span,
                458,
                MINT if not test else "#4A9D91",
                6,
                "15 15",
            ),
            dot(960, 458, 12, BG, MINT),
        ]
    if test:
        parts += [
            base.line(960, 488, 960, 488 + 108 * test, AMBER, 5, "9 13"),
            dot(960, 598, 8, AMBER),
        ]
    return base.svg(parts), f"topology-r{relation:.3f}-t{test:.3f}"


def rack(x, y, accent, filled, new=False):
    width, height, depth = (43, 131, 17) if new else (44, 103, 18)
    outline = "M0,0 l{d},-{h} h{w} v{height} l-{d},{h} h-{w}z".format(
        d=depth, h=depth / 2, w=width, height=height
    )
    parts = [f'<g transform="translate({x} {y})">']
    if not filled:
        parts += [path(outline, "#708897", 2, "#1D303C", 'stroke-dasharray="4 5"')]
    else:
        parts += chassis(width, height, depth, accent)
        for slot in range(4 if new else 3):
            top = 13 + slot * 26
            parts += [
                base.rect(5, top, width - 10, 17, "#192E3B", "#618090", 1.5, 2),
                base.line(10, top + 5, width - 12, top + 5, accent, 2),
            ]
        if new:
            parts.append(base.line(width - 7, 6, width - 7, height - 5, accent, 2))
    return parts + ["</g>"]


def rack_group(x, y, active):
    parts = [
        path(
            f"M{x-12},{y+102} l42,-24 h119 l-42,24z",
            "#4F6D7D",
            2,
            "#1D3541",
            'stroke-dasharray="5 5"',
        ),
    ]
    for index in range(2, -1, -1):
        parts += rack(x + index * 34, y - index * 12, AMBER, active)
    return parts


def montage_panel(x, baseline, scale, emphasis, accent):
    border = accent if emphasis else "#486475"
    return [
        base.rect(x, 281, 835, 484, "#192B37", border, 3, 24),
        base.line(x + 42, 369, x + 792, 369, "#466070", 2),
        base.line(x + 42, 620, x + 792, 620, "#466070", 2),
        f'<clipPath id="{baseline}-art"><rect x="{x+30}" y="382" width="775" height="228"/></clipPath>',
        f'<g clip-path="url(#{baseline}-art)">',
        f'<g transform="translate({x+415},497) scale({scale:.4f}) translate({-x-415},-497)">',
        base.rect(x + 66, 543, 703, 56, "#223845", radius=9),
    ]


def retrofit(frame, cue):
    remove = cue[3] <= frame < cue[4]
    install = cue[4] <= frame < cue[5]
    final = frame >= cue[5]
    zoom_on = phase_progress(frame, cue[3] - 18, 18)
    zoom_off = phase_progress(frame, cue[5], 18)
    move_frame = frame - (cue[3] if remove else cue[4])
    # Both comparison panels stay registered while their equipment areas zoom.
    zoom = 1 + 0.15 * zoom_on * (1 - zoom_off)
    parts = stage(
        "旧机房改造参考",
        "RD120 · 厂商参考设计",
        "来源　施耐德电气 RD120",
        "电力／冷水／空间／联调待核",
    )
    parts += montage_panel(96, "old", zoom, remove, AMBER)
    for index, x in enumerate((192, 410, 628)):
        progress = phase_progress(move_frame, index * 3, 10) if remove else 0
        parts += rack_group(x, 479, False)
        if not install and progress < 1:
            parts.append(
                f'<g opacity="{1-progress:.4f}" transform="translate({-26*progress:.2f},{-44*progress:.2f})">'
            )
            parts += rack_group(x, 479, True)
            parts.append("</g>")
    parts += ["</g></g>"]
    parts += montage_panel(989, "new", zoom, install, MINT)
    for index in range(10):
        x = 1078 + index * 65
        progress = (
            phase_progress(move_frame, index * 2, 11) if install else float(final)
        )
        parts += rack(x, 436, MINT, False, new=True)
        if progress:
            parts.append(
                f'<g opacity="{progress:.4f}" transform="translate(0,{42*(1-progress):.2f})">'
            )
            parts += rack(x, 436, MINT, True, new=True)
            parts.append("</g>")
    parts += ["</g></g>"]

    original = "3 组旧机柜"
    if remove:
        original = "移出 3 组旧机柜"
    elif install:
        original = "旧机柜组已移出"
    parts += [
        base.label(138, 347, "旧机房条件", 48, TEXT, 690),
        base.label(1031, 347, "改造参考配置", 48, TEXT, 690),
        base.label(138, 685, original, 45, AMBER, 700),
        base.label(138, 741, "4 条电力链 · 平均 20 kW／柜", 41, MUTED, 550),
        base.label(1031, 685, "10 套 Helios", 48, MINT, 700),
        base.label(1776, 685, "720 张 GPU", 48, MINT, 700, "end"),
        base.label(1031, 741, "机柜组与机架级系统示意", 41, MUTED, 550),
    ]
    action_frame = min(move_frame, 31) if remove or install else 0
    phase = (
        "remove" if remove else "install" if install else "after" if final else "before"
    )
    return base.svg(parts), f"retrofit-{phase}-{zoom:.4f}-{action_frame:02d}"


def states(cue):
    for frame in range(cue[6]):
        if frame < cue[2]:
            art, name = topology(frame, cue)
            yield "topology", frame + 1, art, name
        else:
            art, name = retrofit(frame, cue)
            yield "retrofit", frame - cue[2] + 1, art, name


if __name__ == "__main__":
    base.states = states
    base.main()
