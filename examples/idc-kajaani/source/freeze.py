"""Freeze the explicitly selected public narration into measured cues and PCM."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--scripts", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.scripts.resolve()))
    from render import prepare_narration
    from voice_backend import validate_voice

    project = json.loads((args.job / "narration.json").read_text(encoding="utf-8"))
    if project["voice"]["id"] != "qwen-uncle-fu-v1":
        raise ValueError("This example requires the public voice profile")
    runtime = json.loads(args.runtime.read_text(encoding="utf-8-sig"))
    validate_voice(project)
    audio = args.job / "audio"
    cache = audio / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    duration, _, _, cues, sample_rate, _ = prepare_narration(
        project, runtime, cache, args.job, audio, 24
    )
    (audio / "cues.json").write_text(
        json.dumps(cues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Frozen public narration: {duration:.3f} seconds, {sample_rate} Hz, {len(cues)} cues"
    )


if __name__ == "__main__":
    main()
