"""Build a portable synthetic external_final project with one cue-bound effect."""

import argparse
import json
from pathlib import Path
import shutil
import sys
import wave

import numpy as np

SKILL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / "scripts"))
from frozen_audio import file_hash
from object_contract import measured_stage

RATE = 24000
FPS = 24
FIXTURE = "合成示例，仅用于验证动画与音频消费者"


def write_wav(path, pcm):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(pcm.astype("<i2").tobytes())


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build(work):
    work.mkdir(parents=True, exist_ok=False)
    (work / "components").mkdir()
    shutil.copyfile(
        Path(__file__).with_name("Stage.tsx"), work / "components/Stage.tsx"
    )

    events = [
        ("module", "模块入位", "合成演示中，模块由外部滑入设备端口。"),
        ("route", "链路连通", "模块入位后，演示连线在两个端口之间逐渐显现。"),
        ("release", "条件满足", "条件满足后，示意时间轴上的交付节点前移。"),
    ]
    cues = [
        {"scene": 0, "text": text, "start": index * 4, "end": (index + 1) * 4}
        for index, (_, _, text) in enumerate(events)
    ]
    samples = cues[-1]["end"] * RATE
    write_wav(work / "dry.wav", np.zeros(samples))
    write_json(work / "cues.json", cues)

    scene = {
        "chapter": "对象与状态 · 合成示例",
        "headline": "看见三个变化",
        "composition": "object_stage",
        "story_world": {"id": "synthetic-module"},
        "data_source": FIXTURE,
        "segments": [{"text": cue["text"]} for cue in cues],
        "shots": [
            {
                "title": "模块、连线与交付节点",
                "segment_start": 0,
                "segment_end": 2,
                "progression": "先观察模块入位，再揭示链路，最后移动交付点。",
            }
        ],
        "object_stage": {
            "objects": [
                {
                    "id": key,
                    "kind": "box",
                    "label": label,
                    "x": 300 + index * 400,
                    "y": 250,
                }
                for index, (key, label, _) in enumerate(events)
            ],
            "actions": [
                {
                    "target": key,
                    "type": "state",
                    "segment": index,
                    "label": label,
                    "tone": "accent",
                    "at": 0.2,
                    "until": 0.66,
                    "evidence": FIXTURE,
                }
                for index, (key, label, _) in enumerate(events)
            ],
        },
    }
    stage = measured_stage(scene, cues, 0, FPS)
    connection = next(
        action for action in stage["actions"] if action["target"] == "route"
    )
    duration = 0.45
    t = np.arange(round(RATE * duration)) / RATE
    pulse = 5000 * np.sin(np.pi * t / duration) ** 2 * np.sin(2 * np.pi * 411 * t)
    write_wav(work / "pulse.wav", pulse)
    project = {
        "title": "对象与状态 · 合成示例",
        "production_mode": "daily_editorial",
        "visual_contract_version": 2,
        "editorial": {
            "component_dir": "components",
            "width": 1920,
            "height": 1080,
            "fps": FPS,
            "captions": "bottom_rail",
            "render": {
                "concurrency": 1,
                "parallel_encoding": False,
                "ffmpeg_threads": 2,
            },
        },
        "voice": {
            "mode": "external_final",
            "path": "dry.wav",
            "cues": "cues.json",
            "sha256": file_hash(work / "dry.wav"),
            "sample_rate": RATE,
            "samples": samples,
            "channels": 1,
            "playback_rate": 1.0,
            "processing_identity": {"synthetic_silence": True},
        },
        "music": {"mode": "off"},
        "sound_tracks": [
            {
                "track_id": "connection-pulse",
                "kind": "effect",
                "path": "pulse.wav",
                "sha256": file_hash(work / "pulse.wav"),
                "start": connection["end_frame"] / FPS,
                "duration": duration,
                "gain_db": -15,
                "source_url": "synthetic:connection-pulse",
                "license": "MIT",
                "attribution": "Daily Media Lab synthetic tone",
                "purpose": "提示光路动作完成",
            }
        ],
        "scenes": [scene],
    }
    write_json(work / "project.json", project)
    print(work / "project.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work", type=Path, required=True, help="New example workspace"
    )
    build(parser.parse_args().work.resolve())
