"""Render a synthetic tracked data badge with and without bottom captions."""

import argparse
from pathlib import Path
import subprocess

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00F7FFF8,&H00FFFFFF,&H00102024,&H00102024,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def event(layer, start, end, body):
    return f"Dialogue: {layer},0:00:{start},0:00:{end},Default,,0,0,0,,{body}\n"


def rectangle(layer, x, y, width, height, color):
    body = (
        rf"{{\an7\pos({x},{y})\1c&H{color}&\p1}}"
        f"m 0 0 l {width} 0 {width} {height} 0 {height}"
    )
    return event(layer, "00.00", "04.00", body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=False)

    # The card, leader, and module use the same 500–2600 ms transport window.
    picture = (
        rectangle(0, 190, 576, 1530, 98, "6E746A")
        + rectangle(1, 1330, 494, 390, 180, "877964")
        + event(2, "00.00", "04.00", r"{\pos(90,92)\fs47}Synthetic transport test")
        + event(3, "00.00", "04.00", r"{\an8\pos(1530,430)}Receiving pad")
        + event(
            4,
            "00.00",
            "04.00",
            r"{\move(346,533,1346,533,500,2600)\1c&HBCBD46&\p1}"
            r"m 0 0 l 200 0 200 110 0 110",
        )
        + event(
            5,
            "00.00",
            "04.00",
            r"{\move(346,380,1346,380,500,2600)\1c&H373027&\p1}"
            r"m 0 0 l 290 0 290 87 105 87 105 155 99 155 99 87 0 87",
        )
        + event(
            6,
            "00.00",
            "04.00",
            r"{\move(363,392,1363,392,500,2600)\fs46}120 kW"
            r"{\fs25}\NSynthetic module",
        )
        + event(
            7,
            "02.60",
            "04.00",
            r"{\an8\pos(1500,748)\fs38\1c&H95D6FF&}Utility connection pending",
        )
        + rectangle(0, 0, 904, 1920, 176, "30291B")
    )
    captions = event(
        10, "00.00", "02.60", r"{\an8\pos(960,969)\fs48}The unit moves to the pad."
    ) + event(
        10, "02.60", "04.00", r"{\an8\pos(960,969)\fs48}Utility connection is pending."
    )
    for name, track in (("captioned-review", picture + captions), ("silent", picture)):
        (folder / f"{name}.ass").write_text(HEADER + track, encoding="utf-8")
        subprocess.run(
            [
                args.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-xerror",
                "-nostdin",
                "-f",
                "lavfi",
                "-i",
                "color=0x3A4C49:s=1920x1080:r=24:d=4",
                "-vf",
                f"ass={name}.ass",
                "-c:v",
                "libx264",
                "-an",
                "-movflags",
                "+faststart",
                f"{name}.mp4",
            ],
            cwd=folder,
            check=True,
        )


if __name__ == "__main__":
    main()
