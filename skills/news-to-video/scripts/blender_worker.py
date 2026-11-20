"""仅由Blender执行；不修改源blend，成功写帧后原子更新同身份回执。"""

import hashlib
import json
from pathlib import Path
import struct
import sys
import time

import bpy


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def main():
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    path = Path(arguments[0]).resolve()
    shot = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8-sig"))["shots"]
        if item["shot_id"] == arguments[1]
    )
    base = path.parent
    for source in [shot["source"], *shot["dependencies"]]:
        if sha(base / source["path"]) != source["sha256"]:
            raise ValueError("Source changed before Blender render")
    identity = hashlib.sha256(
        json.dumps(
            {
                "worker_sha256": sha(Path(__file__).resolve()),
                "shot": {
                    **{
                        key: shot[key]
                        for key in (
                            "source",
                            "dependencies",
                            "render",
                            "media",
                            "start_frame",
                            "end_frame",
                            "handles",
                        )
                    },
                    # 与narrative_media.source_identity保持相同的可选摄影契约。
                    **{
                        key: shot[key]
                        for key in (
                            "camera_sha256",
                            "camera_events_sha256",
                            "camera_event_names",
                        )
                        if key in shot
                    },
                },
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    settings, media = shot["render"], shot["media"]
    if bpy.app.version_string != settings["blender_version"]:
        raise ValueError(
            f"Expected Blender {settings['blender_version']}, got {bpy.app.version_string}"
        )
    scene = bpy.context.scene
    scene.render.engine = settings["engine"]
    scene.render.resolution_x = settings["width"]
    scene.render.resolution_y = settings["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = str(media["bit_depth"])
    scene.render.film_transparent = False
    scene.view_settings.view_transform = settings["display_transform"]
    scene.view_settings.look = settings["look"]
    scene.view_settings.exposure = settings["exposure"]
    scene.view_settings.gamma = settings["gamma"]
    if settings["engine"] == "CYCLES":
        scene.cycles.seed = settings["seed"]
        scene.cycles.samples = settings["samples"]
        scene.cycles.use_denoising = settings["denoise"]
        scene.cycles.device = settings.get("device", "CPU")
    elif settings["engine"] == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = settings["samples"]
        # EEVEE has no Cycles-style denoiser/seed; unsupported claims fail explicitly.
        if settings["denoise"] or settings["seed"] != 0:
            raise ValueError("EEVEE v1 requires denoise=false and seed=0")
    else:
        raise ValueError("Only explicitly tested EEVEE/Cycles are supported")
    receipt_path = base / shot["receipt"]
    receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    if receipt.get("identity") != identity:
        receipt = {"identity": identity, "frames": {}, "timings": {}}
    receipt.setdefault("timings", {})
    first = media["source_first_frame"]
    for frame in range(first, first + shot["end_frame"] - shot["start_frame"]):
        target = base / (media["pattern"] % frame)
        key = str(target.relative_to(base)).replace("\\", "/")
        if target.is_file() and receipt["frames"].get(key) == sha(target):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.stem + ".partial.png")
        scene.frame_set(frame)
        scene.render.filepath = str(temporary)
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        with temporary.open("rb") as stream:
            header = stream.read(26)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(
            ">IIB", header[16:25]
        ) != (settings["width"], settings["height"], media["bit_depth"]):
            raise ValueError("Blender wrote an invalid frame")
        temporary.replace(target)
        receipt["frames"][key] = sha(target)
        receipt["timings"][key] = time.monotonic() - started
        save(receipt_path, receipt)


if __name__ == "__main__":
    main()
