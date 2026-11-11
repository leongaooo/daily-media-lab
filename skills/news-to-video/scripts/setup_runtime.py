"""连接已安装的渲染/Qwen 环境与认可的 B 参考，不安装旧语音引擎。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid

from voice_backend import file_hash, read_json, load_profile


def setup(args):
    skill = Path(__file__).resolve().parent.parent
    cache = Path(args.cache).resolve()
    policy = read_json(skill / "assets/voice-policy.json")
    font = Path(args.font).resolve()
    render_python = Path(args.render_python).resolve()
    tts_python = Path(args.tts_python).resolve()
    model = Path(args.model).resolve()
    reference = Path(args.reference).resolve()
    text = Path(args.reference_text).read_text(encoding="utf-8-sig").strip()
    for path in (font, render_python, tts_python, reference):
        if not path.is_file():
            raise FileNotFoundError(path)
    if file_hash(reference) != policy["reference_sha256"]:
        raise ValueError(
            "Reference is not the approved B voice; existing configuration was not changed"
        )
    if hashlib.sha256(text.encode()).hexdigest() != policy["reference_text_sha256"]:
        raise ValueError("Reference transcript is not the approved B transcript")
    # 每次设置先创建独立候选；全部检查成功后才原子切换运行指针。
    # 错误输入或环境故障不能覆盖此前已可用的私有参考与运行配置。
    profile_dir = cache / "profiles/b-male-v1" / uuid.uuid4().hex
    profile_dir.mkdir(parents=True, exist_ok=True)
    target = profile_dir / "reference.wav"
    shutil.copy2(reference, target)
    profile = {
        "id": policy["voice_id"],
        "model_dir": str(model),
        "reference_audio": str(target),
        "reference_text": text,
        "settings": policy["settings"],
    }
    profile_path = profile_dir / "profile.json"
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    runtime = {
        "python": str(render_python),
        "tts_python": str(tts_python),
        "font": str(font),
        "voice_id": policy["voice_id"],
        "voice_profile": str(profile_path),
        "music_manifest": str(skill / "assets/music-pool/manifest.json"),
    }
    candidate_runtime = profile_dir / "pending-runtime.json"
    candidate_runtime.write_text(
        json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        load_profile(runtime)
        subprocess.run(
            [
                str(render_python),
                str(skill / "scripts/check_runtime.py"),
                "--runtime",
                str(candidate_runtime),
            ],
            check=True,
        )
    except Exception:
        # 只清理本次创建的三个文件，不递归删除其他配置或历史版本。
        for path in (candidate_runtime, profile_path, target):
            path.unlink(missing_ok=True)
        profile_dir.rmdir()
        raise
    runtime_path = cache / "runtime.json"
    if runtime_path.exists():
        shutil.copy2(runtime_path, cache / f"runtime.before-{profile_dir.name}.json")
    candidate_runtime.replace(runtime_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default=str(Path.home() / ".cache/news-to-video"))
    for option in (
        "font",
        "render-python",
        "tts-python",
        "model",
        "reference",
        "reference-text",
    ):
        parser.add_argument(f"--{option}", required=True)
    setup(parser.parse_args())
