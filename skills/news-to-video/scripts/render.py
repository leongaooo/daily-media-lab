"""Local Editorial-only pipeline; one project owns one measured program timeline."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image
import soundfile as sf

from music_bed import DEFAULT_MUSIC, mix_audio, validate_music, write_attribution
from voice_backend import DEFAULT_SPEED, VOICE_ID, make_voice, validate_voice
import remotion_visual

ENGINE = "remotion_editorial"
DIMENSIONS = {"width": 1920, "height": 1080, "fps": 24}
# Reject active renderer settings that Editorial cannot honor; never silently drop them.
LEGACY_FIELDS = {
    "layout",
    "presenter",
    "visual_beats",
    "background_focus",
    "background_opacity",
    "image_layout",
    "header_style",
    "decoration",
}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def stamp(seconds):
    ms = round(seconds * 1000)
    return (
        f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    )


def timeline(items, target, fps):
    sr = items[0]["sr"]
    speech = sum(len(i["audio"]) for i in items) / sr
    required = speech + 0.08 * (len(items) - 1) + 0.2
    duration = math.ceil((target if target is not None else required) * fps) / fps
    if required > duration:
        raise ValueError(
            f"Voice needs at least {required:.2f}s; target is {duration:.2f}s. Shorten script or extend duration; speech was not clipped."
        )
    gap = (duration - speech - 0.2) / max(1, len(items) - 1) if len(items) > 1 else 0
    voice = np.zeros(round(duration * sr))
    gate = np.zeros_like(voice)
    cues = []
    cursor = 0.1
    peak = max(np.max(abs(i["audio"])) for i in items)
    for item in items:
        a = item["audio"].copy()
        a -= np.mean(a)
        a *= 0.78 / max(peak, 0.001)
        ramp = min(round(0.006 * sr), len(a) // 2)
        if ramp:
            a[:ramp] *= np.linspace(0, 1, ramp)
            a[-ramp:] *= np.linspace(1, 0, ramp)
        start = round(cursor * sr)
        voice[start : start + len(a)] += a
        gate[
            max(0, start - round(0.1 * sr)) : min(
                len(gate), start + len(a) + round(0.15 * sr)
            )
        ] = 1
        cues.append(
            dict(
                scene=item["scene"],
                text=item["text"],
                start=cursor,
                speech_end=(start + len(a)) / sr,
            )
        )
        cursor += len(a) / sr + gap
    cues[0]["start"] = 0
    for i, cue in enumerate(cues):
        cue["end"] = cues[i + 1]["start"] if i + 1 < len(cues) else duration
    return duration, voice, gate, cues


def validate(project):
    """Reject unsupported projects before reading voice references or synthesizing."""
    if not project.get("title") or not project.get("scenes"):
        raise ValueError("Project requires title and scenes")
    if project.get("visual_engine", ENGINE) != ENGINE:
        raise ValueError("Only remotion_editorial is supported")
    editorial = project.get("editorial", {})
    dimensions = tuple(
        editorial.get(key, default) for key, default in DIMENSIONS.items()
    )
    if dimensions != tuple(DIMENSIONS.values()):
        raise ValueError("Editorial requires 1920x1080 at 24 fps")
    if any(
        project.get(key, expected) != expected for key, expected in DIMENSIONS.items()
    ):
        raise ValueError(
            "Top-level dimensions must match Editorial: 1920x1080 at 24 fps"
        )
    if editorial.get("captions", "bottom_rail") not in ("bottom_rail", "off"):
        raise ValueError("editorial.captions must be bottom_rail or off")
    for owner in [project, *project["scenes"]]:
        unsupported = LEGACY_FIELDS.intersection(owner)
        if unsupported:
            raise ValueError(
                "Remove unsupported layout fields and plan Editorial scenes: "
                + ", ".join(sorted(unsupported))
            )
    target = project.get("duration")
    if target is not None and (not math.isfinite(target) or target <= 0):
        raise ValueError("duration must be positive or omitted")
    validate_voice(project)
    validate_music(project.get("music", {}))
    for scene in project["scenes"]:
        kind = remotion_visual._kind(scene)
        if kind not in ("hero", "flow", "chart"):
            raise ValueError("editorial_kind must be hero, flow or chart")
        if not scene.get("segments"):
            raise ValueError("Each scene needs semantic narration segments")
        for segment in scene["segments"]:
            if (
                not segment.get("text", "").strip()
                or not segment.get("spoken", segment["text"]).strip()
            ):
                raise ValueError("Empty caption or narration")
            if re.search(r"[A-Za-z]", segment.get("spoken", segment["text"])):
                raise ValueError("Supply Chinese pronunciation in spoken for acronyms")
        if kind == "chart":
            rows = scene.get("data", [])
            if not rows or len(rows) > 5 or not scene.get("data_source"):
                raise ValueError("chart needs 1..5 rows and data_source")
            if any(
                not row.get("label")
                or not math.isfinite(row["value"])
                or row["value"] < 0
                for row in rows
            ):
                raise ValueError("chart values must be finite and nonnegative")


def production_plan(project, cues, payload, output):
    """Describe actual scene choices without promising unimplemented layers."""
    lines = [
        f"# {project['title']} · 制作计划",
        "",
        f"画面引擎：{ENGINE}；1920×1080 / 24fps。",
        "",
        "字幕轨：y904—1080；素材、文字与运动均保留在轨道上方。",
        "",
        f"视觉依据：{project.get('art_direction', '按内容规划；具体构图见逐幕记录。')}",
        "",
    ]
    for index, scene in enumerate(project["scenes"]):
        scene_cues = [cue for cue in cues if cue["scene"] == index]
        actual = payload["scenes"][index]
        lines.extend(
            [
                f"## {index + 1}. {scene.get('chapter', '')} / {scene_cues[0]['start']:.3f}—{scene_cues[-1]['end']:.3f}s",
                "",
                f"镜头：{actual['kind']}；主标题：{scene.get('headline', '')}",
                "",
                f"口播：{' '.join(segment.get('spoken', segment['text']) for segment in scene['segments'])}",
                "",
                f"画面：{scene.get('visual_direction', '按本幕语义设计编辑式构图。')}",
                "",
                f"素材：{scene.get('image') or scene.get('background_image') or '原生文字/图形'}；完整包含：{actual['image_fit']}",
                "",
                f"生图要求：{scene.get('image_prompt', '无需新增生成图；使用已核验素材或原生图形。')}",
                "",
                f"避免：{scene.get('negative_prompt', '文字溢出、字幕遮挡、无来源的现场暗示。')}",
                "",
                f"来源：{scene.get('data_source', '见项目sources及剧本映射。')}",
                "",
            ]
        )
    lines.extend(
        [
            "## 配音与音乐",
            "",
            f"唯一B版男声，{project['voice']['speed']}倍保留音高变速及已认可轻度降噪；音乐原速。",
            "",
            (output / "音乐署名.txt").read_text(encoding="utf-8"),
            "",
            "## 来源记录",
            "",
            json.dumps(project.get("sources", []), ensure_ascii=False, indent=2),
        ]
    )
    (output / "production-plan.md").write_text("\n".join(lines), encoding="utf-8")


def run(args):
    """Render one project as one continuous program using the sole visual engine."""
    if args.visual_engine != ENGINE:
        raise ValueError("Only remotion_editorial is supported")
    project_path = Path(args.project).resolve()
    project = json.loads(project_path.read_text(encoding="utf-8-sig"))
    validate(project)
    base = project_path.parent
    runtime_path = Path(
        args.runtime
        or os.environ.get(
            "NEWS_TO_VIDEO_RUNTIME",
            str(Path.home() / ".cache/news-to-video/runtime.json"),
        )
    )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8-sig"))
    install, cli, probe, width, height, fps = remotion_visual.preflight(
        project, base, runtime
    )
    project["editorial"] = {
        **DIMENSIONS,
        "captions": "bottom_rail",
        **project.get("editorial", {}),
    }
    project.update(visual_engine=ENGINE, width=width, height=height, fps=fps)
    project["voice"] = {
        "id": VOICE_ID,
        "speed": project.get("voice", {}).get("speed", DEFAULT_SPEED),
    }
    project["music"] = {**DEFAULT_MUSIC, **project.get("music", {})}
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if "visual_selection_version" in project:
        from score_visuals import assess

        selection = assess(project)
        save_json(output / "visual-selection-report.json", selection)
        if selection["errors"]:
            raise ValueError(
                "Visual selection failed; see visual-selection-report.json"
            )
    font = Path(project.get("font", runtime.get("font", "")))
    if not font.is_file():
        raise ValueError("Configure a readable Chinese font file")
    cache = output / ".cache"
    cache.mkdir(exist_ok=True)
    items, models = make_voice(project, runtime, cache)
    duration, voice, gate, cues = timeline(items, project.get("duration"), fps)
    mixed, metrics, track = mix_audio(
        voice, gate, items[0]["sr"], project["music"], runtime, project["title"]
    )
    write_attribution(output, track)
    sf.write(output / "voice.wav", voice, items[0]["sr"], subtype="PCM_16")
    sf.write(output / "mix.wav", mixed, items[0]["sr"], subtype="PCM_16")
    save_json(output / "timeline.json", cues)
    save_json(output / "project.json", project)
    (output / "captions.srt").write_text(
        "\n".join(
            f"{index + 1}\n{stamp(cue['start'])} --> {stamp(cue['end'])}\n{cue['text']}\n"
            for index, cue in enumerate(cues)
        ),
        encoding="utf-8-sig",
    )
    (output / "narration.txt").write_text(
        "\n".join(
            segment.get("spoken", segment["text"])
            for scene in project["scenes"]
            for segment in scene["segments"]
        ),
        encoding="utf-8",
    )
    folder = output / "remotion"
    payload = remotion_visual.stage(project, cues, duration, base, folder, font)
    production_plan(project, cues, payload, output)
    silent = cache / f"{remotion_visual.render_key(folder, payload)}.mp4"
    reused = silent.is_file()
    if not reused:
        remotion_visual.render(
            install, cli, folder, silent, payload, output / "render.log"
        )
    frames = round(duration * fps)
    remotion_visual.verify(silent, probe, width, height, fps, frames)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    previews = [
        remotion_visual.preview_frame(
            ffmpeg, silent, math.floor((cue["start"] + cue["end"]) / 2 * fps)
        )
        for cue in cues
    ]
    # The storyboard follows the actual horizontal frame ratio, without empty portrait cells.
    sheet = Image.new("RGB", (810, 152 * math.ceil(len(previews) / 3)), "#0c1725")
    for index, picture in enumerate(previews):
        sheet.paste(picture, ((index % 3) * 270, (index // 3) * 152))
    sheet.save(output / "storyboard.jpg")
    result = output / "video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(silent),
            "-i",
            str(output / "mix.wav"),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            str(duration),
            "-movflags",
            "+faststart",
            str(result),
        ],
        check=True,
    )
    subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(result), "-f", "null", "-"], check=True
    )
    reader = imageio_ffmpeg.read_frames(str(result))
    actual = next(reader)
    reader.close()
    if tuple(actual["size"]) != (width, height) or abs(actual["fps"] - fps) > 0.01:
        raise ValueError("Encoded dimensions or frame rate mismatch")
    if abs(actual["duration"] - duration) > 0.15:
        raise ValueError("Encoded duration mismatch")
    report = dict(
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        cue_count=len(cues),
        continuous_captions=all(
            left["end"] == right["start"] for left, right in zip(cues, cues[1:])
        ),
        picture_stream_reused=reused,
        visual_engine=ENGINE,
        full_decode_passed=True,
        audio=metrics,
        warnings=[],
        model_sha256=models,
        voice=project["voice"],
        sources=project.get("sources", []),
        encoded_metadata={
            key: actual[key] for key in ("size", "fps", "duration", "codec", "pix_fmt")
        },
        layout_contract="Editorial composition with a reserved bottom caption rail",
        alignment="Measured synthesized semantic clips; not ASR word-level forced alignment",
        remotion_editorial={
            "version": "remotion-editorial-v1",
            "composition": "Editorial",
            "picture_frame_count": frames,
            "captions_in_video": project["editorial"]["captions"],
            "caption_rail": {
                "reserved_y": [904, 1080],
                "content_must_end_before_y": 904,
            },
        },
    )
    save_json(output / "validation.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime")
    parser.add_argument("--visual-engine", choices=(ENGINE,), default=ENGINE)
    return parser


if __name__ == "__main__":
    run(argument_parser().parse_args())
