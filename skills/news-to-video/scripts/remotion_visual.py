"""Stage and render the document-driven Remotion editorial composition."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from frozen_audio import frame_at
from narrative_media import (
    stage_manifest,
    read_json as read_manifest,
    validate_manifest,
)

from PIL import Image
from visual_contract import ASSET_KEYS, palette_for, require_valid
from object_contract import measured_stage
from joint_directing import load_directing, stage_directing

TEMPLATE = Path(__file__).resolve().parents[1] / "assets/remotion-editorial"


def normalize_editorial(project):
    """保留作者输入，解析旧字段并在声音处理前拒绝空主视觉。

    data_source/editorial_summary 是权威字段；旧 source/summary 仅补缺，
    同时存在的差异记入内部回执。两份节点冲突会改变事实，直接拒绝。
    Blender完整镜头不受旧节点规则约束。
    """
    if project.get("narrative_version") == 1:
        return project
    scenes = []
    for index, original in enumerate(project.get("scenes", [])):
        scene = dict(original)
        notes = list(scene.get("field_mapping_notes", []))
        for canonical, alias, default in (
            ("editorial_nodes", "nodes", []),
            ("data_source", "source", ""),
            ("editorial_summary", "summary", ""),
        ):
            if (
                canonical in scene
                and alias in scene
                and scene[canonical] != scene[alias]
            ):
                if canonical == "editorial_nodes":
                    raise ValueError(
                        f"Scene {index + 1}: nodes conflicts with editorial_nodes"
                    )
                note = f"{canonical} takes precedence over differing {alias}"
                if note not in notes:
                    notes.append(note)
            scene[canonical] = scene.get(canonical, scene.get(alias, default))
        for field in ("data_source", "editorial_summary"):
            if not isinstance(scene[field], str):
                raise ValueError(f"Scene {index + 1}: {field} must be text")
        nodes = scene["editorial_nodes"]
        if not isinstance(nodes, list) or any(
            not isinstance(node, dict)
            or not isinstance(node.get("title"), str)
            or not node["title"].strip()
            or not isinstance(node.get("detail", ""), str)
            for node in nodes
        ):
            raise ValueError(
                f"Scene {index + 1}: editorial_nodes require a title and text detail"
            )
        kind = _kind(scene)
        consumers = scene.get("shots") or [{}]
        for shot in consumers:
            effective_kind = shot.get("composition", kind)
            effective_nodes = shot.get("nodes", nodes)
            if not isinstance(effective_nodes, list) or any(
                not isinstance(node, dict)
                or not isinstance(node.get("title"), str)
                or not node["title"].strip()
                or not isinstance(node.get("detail", ""), str)
                for node in effective_nodes
            ):
                raise ValueError(
                    f"Scene {index + 1}: shot nodes require a title and text detail"
                )
            if effective_kind == "flow" and not 2 <= len(effective_nodes) <= 3:
                raise ValueError(
                    f"Scene {index + 1}: flow requires 2–3 editorial_nodes"
                )
            if effective_kind == "comparison" and len(effective_nodes) != 2:
                raise ValueError(
                    f"Scene {index + 1}: comparison requires exactly 2 editorial_nodes"
                )
            if (
                effective_kind == "evidence_board"
                and not 1 <= len(effective_nodes) <= 4
            ):
                raise ValueError(
                    f"Scene {index + 1}: evidence_board requires 1–4 editorial_nodes"
                )
        labels = scene.get("comparison_labels")
        if labels is not None and (
            not isinstance(labels, list)
            or len(labels) != 2
            or any(not isinstance(label, str) or not label.strip() for label in labels)
        ):
            raise ValueError(
                f"Scene {index + 1}: comparison_labels needs two nonempty labels"
            )
        if notes:
            scene["field_mapping_notes"] = notes
        scenes.append(scene)
    return {**project, "scenes": scenes}


def render_options(project):
    """校验本次进程的资源设置；省略时保留原渲染默认值。"""
    options = project.get("editorial", {}).get("render", {})
    allowed = {"concurrency", "parallel_encoding", "ffmpeg_threads", "node_heap_mb"}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError("editorial.render contains unsupported options")
    for key, minimum, maximum in (
        ("concurrency", 1, 8),
        ("ffmpeg_threads", 1, 64),
        ("node_heap_mb", 128, 16384),
    ):
        if key in options and (
            type(options[key]) is not int or not minimum <= options[key] <= maximum
        ):
            raise ValueError(
                f"editorial.render.{key} must be an integer in {minimum}..{maximum}"
            )
    if (
        "parallel_encoding" in options
        and type(options["parallel_encoding"]) is not bool
    ):
        raise ValueError("editorial.render.parallel_encoding must be boolean")
    return dict(options)


def _kind(scene):
    """Choose a visual grammar from the scene's meaning, with explicit overrides."""
    if scene.get("composition"):
        return scene["composition"]
    if scene.get("editorial_kind"):
        return scene["editorial_kind"]
    mode = scene.get("mode", "theme_text")
    if mode == "chart":
        return "chart"
    if scene.get("image") or scene.get("background_image"):
        return "hero"
    return (
        "flow"
        if scene.get("visual_direction", "").lower().find("流程") >= 0
        else "hero"
    )


def _story_shots(scene, base, public, index, cues, start_frame, fps):
    """Bind shot focus to measured caption cues, never an arbitrary eight seconds."""
    shots = []
    planned = scene.get("shots", [])
    for shot_index, shot in enumerate(planned):
        item = dict(shot)
        if "segment_start" in shot or "segment_end" in shot:
            first = shot.get("segment_start", 0)
            last = shot.get("segment_end", first)
            if (
                type(first) is not int
                or type(last) is not int
                or not 0 <= first <= last < len(cues)
            ):
                raise ValueError("Story shot segment indices must reference this scene")
            item["start"] = (round(cues[first]["start"] * fps) - start_frame) / fps
            item["end"] = (round(cues[last]["end"] * fps) - start_frame) / fps
        elif "start" not in shot and "end" not in shot:
            # Legacy plans get a duration-based distribution; authored bindings win.
            duration = (round(cues[-1]["end"] * fps) - start_frame) / fps
            item["start"] = duration * shot_index / len(planned)
            item["end"] = duration * (shot_index + 1) / len(planned)
        for key in ASSET_KEYS:
            if shot.get(key):
                item[key] = _copy_asset(
                    base, shot[key], public, index, f"shot-{shot_index}-{key}"
                )
        if shot.get("image"):
            item["image"] = _copy_asset(
                base,
                shot["image"],
                public,
                index,
                f"shot-{shot_index}",
            )
        shots.append(item)
    return shots


def preflight(project, base, runtime):
    """Resolve the sole renderer and independent FFprobe before audio work."""
    project = normalize_editorial(project)
    render_options(project)
    require_valid(project, base)
    _component_source(project, base)
    if project.get("narrative_version") == 1:
        manifest_path = (base / project["narrative_manifest"]).resolve()
        manifest = read_manifest(manifest_path)
        validate_manifest(manifest, manifest_path.parent)
        load_directing(project, base, manifest=manifest)
    editorial = project.get("editorial", {})
    width = editorial.get("width", 1920)
    height = editorial.get("height", 1080)
    fps = editorial.get("fps", 24)
    if (width, height, fps) != (1920, 1080, 24):
        raise ValueError("Remotion editorial currently requires 1920x1080 at 24 fps")
    install = Path(
        runtime.get(
            "remotion_install", Path.home() / ".cache/news-to-video/remotion-editorial"
        )
    ).resolve()
    cli = install / "node_modules/@remotion/cli/remotion-cli.js"
    if not cli.is_file():
        cli = install / "node_modules/@remotion/cli/dist/index.mjs"
    if not shutil.which("node") or not cli.exists():
        raise RuntimeError(
            "Remotion editorial runtime is missing; see references/remotion-editorial.md"
        )
    for index, scene in enumerate(project["scenes"]):
        if project.get("narrative_version") == 1:
            # The sealed full-frame master owns its visuals; legacy node/slot rules do not apply.
            continue
        if _kind(scene) == "flow":
            nodes = scene.get("editorial_nodes", [])
            if not isinstance(nodes, list) or not 2 <= len(nodes) <= 3:
                raise ValueError(
                    f"Scene {index + 1}: flow requires 2–3 editorial_nodes"
                )
            if any(
                not isinstance(node, dict)
                or not isinstance(node.get("title"), str)
                or not node["title"].strip()
                or not isinstance(node.get("detail", ""), str)
                for node in nodes
            ):
                raise ValueError(
                    f"Scene {index + 1}: flow nodes require a title and text detail"
                )
        if _kind(scene) == "story":
            shots = scene.get("shots", [])
            if not 2 <= len(shots) <= 4:
                raise ValueError(f"Scene {index + 1}: story requires 2–4 shots")
            if any(
                not isinstance(shot, dict) or not str(shot.get("title", "")).strip()
                for shot in shots
            ):
                raise ValueError(f"Scene {index + 1}: story shots require titles")
        if scene.get("editorial_image_fit", "contain") not in ("contain", "cover"):
            raise ValueError(f"Scene {index + 1}: unsupported editorial_image_fit")
        for key in ("image", "background_image"):
            if scene.get(key) and not (base / scene[key]).is_file():
                raise FileNotFoundError(
                    f"Scene {index + 1}: missing {key}: {scene[key]}"
                )
    probe = (
        runtime.get("ffprobe")
        or shutil.which("ffprobe")
        or (
            Path.home()
            / ".cache/news-to-video/tools"
            / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        )
    )
    if not Path(probe).is_file():
        raise RuntimeError("FFprobe is required for Remotion editorial verification")
    return install, cli, Path(probe), width, height, fps


def _copy_asset(base, source, public, index, role):
    if not source:
        return None
    path = base / source
    with Image.open(path) as image:
        extension = (
            path.suffix.lower()
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            else ".png"
        )
        target = public / f"scene-{index}-{role}{extension}"
        image.convert("RGB" if extension in (".jpg", ".jpeg") else "RGBA").save(target)
    return f"assets/{target.name}"


def _cue_frame(cue, boundary):
    key = boundary + "_frame"
    return cue[key] if key in cue else frame_at(cue[boundary])


def stage(project, cues, duration, base, folder, font):
    """Create a self-contained project; the React template owns all layout decisions."""
    project = normalize_editorial(project)
    options = render_options(project)
    public = folder / "public"
    src = folder / "src"
    public.mkdir(parents=True, exist_ok=True)
    src.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE / "Root.tsx", src / "Root.tsx")
    shutil.copyfile(TEMPLATE / "index.ts", src / "index.ts")
    shutil.copyfile(TEMPLATE / "remotion.config.ts", folder / "remotion.config.ts")
    shutil.copyfile(TEMPLATE / "package.json", folder / "package.json")
    shutil.copyfile(TEMPLATE / "tsconfig.json", folder / "tsconfig.json")
    (public / "assets").mkdir(exist_ok=True)
    shutil.copyfile(font, public / f"font{font.suffix}")
    require_valid(project, base)
    scene_payload = []
    caption_mode = project.get("editorial", {}).get("captions", "bottom_rail")
    editorial_fps = project.get("editorial", {}).get("fps", 24)
    for index, scene in enumerate(project["scenes"]):
        scene_cues = [cue for cue in cues if cue["scene"] == index]
        if not scene_cues:
            continue
        # Share rounded absolute boundaries to prevent cumulative scene drift.
        start_frame = _cue_frame(scene_cues[0], "start")
        end_frame = _cue_frame(scene_cues[-1], "end")
        item = dict(
            kind="narrative" if project.get("narrative_version") == 1 else _kind(scene),
            composition=(
                "narrative" if project.get("narrative_version") == 1 else _kind(scene)
            ),
            palette=palette_for(scene),
            story_world=scene.get("story_world", {}),
            background_style=scene.get("background_style", "plain"),
            camera_language=scene.get(
                "camera_language",
                {"slow_push": "slow-push", "slow-push": "slow-push"}.get(
                    scene.get("motion_plan", {}).get("camera"), "none"
                ),
            ),
            **{
                key: _copy_asset(base, scene.get(key), public / "assets", index, key)
                for key in ASSET_KEYS
            },
            duration=end_frame - start_frame,
            headline=scene.get("headline", ""),
            center_text=scene.get("center_text", ""),
            chapter=scene.get("chapter", ""),
            segments=[cue["text"] for cue in scene_cues],
            captions=(
                [
                    {
                        "text": cue["text"],
                        "start": _cue_frame(cue, "start") - start_frame,
                        "end": _cue_frame(cue, "end") - start_frame,
                    }
                    for cue in scene_cues
                ]
                if caption_mode == "bottom_rail"
                else []
            ),
            image=_copy_asset(
                base,
                scene.get("image") or scene.get("background_image"),
                public / "assets",
                index,
                "image",
            ),
            data=scene.get("data", []),
            unit=scene.get("unit", ""),
            source=scene.get("data_source", ""),
            nodes=scene.get("editorial_nodes", []),
            comparison_labels=scene.get("comparison_labels", ["对照 A", "对照 B"]),
            field_mapping_notes=scene.get("field_mapping_notes", []),
            image_fit=scene.get("editorial_image_fit", "contain"),
            summary=scene.get("editorial_summary", ""),
            visual_strategy=scene.get("visual_strategy", ""),
            motion_plan=scene.get("motion_plan", {}),
            shots=(
                _story_shots(
                    scene,
                    base,
                    public / "assets",
                    index,
                    scene_cues,
                    start_frame,
                    editorial_fps,
                )
                if scene.get("shots")
                else []
            ),
        )
        if scene.get("object_stage"):
            item["object_stage"] = measured_stage(
                scene, scene_cues, start_frame, editorial_fps
            )
            for object_index, obj in enumerate(item["object_stage"]["objects"]):
                if obj.get("asset"):
                    obj["asset"] = _copy_asset(
                        base,
                        obj["asset"],
                        public / "assets",
                        index,
                        f"object-{object_index}",
                    )
        shots = item["shots"]
        if project.get("visual_contract_version"):
            boundaries = [
                (
                    round(shot["start"] * editorial_fps),
                    round(shot["end"] * editorial_fps),
                )
                for shot in shots
            ]
            if (
                not boundaries
                or boundaries[0][0] != 0
                or boundaries[-1][1] != item["duration"]
                or any(end <= start for start, end in boundaries)
                or any(
                    left[1] != right[0]
                    for left, right in zip(boundaries, boundaries[1:])
                )
            ):
                raise ValueError(
                    "Shot frame boundaries must cover the measured scene continuously"
                )
        scene_payload.append(item)
    payload = dict(
        font_asset=f"font{font.suffix}",
        scenes=scene_payload,
        width=project.get("editorial", {}).get("width", 1920),
        height=project.get("editorial", {}).get("height", 1080),
        fps=project.get("editorial", {}).get("fps", 24),
    )
    if options:
        payload["render_options"] = options
    if project.get("narrative_version") == 1:
        payload["narrative_shots"] = stage_manifest(
            project, base, public, round(duration * editorial_fps)
        )
        payload["narrative_cues"] = cues
        payload["narrative_version"] = 1
        if project.get("narrative_directing"):
            payload["narrative_directing"] = stage_directing(
                project, base, public, round(duration * editorial_fps)
            )
    (src / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "visual-diversity-report.json").write_text(
        json.dumps(require_valid(project, base), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.copyfile(TEMPLATE / "Composition.tsx", src / "Composition.tsx")
    shutil.copyfile(TEMPLATE / "EditorialPanels.tsx", src / "EditorialPanels.tsx")
    shutil.copyfile(TEMPLATE / "caption-layout.ts", src / "caption-layout.ts")
    shutil.copyfile(TEMPLATE / "JointOverlay.tsx", src / "JointOverlay.tsx")
    shutil.copyfile(TEMPLATE / "ObjectStage.tsx", src / "ObjectStage.tsx")
    custom = _component_source(project, base)
    custom_path = src / "custom"
    custom_target = custom_path.resolve()
    if (
        custom_target.parent != src.resolve()
        or custom_path.is_symlink()
        or custom_path.is_junction()
    ):
        raise ValueError(
            "Generated custom directory must be a real child of the stage src"
        )
    if custom and (
        custom == custom_target
        or custom_target in custom.parents
        or custom in custom_target.parents
    ):
        raise ValueError(
            "Custom source and generated custom directory must be separate"
        )
    if custom_target.exists():
        # Only this renderer-owned child is cleared; no user source is ever removed.
        shutil.rmtree(custom_target)
    if custom:
        # A project may author its visual stage; the shared wrapper still owns captions.
        # Re-stage from source on every run, never rely on edits to generated output.
        for path in custom.rglob("*"):
            if path.is_file() and path.suffix in (".tsx", ".ts", ".css"):
                relative = path.relative_to(custom)
                if any(part in ("node_modules", ".git") for part in relative.parts):
                    continue
                destination = src / "custom" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
    (src / "ProjectStage.tsx").write_text(
        (
            'export {default} from "./custom/Stage";\n'
            if custom
            else 'export {ObjectStage as default} from "./ObjectStage";\n'
        ),
        encoding="utf-8",
    )
    return payload


def _component_source(project, base):
    """Resolve explicit trusted local source, independent of the generated checkout."""
    value = project.get("editorial", {}).get("component_dir")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("editorial.component_dir must name a local source directory")
    source = (base / value).resolve()
    if not source.is_dir() or not (source / "Stage.tsx").is_file():
        raise ValueError("Custom component directory requires Stage.tsx default export")
    return source


def render(install, cli, folder, silent, payload, log):
    """Render only pictures; audio is muxed by news-to-video after this step."""
    environment = {**os.environ, "REMOTION_DISABLE_TELEMETRY": "1"}
    options = render_options(
        {"editorial": {"render": payload.get("render_options", {})}}
    )
    if "node_heap_mb" in options:
        environment["NODE_OPTIONS"] = (
            environment.get("NODE_OPTIONS", "")
            + f" --max-old-space-size={options['node_heap_mb']}"
        ).strip()
    if "ffmpeg_threads" in options:
        # 只扩展本次生成工程的配置；不修改公共模板或系统全局设置。
        config = folder / "remotion.config.ts"
        threads = str(options["ffmpeg_threads"])
        config.write_text(
            config.read_text(encoding="utf-8")
            + "\nConfig.overrideFfmpegCommand(({args}) => [...args.slice(0, -1), "
            + f'"-threads", "{threads}", "-filter_threads", "1", '
            + "args[args.length - 1]]);\n",
            encoding="utf-8",
        )
    props_file = folder / "props.json"
    props_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    command = [
        "node",
        str(cli),
        "render",
        "src/index.ts",
        "Editorial",
        str(silent),
        "--props",
        str(props_file),
        "--codec",
        "h264",
        "--color-space",
        "bt709",
        "--concurrency",
        str(options.get("concurrency", 2)),
        "--log",
        "verbose",
    ]
    if options.get("parallel_encoding") is False:
        command.append("--disallow-parallel-encoding")
    if payload.get("narrative_version") == 1:
        command.extend(["--image-format", "png"])
    browser = environment.get("NEWS_TO_VIDEO_BROWSER")
    if browser:
        if not Path(browser).is_file():
            raise ValueError("NEWS_TO_VIDEO_BROWSER must point to an existing browser")
        # The explicit CLI override also works when the global CLI resolves config elsewhere.
        command.extend(["--browser-executable", browser])
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            cwd=folder,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
    if result.returncode:
        raise RuntimeError(f"Remotion editorial render failed; see {log}")


def verify(path, ffprobe, width, height, fps, frames):
    metadata = json.loads(
        subprocess.check_output(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height,r_frame_rate,nb_frames",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )
    stream = metadata["streams"][0]
    expected = {
        "codec_type": "video",
        "width": width,
        "height": height,
        "r_frame_rate": f"{fps}/1",
        "nb_frames": str(frames),
    }
    if any(stream.get(key) != value for key, value in expected.items()):
        raise ValueError(
            f"Remotion stream does not match editorial metadata: {metadata}"
        )


def render_key(folder, payload, version="remotion-editorial-v1"):
    # Retain prior immutable sequence versions for recovery without hashing unused versions.
    live_frames = {
        "public/" + frame
        for shot in payload.get("narrative_shots", [])
        for frame in shot["frames"]
    }
    files = {
        str(file.relative_to(folder)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in folder.rglob("*")
        if file.is_file()
        and (
            not file.relative_to(folder).as_posix().startswith("public/narrative/")
            or file.relative_to(folder).as_posix() in live_frames
        )
        and file.name not in ("props.json", "mix.wav")
        and "node_modules" not in file.parts
        and ".remotion" not in file.parts
    }
    return hashlib.sha256(
        json.dumps(
            [version, payload, files], sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


def preview_frame(ffmpeg, path, frame):
    """Extract an encoded frame for the storyboard; preview pixels come from the new engine."""
    target = path.with_name(f"editorial-preview-{frame}.png")
    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-v",
            "error",
            "-ss",
            f"{frame / 24:.6f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=270:152",
            str(target),
        ],
        check=True,
    )
    with Image.open(target) as image:
        return image.convert("RGB")
