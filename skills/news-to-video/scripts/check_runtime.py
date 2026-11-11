"""检查渲染环境与唯一 B 配音后端；不读取旧引擎或选择备用声音。"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import imageio_ffmpeg
from PIL import ImageFont

from music_bed import select_track
from voice_backend import load_profile, read_json
from remotion_visual import preflight


def check(runtime_path):
    runtime = read_json(runtime_path)
    preflight({"scenes": []}, Path(runtime_path).parent, runtime)
    _, identity = load_profile(runtime)
    ImageFont.truetype(runtime["font"], 40)
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-version"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    _, track = select_track({}, runtime, "runtime-check")
    # 临时请求只含本机配置，检查结束清理；参考音频不会上传。
    with tempfile.TemporaryDirectory(prefix="news-video-check-") as temporary:
        request = Path(temporary) / "request.json"
        request.write_text(json.dumps({"runtime": runtime}), encoding="utf-8")
        subprocess.run(
            [
                runtime["tts_python"],
                "-X",
                "utf8",
                str(Path(__file__).with_name("qwen_synth.py")),
                str(request),
                "--check",
            ],
            check=True,
        )
    print(
        json.dumps(
            {
                "ok": True,
                "python": sys.executable,
                "voice_id": identity["voice_id"],
                "visual_engine": "remotion_editorial",
                "fallback_voice": None,
                "music_track": track["id"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        default=os.environ.get(
            "NEWS_TO_VIDEO_RUNTIME",
            str(Path.home() / ".cache/news-to-video/runtime.json"),
        ),
    )
    args = parser.parse_args()
    check(args.runtime)
