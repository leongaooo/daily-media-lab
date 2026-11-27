"""Build the composition project and the common integer-frame timing."""

import argparse
import hashlib
import json
from pathlib import Path

import soundfile


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def identity(path, root):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": path.relative_to(root).as_posix(), "sha256": digest}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--voice-id", default="qwen-uncle-fu-v1")
    parser.add_argument("--tempo", type=float, default=1.15)
    args = parser.parse_args()
    job = args.job
    cues = read(job / "audio/cues.json")
    boundaries = [cue["start_frame"] for cue in cues] + [cues[-1]["end_frame"]]
    if (
        len(boundaries) != 9
        or min(b - a for a, b in zip(boundaries, boundaries[1:])) < 25
    ):
        raise ValueError(
            "The design requires eight frozen cues, each longer than the zoom ramp"
        )
    write(job / "timing.json", {"fps": 24, "boundaries": boundaries})
    if not args.manifest:
        return
    shots = []
    for shot_id, start, end, source, evidence, kind, label, boundary in (
        (
            "topology",
            0,
            2,
            "visuals.py",
            "XTX-OPEN-1124",
            "explanation",
            "启用与功率容量",
            "IT 功率容量不等于瞬时负载",
        ),
        (
            "retrofit",
            2,
            6,
            "visuals.py",
            "KAJAANI-CITY-0122",
            "explanation",
            "首座与第二座的状态对照",
            "第二座仍为 2027 年计划",
        ),
        (
            "route",
            6,
            8,
            "kajaani.blend",
            "KAJAANI-CITY-0122",
            "metaphor",
            "概念场景",
            "建筑布局、设备结构和路线为原创示意",
        ),
    ):
        is_3d = shot_id == "route"
        dependency_names = (
            ["campus.py", "visuals.py", "mixed_shot.py", "mixed_shot_blender.py"]
            if is_3d
            else ["mixed_shot.py"]
        )
        dependencies = [
            identity(job / "source" / name, job) for name in dependency_names
        ]
        if is_3d:
            dependencies.append(identity(job / "projection.json", job))
        else:
            dependencies.append(identity(job / "source/rack.svg", job))
        dependencies.append(identity(job / "timing.json", job))
        shots.append(
            {
                "shot_id": shot_id,
                "story_world": shot_id,
                "start_frame": boundaries[start],
                "end_frame": boundaries[end],
                "source": identity(job / "source" / source, job),
                "dependencies": dependencies,
                "render": {
                    "blender_version": "4.4.3" if is_3d else "not-used",
                    "engine": "BLENDER_WORKBENCH plus SVG" if is_3d else "Chromium SVG",
                    "seed": 0,
                    "samples": 8 if is_3d else 1,
                    "denoise": False,
                    "width": 1920,
                    "height": 1080,
                    "fps": 24,
                    "display_transform": "Standard",
                    "look": "None",
                    "exposure": 0,
                    "gamma": 1,
                },
                "media": {
                    "role": "master",
                    "pattern": f"frames/{shot_id}/%06d.png",
                    "source_first_frame": 1,
                    "bit_depth": 8,
                    "color_space": "display-srgb",
                    "alpha": "opaque",
                },
                "handles": {"head": 0, "tail": 0},
                "facts": {
                    "kind": kind,
                    "label": label,
                    "evidence_ids": [evidence],
                    "prohibited_implications": [boundary],
                },
                "receipt": f"receipts/{shot_id}.json",
            }
        )
    write(job / "shots.json", {"schema_version": 1, "fps": 24, "shots": shots})

    project = read(job / "narration.json")
    wave = job / "audio/voice.wav"
    info = soundfile.info(wave)
    project.update(
        narrative_version=1,
        narrative_manifest="shots.json",
        music={"mode": "off"},
        voice={
            "mode": "external_final",
            **identity(wave, job),
            "sample_rate": info.samplerate,
            "samples": info.frames,
            "channels": info.channels,
            "playback_rate": 1.0,
            "processing_identity": {
                "voice_id": args.voice_id,
                "tempo_applied": args.tempo,
            },
            "cues": "audio/cues.json",
        },
        editorial={
            "captions": "bottom_rail",
            "render": {
                "concurrency": 1,
                "parallel_encoding": False,
                "ffmpeg_threads": 2,
            },
        },
    )
    write(job / "project.json", project)


if __name__ == "__main__":
    main()
