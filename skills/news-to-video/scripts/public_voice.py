"""公开内置音色边界：固定上游、权重和采样身份，不读取私人参考。"""

import hashlib
import json
from pathlib import Path
import urllib.request


PUBLIC_VOICE_ID = "qwen-uncle-fu-v1"
POLICY_PATH = Path(__file__).resolve().parents[1] / "assets/public-voice-policy.json"


def policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_public_profile(runtime, verify_weights=True):
    """仅接收模型目录；公开模式不能夹带参考录音或任意采样覆盖。"""
    profile = json.loads(Path(runtime["voice_profile"]).read_text(encoding="utf-8-sig"))
    if set(profile) != {"id", "model_dir"} or profile["id"] != PUBLIC_VOICE_ID:
        raise ValueError("Public profile only accepts id and model_dir; no reference audio")
    pinned = policy()
    model = Path(profile["model_dir"])
    for relative, expected in pinned["files"].items():
        path = model / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        # 父进程已校验大权重；子进程仍核验影响推理的小配置。
        if verify_weights or path.suffix != ".safetensors":
            if checksum(path) != expected:
                raise ValueError(f"Pinned public model checksum mismatch: {relative}")
    profile.update(
        settings=pinned["settings"],
        speaker=pinned["speaker"],
        language=pinned["language"],
    )
    identity = {
        "backend": "qwen-custom-voice-v1",
        "voice_id": PUBLIC_VOICE_ID,
        "model": pinned["model"],
        "revision": pinned["revision"],
        "model_sha256": pinned["files"],
        "speaker": pinned["speaker"],
        "language": pinned["language"],
        "settings": pinned["settings"],
        "license": pinned["license"],
        "source_url": pinned["source_url"],
        "postprocess": "boundary-trim-0.003-pad-0.12-0.20-peak-0.89-v1",
    }
    return profile, identity


def download_model(destination):
    """显式下载固定版本；逐文件校验后替换，中断不留下可用的伪权重。"""
    pinned = policy()
    destination = Path(destination).resolve()
    for relative, expected in pinned["files"].items():
        target = destination / relative
        if target.is_file() and checksum(target) == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".partial")
        url = (
            f"https://huggingface.co/{pinned['model']}/resolve/"
            f"{pinned['revision']}/{relative}"
        )
        print(f"Downloading pinned public model file: {relative}", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                with temporary.open("wb") as stream:
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk)
            if checksum(temporary) != expected:
                raise ValueError(f"Downloaded public model checksum mismatch: {relative}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
