"""检查渲染与所选声音分支；冻结音频不依赖TTS，显式公开声音保留独立身份。"""

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
from frozen_audio import external_mode, load_final


def check(runtime_path, project_path=None):
    runtime = read_json(runtime_path)
    project = read_json(project_path) if project_path else {"scenes": []}
    preflight(
        project,
        (
            Path(project_path).resolve().parent
            if project_path
            else Path(runtime_path).parent
        ),
        runtime,
    )
    if external_mode(project):
        _, _, _, _, _, identity, _ = load_final(
            project, Path(project_path).resolve().parent
        )
        ImageFont.truetype(runtime["font"], 40)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "external_final",
                    "tts_invoked": False,
                    "sha256": identity["sha256"],
                }
            )
        )
        return
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
    parser.add_argument(
        "--project", help="Check final-audio project without a TTS environment"
    )
    args = parser.parse_args()
    check(args.runtime, args.project)
