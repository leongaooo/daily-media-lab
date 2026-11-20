"""创建一秒静音external_final输入，核验实际源与联合投影；不调用TTS或渲染。"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave

SAMPLE_RATE = 24000
SAMPLES = 24000
FRAMES = 24
CAPTION = "联合事件技术测试 · 一秒静音非口播"


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def prepare(output):
    """先验证生成源／投影，再写入新冻结输入；不伪造媒体或成功回执。"""
    output = Path(output).resolve()
    names = ("shots.json", "projection.json", "directing.json", "joint-technical.blend")
    missing = [name for name in names if not (output / name).is_file()]
    if missing:
        raise ValueError(
            f"Run generate_scene.py first; missing generated inputs: {missing}"
        )
    existing = [
        name
        for name in ("silence.wav", "cues.json", "project.json")
        if (output / name).exists()
    ]
    if existing:
        raise ValueError(
            f"Frozen input already exists; use a new output directory: {existing}"
        )

    # 与真实渲染共享校验器；路径从公开仓结构定位，不依赖安装盘符或私有runtime。
    scripts = (
        Path(__file__).resolve().parents[2] / "skills" / "news-to-video" / "scripts"
    )
    sys.path.insert(0, str(scripts))
    from joint_directing import load_directing
    from narrative_media import read_json, validate_manifest

    project = {
        "title": "原创联合事件技术测试",
        "narrative_version": 1,
        "narrative_manifest": "shots.json",
        "narrative_directing": "directing.json",
        "production_mode": "daily_editorial",
        "music": {"mode": "off"},
        "scenes": [{"headline": "技术测试 · 非新闻", "segments": [{"text": CAPTION}]}],
    }
    manifest = read_json(output / "shots.json")
    validate_manifest(manifest, output, total_frames=FRAMES, check_frames=False)
    load_directing(project, output, manifest=manifest, total_frames=FRAMES)

    audio = output / "silence.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(b"\x00\x00" * SAMPLES)
    project["voice"] = {
        "mode": "external_final",
        "path": audio.name,
        "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
        "sample_rate": SAMPLE_RATE,
        "samples": SAMPLES,
        "channels": 1,
        "processing_identity": {
            "fixture": "original-silence-not-narration",
            "license": "MIT",
            "purpose": "joint event, projection and cache technical smoke only",
        },
        "playback_rate": 1.0,
        "cues": "cues.json",
    }
    write_json(
        output / "cues.json",
        [{"scene": 0, "text": CAPTION, "start": 0, "end": SAMPLES / SAMPLE_RATE}],
    )
    write_json(output / "project.json", project)
    print(
        "Prepared one-second original silence and exact cue; no TTS, images or render started."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="generate_scene.py创建的同一目录"
    )
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    main()
