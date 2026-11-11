"""Stage and render the document-driven Remotion editorial composition."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image


TEMPLATE = Path(__file__).resolve().parents[1] / "assets/remotion-editorial"


def _kind(scene):
    """Choose a visual grammar from the scene's meaning, with explicit overrides."""
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


def preflight(project, base, runtime):
    """Resolve the sole renderer and independent FFprobe before audio work."""
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
        image.convert("RGBA").save(target)
    return f"assets/{target.name}"


def stage(project, cues, duration, base, folder, font):
    """Create a self-contained project; the React template owns all layout decisions."""
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
    scene_payload = []
    caption_mode = project.get("editorial", {}).get("captions", "bottom_rail")
    editorial_fps = project.get("editorial", {}).get("fps", 24)
    for index, scene in enumerate(project["scenes"]):
        scene_cues = [cue for cue in cues if cue["scene"] == index]
        if not scene_cues:
            continue
        # Share rounded absolute boundaries to prevent cumulative scene drift.
        start_frame = round(scene_cues[0]["start"] * editorial_fps)
        end_frame = round(scene_cues[-1]["end"] * editorial_fps)
        item = dict(
            kind=_kind(scene),
            duration=end_frame - start_frame,
            headline=scene.get("headline", ""),
            center_text=scene.get("center_text", ""),
            chapter=scene.get("chapter", ""),
            segments=[cue["text"] for cue in scene_cues],
            captions=(
                [
                    {
                        "text": cue["text"],
                        "start": round(cue["start"] * editorial_fps) - start_frame,
                        "end": round(cue["end"] * editorial_fps) - start_frame,
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
            image_fit=scene.get("editorial_image_fit", "contain"),
            summary=scene.get("editorial_summary", ""),
        )
        scene_payload.append(item)
    payload = dict(
        scenes=scene_payload,
        width=project.get("editorial", {}).get("width", 1920),
        height=project.get("editorial", {}).get("height", 1080),
        fps=project.get("editorial", {}).get("fps", 24),
    )
    (src / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copyfile(TEMPLATE / "Composition.tsx", src / "Composition.tsx")
    return payload


def render(install, cli, folder, silent, payload, log):
    """Render only pictures; audio is muxed by news-to-video after this step."""
    environment = {**os.environ, "REMOTION_DISABLE_TELEMETRY": "1"}
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
        "--concurrency",
        "2",
        "--log",
        "verbose",
    ]
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
    files = {
        str(file.relative_to(folder)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in folder.rglob("*")
        if file.is_file()
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
