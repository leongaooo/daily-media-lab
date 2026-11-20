"""生成一秒原创静音的external_final技术输入，不生成或冒充人声。"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000
SAMPLES = 24000
CAPTION = "色彩与帧映射技术测试 · 静音非口播"


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def prepare(output):
    """写入自有静音、准确cue和媒体项目；拒绝覆盖先前冻结音频或项目。"""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    existing = [
        name
        for name in ["silence.wav", "cues.json", "project.json"]
        if (output / name).exists()
    ]
    if existing:
        raise ValueError(
            f"Output already contains frozen input; use a new directory: {existing}"
        )
    # 场景、母版依赖及色片采样框必须由generate_scene.py真实产生，不能伪造哈希。
    manifest_path = output / "shots.json"
    patches_path = output / "patches.json"
    if not manifest_path.is_file() or not patches_path.is_file():
        raise ValueError(
            "Run generate_scene.py first to create shots.json and patches.json"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest.get("shots", [])
    if (
        manifest.get("fps") != 24
        or len(shots) != 1
        or shots[0].get("start_frame") != 0
        or shots[0].get("end_frame") != 24
    ):
        raise ValueError(
            "This silent input requires the one-second, 24-frame calibration scene"
        )
    audio = output / "silence.wav"
    sf.write(audio, np.zeros(SAMPLES), SAMPLE_RATE, subtype="PCM_16")
    write_json(
        output / "cues.json",
        [{"scene": 0, "text": CAPTION, "start": 0, "end": SAMPLES / SAMPLE_RATE}],
    )
    project = {
        "title": "原创校色卡技术测试",
        "narrative_version": 1,
        "narrative_manifest": "shots.json",
        "production_mode": "daily_editorial",
        "voice": {
            "mode": "external_final",
            "path": audio.name,
            "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            "sample_rate": SAMPLE_RATE,
            "samples": SAMPLES,
            "channels": 1,
            "processing_identity": {
                "fixture": "original-silence-not-narration",
                "license": "MIT",
                "purpose": "technical frame and color calibration only",
            },
            "playback_rate": 1.0,
            "cues": "cues.json",
        },
        "music": {"mode": "off"},
        "scenes": [
            {"headline": "技术校色卡 · 非新闻", "segments": [{"text": CAPTION}]}
        ],
    }
    write_json(output / "project.json", project)
    print(
        "Original one-second silence and exact cue prepared; no speech synthesis or private reference used."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="generate_scene.py创建的同一产物目录"
    )
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    main()
