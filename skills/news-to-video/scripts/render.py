"""Local Editorial-only pipeline; one project owns one measured program timeline."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import shutil
import sys
from uuid import uuid4

from media_storage import clean_rendered_stage, render_storage

from frozen_audio import external_mode, validate_config, load_final, frame_at
from narrative_media import read_json as read_narrative, validate_manifest
from episode import file_identity, validate_animatic_receipt

import imageio_ffmpeg
import numpy as np
from PIL import Image
import soundfile as sf

from music_bed import DEFAULT_MUSIC, mix_audio, validate_music, write_attribution
from voice_backend import DEFAULT_SPEED, VOICE_ID, make_voice, validate_voice
import remotion_visual
from visual_contract import GRAMMARS, require_valid
from director_contract import assess as assess_director, narration_identity

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


def _visual_path(project):
    if project.get("narrative_version") == 1:
        return "narrative_v1"
    if project.get("visual_contract_version") == 2:
        return "object_stage"
    return "legacy"


def validate_formal_acceptance(project, project_path, base):
    """Bind the full render to the approved baseline and the reviewed scene inputs."""
    contract = project.get("acceptance_contract")
    if contract is None:
        return None
    if contract != "daily-v1":
        raise ValueError("Unsupported project acceptance_contract")
    for key in (
        "episode_id",
        "baseline_id",
        "production_baseline",
        "animatic_review_receipt",
    ):
        if not isinstance(project.get(key), str) or not project[key].strip():
            raise ValueError(f"daily-v1 requires {key}")
    receipt_path = (base / project["animatic_review_receipt"]).resolve(strict=True)
    stability_gate_version = project.get("stability_gate_version")
    if stability_gate_version not in (None, 1):
        raise ValueError("stability_gate_version must be 1 when provided")
    receipt = validate_animatic_receipt(
        receipt_path,
        project["episode_id"],
        require_stability=stability_gate_version == 1,
    )
    baseline = file_identity(base / project["production_baseline"])
    if (
        baseline != receipt["baseline"]
        or project["baseline_id"] != receipt["baseline_id"]
    ):
        raise ValueError(
            "Formal project baseline differs from the reviewed production baseline"
        )
    visual_path = _visual_path(project)
    if visual_path != receipt["visual_path"]:
        raise ValueError(
            "Animatic visual_path must match the formal project visual path"
        )
    if project.get("editorial", {}).get("captions", "bottom_rail") != "bottom_rail":
        raise ValueError("Daily production requires the bottom caption rail")
    if visual_path == "legacy":
        reason = project.get("simple_diagram_reason")
        if (
            project.get("visual_contract_version") != 1
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise ValueError(
                "Daily production requires an explicit simple diagram or narrative path"
            )
    preview_path = Path(receipt["project"]["path"])
    preview_project = remotion_visual.normalize_editorial(read_narrative(preview_path))
    selected = receipt["scope"]["scenes"]
    if selected != sorted(set(selected)) or not all(
        0 <= index < len(project["scenes"]) for index in selected
    ):
        raise ValueError("Preview scope must name ordered scenes in the formal project")
    if preview_project.get("scenes") != [
        project["scenes"][index] for index in selected
    ]:
        raise ValueError("Preview scene or narration differs from the formal inputs")
    if external_mode(project):
        voice = project["voice"]
        if (
            file_identity(base / voice["path"])["sha256"]
            != receipt["voice_window"]["source"]["sha256"]
        ):
            raise ValueError("Review audio must come from the formal frozen dry voice")
        full_cues = read_narrative(base / voice["cues"])
        selected_cues = [cue for cue in full_cues if cue["scene"] in selected]
        window = receipt["voice_window"]
        rate = voice["sample_rate"]
        start, end = window["start_sample"], window["end_sample"]
        if (start, end) != (
            round(selected_cues[0]["start"] * rate),
            round(selected_cues[-1]["end"] * rate),
        ):
            raise ValueError("Preview window must cover the selected semantic scenes")
        for cue in selected_cues:
            cue["scene"] = selected.index(cue["scene"])
            for edge in ("start", "end"):
                cue[edge] = (round(cue[edge] * rate) - start) / rate
        preview_cues = read_narrative(
            preview_path.parent / preview_project["voice"]["cues"]
        )
        for given, expected in zip(preview_cues, selected_cues, strict=True):
            if any(
                given[key] != expected[key] for key in ("scene", "text", "start", "end")
            ):
                raise ValueError("Preview must use the selected frozen semantic cues")
    if visual_path == "object_stage":
        component = remotion_visual._component_source(project, base)
        consumer = (
            component / "Stage.tsx"
            if component
            else remotion_visual.TEMPLATE / "ObjectStage.tsx"
        )
        if (
            file_identity(consumer)["sha256"]
            != receipt["consumer"]["artifact"]["sha256"]
        ):
            raise ValueError("Formal visual consumer differs from the reviewed source")
    return {
        "baseline": baseline,
        "baseline_id": project["baseline_id"],
        "animatic": file_identity(receipt_path),
        "project": file_identity(project_path),
        "visual_path": visual_path,
        "stability_gate": receipt.get("stability_gate"),
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
    project = remotion_visual.normalize_editorial(project)
    remotion_visual.render_options(project)
    narrative = project.get("narrative_version") == 1
    if "narrative_version" in project and not narrative:
        raise ValueError("narrative_version must be 1")
    if narrative:
        if not project.get("narrative_manifest"):
            raise ValueError("Narrative project requires narrative_manifest")
        if project.get("visual_contract_version") is not None:
            raise ValueError(
                "Narrative v1 is separate from legacy visual_contract_version"
            )
    else:
        require_valid(project)
    director = assess_director(project)
    if director["errors"]:
        raise ValueError("Director contract: " + "; ".join(director["errors"]))
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
    if external_mode(project):
        validate_config(project["voice"])
    else:
        validate_voice(project)
    validate_music(project.get("music", {}))
    if narrative and project.get("music", {}).get("mode", "pool") == "pool":
        if not project.get("music", {}).get("track_id") or not project.get(
            "music", {}
        ).get("selection_reason"):
            raise ValueError(
                "Narrative music requires explicit track_id and selection_reason, or mode=off"
            )
    for scene in project["scenes"]:
        kind = remotion_visual._kind(scene)
        if not narrative and kind not in GRAMMARS:
            raise ValueError("Unsupported editorial visual grammar")
        if not scene.get("segments"):
            raise ValueError("Each scene needs semantic narration segments")
        for segment in scene["segments"]:
            if (
                not segment.get("text", "").strip()
                or not segment.get("spoken", segment["text"]).strip()
            ):
                raise ValueError("Empty caption or narration")
            if not external_mode(project) and re.search(
                r"[A-Za-z]", segment.get("spoken", segment["text"])
            ):
                raise ValueError("Supply Chinese pronunciation in spoken for acronyms")
        if not narrative and kind == "chart":
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
        if not narrative and kind == "story":
            shots = scene.get("shots", [])
            if not 2 <= len(shots) <= 4:
                raise ValueError("story needs 2..4 semantic shots")
            if any(
                not isinstance(shot, dict) or not shot.get("title", "").strip()
                for shot in shots
            ):
                raise ValueError("story shots need non-empty titles")


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
                f"视觉策略：{scene.get('visual_strategy', '未指定')}；动效计划：{json.dumps(scene.get('motion_plan', {}), ensure_ascii=False)}",
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
        if actual.get("object_stage"):
            lines.extend(
                ["| 字幕索引 | 对象动作 | 实测帧区间 | 依据 |", "|---|---|---|---|"]
            )
            for action in actual["object_stage"]["actions"]:
                lines.append(
                    f"| {action['segment']} | {action['target']} / {action['type']} "
                    f"| {action['start_frame']}—{action['end_frame']} | {action['evidence']} |"
                )
            lines.extend(
                [
                    "",
                    "上述为实际编译的动作；连续播放与审美验收另记，不能由帧表代替。",
                    "",
                ]
            )
    lines.extend(
        [
            "## 配音与音乐",
            "",
            (
                "已冻结最终口播：逐字节保留，播放倍率1.0，无TTS/变速/降噪/重拼。"
                if external_mode(project)
                else f"显式声音 {project['voice']['id']}，{project['voice']['speed']}倍保留音高变速及已认可轻度降噪；音乐原速。"
            ),
            "",
            (output / "音乐署名.txt").read_text(encoding="utf-8"),
            "",
            "## 来源记录",
            "",
            json.dumps(project.get("sources", []), ensure_ascii=False, indent=2),
        ]
    )
    (output / "production-plan.md").write_text("\n".join(lines), encoding="utf-8")


def prepare_narration(project, runtime, cache, base, output, fps):
    """唯一人声分流边界；最终音频不触碰合成、处理及分段时间线。"""
    if external_mode(project):
        duration, voice, gate, cues, sample_rate, models, original_voice = load_final(
            project, base
        )
        # Preserve the exact frozen file bytes; the stereo mix is a separate work product.
        if original_voice.resolve() != (output / "voice.wav").resolve():
            shutil.copyfile(original_voice, output / "voice.wav")
    else:
        items, models = make_voice(project, runtime, cache)
        duration, voice, gate, cues = timeline(items, project.get("duration"), fps)
        sample_rate = items[0]["sr"]
        for cue in cues:
            cue["start_frame"] = frame_at(cue["start"])
            cue["end_frame"] = frame_at(cue["end"])
        sf.write(output / "voice.wav", voice, sample_rate, subtype="PCM_16")
    return duration, voice, gate, cues, sample_rate, models


def run(args, *, reclaim_narrative_stage=False, production_context=None):
    """Render one project as one continuous program using the sole visual engine."""
    if args.visual_engine != ENGINE:
        raise ValueError("Only remotion_editorial is supported")
    project_path = Path(args.project).resolve()
    project = remotion_visual.normalize_editorial(
        json.loads(project_path.read_text(encoding="utf-8-sig"))
    )
    validate(project)
    picture_only = getattr(args, "picture_only", False)
    if picture_only and (
        project.get("narrative_version") != 1 or not external_mode(project)
    ):
        raise ValueError("--picture-only requires a sealed narrative and frozen audio")
    base = project_path.parent
    acceptance = validate_formal_acceptance(project, project_path, base)
    pending_images = any(
        scene.get("image_generation", {}).get("enabled", True)
        and scene.get("image_generation")
        and not scene["image_generation"].get("resolved_sha256")
        for news in project["scenes"]
        for scene in [news, *news.get("shots", [])]
    )
    if pending_images:
        if not getattr(args, "image_connection", None):
            raise ValueError(
                "Enabled image_generation requires --image-connection; image_prompt alone never submits a paid request"
            )
        from generate_images import run as generate_images
        from types import SimpleNamespace

        generated = Path(args.output).resolve() / "generated-assets"
        status = generate_images(
            SimpleNamespace(
                project=str(project_path),
                connection=args.image_connection,
                credentials=getattr(args, "image_credentials", None),
                output=str(generated),
                generate=True,
                max_new_images=10,
            )
        )
        if status:
            raise ValueError(
                "Image generation failed; see generated-assets/generation-report.json"
            )
        project = remotion_visual.normalize_editorial(
            json.loads(
                (generated / "resolved-project.json").read_text(encoding="utf-8")
            )
        )
        validate(project)
        if acceptance is not None:
            validate_formal_acceptance(project, project_path, base)
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
    # Preserve cue identity and suppress the display layer for the silent cut.
    if picture_only:
        project["editorial"]["captions"] = "off"
    project.update(visual_engine=ENGINE, width=width, height=height, fps=fps)
    if not external_mode(project):
        project["voice"] = {
            "id": project.get("voice", {}).get("id", VOICE_ID),
            "speed": project.get("voice", {}).get("speed", DEFAULT_SPEED),
        }
    project["music"] = {**DEFAULT_MUSIC, **project.get("music", {})}
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    save_json(output / "story-world-report.json", assess_director(project))
    if project.get("narrative_version") != 1:
        save_json(output / "visual-diversity-report.json", require_valid(project, base))
    previous_path = output / "project.json"
    if (
        "director_contract_version" in project or external_mode(project)
    ) and previous_path.is_file():
        previous = json.loads(previous_path.read_text(encoding="utf-8-sig"))
        if narration_identity(previous) != narration_identity(project):
            raise ValueError(
                "Narration is frozen for this output; keep spoken/voice/duration "
                "unchanged. For an explicitly authorized rewrite use a new output."
            )
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
    duration, voice, gate, cues, sample_rate, models = prepare_narration(
        project, runtime, cache, base, output, fps
    )
    if project.get("narrative_version") == 1:
        manifest_path = (base / project["narrative_manifest"]).resolve()
        validate_manifest(
            read_narrative(manifest_path), manifest_path.parent, round(duration * fps)
        )
    mixed, metrics, track = mix_audio(
        voice, gate, sample_rate, project["music"], runtime, project["title"]
    )
    from sound_tracks import add_tracks, resolve_event_tracks

    sound_tracks = project.get("sound_tracks", [])
    if project.get("narrative_directing"):
        from joint_directing import load_directing

        directing = load_directing(project, base, total_frames=round(duration * fps))
        sound_tracks = resolve_event_tracks(sound_tracks, directing["events"], fps)
    mixed, track_metrics = add_tracks(mixed, voice, sample_rate, sound_tracks, base)
    metrics["sound_tracks"] = track_metrics
    # Report the final mix, including independent ambience/effects added above.
    metrics["peak"] = float(np.max(np.abs(mixed)))
    metrics["peak_scope"] = "final mix including sound_tracks"
    write_attribution(output, track)
    if track_metrics:
        with (output / "音乐署名.txt").open("a", encoding="utf-8") as attribution:
            for sound in track_metrics:
                attribution.write(
                    f"\n{sound['track_id']}：{sound['attribution']}；{sound['source_url']}；{sound['license']}；设计声音，非新闻现场录音。\n"
                )
    sf.write(output / "mix.wav", mixed, sample_rate, subtype="PCM_16")
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
    save_json(
        output / "motion-report.json",
        {
            "version": "narrative-1" if project.get("narrative_version") == 1 else 2,
            "visual_path": _visual_path(project),
            "consumer": {
                "kind": (
                    "narrative_stage"
                    if project.get("narrative_version") == 1
                    else (
                        "object_stage"
                        if project.get("visual_contract_version") == 2
                        else "editorial_composition"
                    )
                ),
                "module": (
                    "narrative"
                    if project.get("narrative_version") == 1
                    else (
                        "custom/Stage"
                        if project.get("editorial", {}).get("component_dir")
                        else (
                            "ObjectStage"
                            if project.get("visual_contract_version") == 2
                            else "Composition"
                        )
                    )
                ),
            },
            "narrative_shots": payload.get("narrative_shots", []),
            "engine": ENGINE,
            "status": "staged-awaiting-render",
            "review_status": "requires-continuous-review",
            "scenes": [
                {
                    "scene": index,
                    "kind": scene["kind"],
                    "shots": scene["shots"],
                    "actions": [
                        {
                            "action_id": f"scene-{index}-action-{action_index}",
                            **action,
                        }
                        for action_index, action in enumerate(
                            scene.get("object_stage", {}).get("actions", [])
                        )
                    ],
                    "content_ends_before_y": 904,
                }
                for index, scene in enumerate(payload["scenes"])
            ],
        },
    )
    motion_path = output / "motion-report.json"
    motion = read_narrative(motion_path)
    consumer_module = motion["consumer"]["module"]
    consumer_path = folder / "src" / f"{consumer_module}.tsx"
    if not consumer_path.is_file() and consumer_module == "narrative":
        consumer_path = folder / "src" / "Composition.tsx"
    if not consumer_path.is_file():
        raise ValueError(f"Visual consumer source is missing: {consumer_path}")
    motion["consumer"]["artifact"] = file_identity(consumer_path)
    save_json(motion_path, motion)
    production_plan(project, cues, payload, output)
    silent = cache / f"{remotion_visual.render_key(folder, payload)}.mp4"
    frames = round(duration * fps)
    reused = silent.is_file()
    if reused:
        try:
            remotion_visual.verify(silent, probe, width, height, fps, frames)
        except (ValueError, subprocess.CalledProcessError, json.JSONDecodeError):
            # This content-addressed file belongs to this renderer, never a user master.
            silent.unlink()
            reused = False
    if not reused:
        temporary_picture = silent.with_suffix(".partial.mp4")
        try:
            remotion_visual.render(
                install, cli, folder, temporary_picture, payload, output / "render.log"
            )
            remotion_visual.verify(temporary_picture, probe, width, height, fps, frames)
            temporary_picture.replace(silent)
        finally:
            temporary_picture.unlink(missing_ok=True)
    motion = json.loads(motion_path.read_text(encoding="utf-8"))
    motion.update(status="rendered", picture_key=silent.stem, frame_count=frames)
    save_json(motion_path, motion)
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
    # Both cuts share the Remotion picture and retain the frozen cue duration.
    mux = [ffmpeg, "-y", "-v", "error", "-i", str(silent)]
    if not picture_only:
        mux.extend(["-i", str(output / "mix.wav")])
    mux.extend(["-map", "0:v:0", "-c:v", "copy"])
    if not picture_only:
        mux.extend(["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"])
    mux.extend(
        [
            "-t",
            str(duration),
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-color_range",
            "tv",
            "-movflags",
            "+faststart",
            str(result),
        ]
    )
    subprocess.run(mux, check=True)
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
        model_sha256=models if not external_mode(project) else {},
        frozen_audio=models if external_mode(project) else None,
        voice=project["voice"],
        sources=project.get("sources", []),
        encoded_metadata={
            key: actual[key] for key in ("size", "fps", "duration", "codec", "pix_fmt")
        },
        layout_contract="Editorial composition with a reserved bottom caption rail",
        alignment=(
            "Frozen sample timeline with supplied measured cues; not word-level forced alignment"
            if external_mode(project)
            else "Measured synthesized semantic clips; not ASR word-level forced alignment"
        ),
        remotion_editorial={
            "version": f"remotion-editorial-v{project.get('visual_contract_version', 1)}",
            "composition": "Editorial",
            "picture_frame_count": frames,
            "captions_in_video": project["editorial"]["captions"],
            "caption_rail": {
                "reserved_y": [904, 1080],
                "content_must_end_before_y": 904,
            },
        },
    )
    if production_context is not None:
        report["production_baseline"] = production_context
    report["artifacts"] = {
        name: file_identity(output / name)
        for name in (
            "video.mp4",
            "captions.srt",
            "timeline.json",
            "voice.wav",
            "motion-report.json",
        )
    }
    if picture_only:
        report["picture_only"] = True
    elif acceptance is not None:
        report["acceptance"] = acceptance
    save_json(output / "validation.json", report)
    if reclaim_narrative_stage and project.get("narrative_version") == 1:
        try:
            clean_rendered_stage(
                project,
                base,
                output,
                output / f"storage-stage-cleanup-{uuid4().hex}.json",
                reason="Decoded delivery and its independently sealed source frames",
                apply=True,
            )
        except (OSError, KeyError, ValueError) as error:
            # The encoded delivery is already verified. Keep any stage with incomplete evidence.
            print(f"Narrative stage cleanup deferred: {error}", file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--min-free-bytes",
        type=int,
        help="Minimum free bytes required for a managed media jobs output",
    )
    parser.add_argument(
        "--keep-narrative-stage",
        action="store_true",
        help="Keep managed Remotion frame copies for Studio or working review",
    )
    parser.add_argument(
        "--picture-only",
        action="store_true",
        help="Render a sealed narrative without visible captions or an audio stream",
    )
    parser.add_argument("--runtime")
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run a technical example or preflight render without a production receipt",
    )
    parser.add_argument("--image-connection")
    parser.add_argument("--image-credentials")
    parser.add_argument("--visual-engine", choices=(ENGINE,), default=ENGINE)
    return parser


if __name__ == "__main__":
    options = argument_parser().parse_args()
    from production_contract import ACTIVE_NAME, ASSETS

    if (ASSETS / ACTIVE_NAME).is_file() and not (
        options.picture_only or options.backend_only
    ):
        raise SystemExit("Use production.py for new production or revalidation")
    if options.min_free_bytes is not None and options.min_free_bytes < 0:
        raise SystemExit("--min-free-bytes must be nonnegative")
    with render_storage(
        Path(options.project), Path(options.output), options.min_free_bytes
    ) as job:
        run(
            options,
            reclaim_narrative_stage=job is not None
            and not options.keep_narrative_stage,
        )
