"""Prepare a two-second synthetic render without TTS or any media inputs."""

import argparse
import hashlib
import json
import wave
from pathlib import Path

SAMPLE_RATE = 24000
SAMPLES = 2 * SAMPLE_RATE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    job = parser.parse_args().job
    job.mkdir(parents=True, exist_ok=False)
    voice = job / "silence.wav"
    with wave.open(str(voice), "wb") as silence:
        silence.setparams((1, 2, SAMPLE_RATE, SAMPLES, "NONE", "not compressed"))
        silence.writeframes(bytes(SAMPLES * 2))
    template = Path(__file__).with_name("project.json")
    project = json.loads(template.read_text(encoding="utf8"))
    project["voice"] = {
        "mode": "external_final",
        "path": voice.name,
        "sha256": hashlib.sha256(voice.read_bytes()).hexdigest(),
        "sample_rate": SAMPLE_RATE,
        "samples": SAMPLES,
        "channels": 1,
        "playback_rate": 1.0,
        "processing_identity": {"mode": "synthetic silence", "duration_seconds": 2},
        "cues": "cues.json",
    }
    text = "合成测试 · 检查字幕与作业入口"
    project["scenes"][0]["segments"][0].update(text=text, spoken=text)
    cues = [{"scene": 0, "text": text, "start": 0, "end": 2}]
    for name, value in (("project.json", project), ("cues.json", cues)):
        (job / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )


if __name__ == "__main__":
    main()
