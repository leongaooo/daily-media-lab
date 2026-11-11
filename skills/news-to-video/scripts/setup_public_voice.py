"""为公开内置音色创建独立 runtime；不覆盖默认私人配置，不自动下载模型。"""

import argparse
import json
from pathlib import Path
import sys
import uuid

from public_voice import PUBLIC_VOICE_ID, download_model, load_public_profile


def setup_public(args):
    """校验固定模型后写入可复用配置；渲染/设备预检仍由 check_runtime 执行。"""
    model = Path(args.model).resolve()
    if args.download:
        download_model(model)
    cache = Path(args.cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    profile_path = cache / f"profile-{uuid.uuid4().hex}.json"
    runtime = {
        "python": str(Path(args.render_python).resolve()),
        "tts_python": str(Path(args.tts_python).resolve()),
        "font": str(Path(args.font).resolve()),
        "voice_id": PUBLIC_VOICE_ID,
        "voice_profile": str(profile_path),
        "music_manifest": str(
            Path(__file__).resolve().parents[1] / "assets/music-pool/manifest.json"
        ),
    }
    if args.ffprobe:
        runtime["ffprobe"] = str(Path(args.ffprobe).resolve())
    for key in ("python", "tts_python", "font"):
        if not Path(runtime[key]).is_file():
            raise FileNotFoundError(runtime[key])
    profile_path.write_text(
        json.dumps({"id": PUBLIC_VOICE_ID, "model_dir": str(model)}, indent=2),
        encoding="utf-8",
    )
    candidate = cache / f"pending-{profile_path.stem}.json"
    try:
        load_public_profile(runtime)
        candidate.write_text(json.dumps(runtime, indent=2), encoding="utf-8")
        candidate.replace(cache / "runtime.json")
    except Exception:
        profile_path.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)
        raise
    print(
        f"Public runtime saved: {cache / 'runtime.json'}; "
        "device preflight still required"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache", default=str(Path.home() / ".cache/news-to-video/public-voice")
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--render-python", default=sys.executable)
    parser.add_argument("--tts-python", required=True)
    parser.add_argument("--font", required=True)
    parser.add_argument("--ffprobe")
    setup_public(parser.parse_args())
