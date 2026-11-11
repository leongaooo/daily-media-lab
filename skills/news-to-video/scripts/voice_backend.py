"""B 版唯一音色的策略、缓存与隔离进程边界；不加载旧语音引擎。"""

import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import soundfile as sf
import imageio_ffmpeg


SKILL = Path(__file__).resolve().parent.parent
VOICE_ID = "b-male-v1"
DEFAULT_SPEED = 1.15
TEMPO_VERSION = "ffmpeg-atempo-f32-v1"
DENOISE_FILTER = "afftdn=nr=8:nf=-35:tn=0:gs=6"
DENOISE_VERSION = "approved-mild-afftdn-aligned-rms-v1"


def denoise_clip(path):
    """对变速后的B干声执行已认可的轻度降噪，音乐和原始缓存不变。

    afftdn在24kHz引入600样本延迟，先补足尾部再移除延迟，保持字尾和长度。
    讲话帧RMS匹配原声，统一限峰；仅低能量音频不增益。缓存由输入内容、
    参数及处理版本决定，失败时不留下可命中的半成品。
    """
    identity = {
        "source_sha256": file_hash(path),
        "filter": DENOISE_FILTER,
        "transform": DENOISE_VERSION,
    }
    target = path.parent / f"denoise-{audio_key('denoise', identity)}.wav"
    if target.exists():
        return target
    original, sample_rate = sf.read(path, dtype="float32")
    if (
        original.ndim != 1
        or sample_rate != 24000
        or not len(original)
        or not np.isfinite(original).all()
        or np.max(np.abs(original)) >= 1
    ):
        raise ValueError(f"Invalid B voice before denoise: {path}")
    temporary = target.with_suffix(".partial.wav")
    delay = 600
    filters = (
        f"apad=pad_len={delay},{DENOISE_FILTER},"
        f"atrim=start_sample={delay}:end_sample={len(original) + delay},"
        "asetpts=PTS-STARTPTS"
    )
    try:
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-v",
                "error",
                "-y",
                "-i",
                str(path),
                "-af",
                filters,
                "-c:a",
                "pcm_f32le",
                str(temporary),
            ],
            check=True,
        )
        audio, processed_rate = sf.read(temporary, dtype="float32")
        if (
            processed_rate != sample_rate
            or audio.shape != original.shape
            or not np.isfinite(audio).all()
        ):
            raise ValueError(f"Invalid denoise output: {temporary}")
        hop = round(sample_rate * 0.02)
        frames = np.pad(original, (0, (-len(original)) % hop)).reshape(-1, hop)
        active = np.repeat(np.sqrt(np.mean(frames**2, axis=1)) > 10 ** (-36 / 20), hop)[
            : len(original)
        ]
        gain = 1.0
        if active.any():
            before_rms = float(np.sqrt(np.mean(original[active] ** 2)))
            after_rms = float(np.sqrt(np.mean(audio[active] ** 2)))
            if after_rms < 1e-8:
                raise ValueError("Denoise unexpectedly removed active B speech")
            gain = before_rms / after_rms
        gain = min(gain, 0.94 / max(float(np.max(np.abs(audio))), 1e-8))
        sf.write(temporary, audio * gain, sample_rate, subtype="FLOAT")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_voice(project):
    """仅启用 B 版；语速为独立的保留音高播放倍率。"""
    voice = project.get("voice", {})
    if not isinstance(voice, dict) or set(voice) - {"id", "speed"}:
        raise ValueError("voice only accepts id=b-male-v1 and numeric speed")
    if voice.get("id", VOICE_ID) != VOICE_ID:
        raise ValueError(
            "Only B voice b-male-v1 is enabled. Run migrate_audio.py on the legacy project."
        )
    speed = voice.get("speed", DEFAULT_SPEED)
    if (
        isinstance(speed, bool)
        or not isinstance(speed, (int, float))
        or not math.isfinite(speed)
        or not 0.5 <= speed <= 2.0
    ):
        raise ValueError("voice.speed must be a finite number between 0.5 and 2.0")


def tempo_clip(path, speed):
    """保留原生干声，按原文件内容和倍率缓存保留音高的变速副本。

    改语速不改变 Qwen 合成身份，不需再次加载模型。临时文件成功解码后
    才原子替换目标，避免中断后把半成品当缓存；音乐不经过此处理。
    """
    if speed == 1.0:
        return path
    identity = {
        "raw_sha256": file_hash(path),
        "speed": float(speed),
        "transform": TEMPO_VERSION,
    }
    key = audio_key("tempo", identity)
    target = path.parent / f"tempo-{key}.wav"
    if not target.exists():
        temporary = target.with_suffix(".partial.wav")
        try:
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(),
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(path),
                    "-af",
                    f"atempo={speed:.12g}",
                    "-c:a",
                    "pcm_f32le",
                    str(temporary),
                ],
                check=True,
            )
            audio, sample_rate = sf.read(temporary, dtype="float32")
            if (
                audio.ndim != 1
                or sample_rate != 24000
                or not len(audio)
                or not np.isfinite(audio).all()
                or np.max(np.abs(audio)) >= 1
            ):
                raise ValueError(f"Invalid tempo output: {temporary}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def load_profile(runtime, verify_weights=True):
    """核验私有参考与固定策略，返回可跨解释器使用的本地音色配置。"""
    if runtime.get("voice_id") != VOICE_ID:
        raise ValueError(
            "runtime.voice_id must be b-male-v1; legacy runtime is retired"
        )
    profile_path = Path(runtime["voice_profile"])
    profile = read_json(profile_path)
    policy = read_json(SKILL / "assets/voice-policy.json")
    if profile.get("id") != VOICE_ID:
        raise ValueError("Only the approved B voice profile is accepted")
    reference = Path(profile["reference_audio"])
    text = profile["reference_text"].strip()
    if file_hash(reference) != policy["reference_sha256"]:
        raise ValueError(
            "Reference audio differs from the approved separated-vocal B prompt"
        )
    if hashlib.sha256(text.encode()).hexdigest() != policy["reference_text_sha256"]:
        raise ValueError("B reference transcript changed")
    if profile.get("settings") != policy["settings"]:
        raise ValueError(
            "B voice generation settings changed from the approved profile"
        )
    model = Path(profile["model_dir"])
    lock = read_json(SKILL / "assets/runtime-lock.json")
    hashes = {}
    for relative, expected in lock["files"].items():
        path = model / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = file_hash(path) if verify_weights else expected
        if actual != expected:
            raise ValueError(f"Pinned Qwen weight checksum mismatch: {relative}")
        hashes[relative] = actual
    # 小配置同样影响推理；变更它们也不能命中旧音频缓存。
    for path in sorted(model.rglob("*.json")):
        if path.name != "download-provenance.json":
            hashes[str(path.relative_to(model))] = file_hash(path)
    for name in ("merges.txt", "vocab.json"):
        hashes[name] = file_hash(model / name)
    identity = {
        "backend": "qwen-b-icl-v1",
        "voice_id": VOICE_ID,
        "reference_sha256": policy["reference_sha256"],
        "reference_text_sha256": policy["reference_text_sha256"],
        "model_sha256": hashes,
        "settings": policy["settings"],
        "postprocess": "boundary-trim-0.003-pad-0.12-0.20-peak-0.89-v1",
    }
    return profile, identity


def audio_key(spoken, identity):
    payload = json.dumps([spoken, identity], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def make_voice(project, runtime, cache):
    """小批隔离进程补齐未命中片段，限制长稿的进程资源驻留。"""
    validate_voice(project)
    _, identity = load_profile(runtime)
    python = Path(runtime["tts_python"])
    if not python.is_file():
        raise FileNotFoundError(
            f"Qwen Python missing: {python}; no alternate voice fallback"
        )
    jobs = []
    pending = {}
    for scene_index, scene in enumerate(project["scenes"]):
        for segment in scene["segments"]:
            spoken = segment.get("spoken", segment["text"])
            key = audio_key(spoken, identity)
            path = cache / f"{key}.wav"
            jobs.append((scene_index, segment["text"], spoken, key, path))
            if not path.exists():
                pending[key] = {"text": spoken, "output": str(path)}
    if pending:
        request = cache / "b-voice-request.json"
        tasks = list(pending.values())
        # Windows 长稿连续生成曾在三十余段后无法分配内存。
        # 每批最多八段，进程退出释放模型及分配器；已完成的干声可续用。
        for offset in range(0, len(tasks), 8):
            request.write_text(
                json.dumps(
                    {"runtime": runtime, "jobs": tasks[offset : offset + 8]},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    str(python),
                    "-X",
                    "utf8",
                    "-X",
                    "faulthandler",
                    str(SKILL / "scripts/qwen_synth.py"),
                    str(request),
                ],
                check=True,
            )
    items = []
    speed = project.get("voice", {}).get("speed", DEFAULT_SPEED)
    for scene_index, text, spoken, key, path in jobs:
        path = tempo_clip(path, speed)
        path = denoise_clip(path)
        audio, sample_rate = sf.read(path, dtype="float32")
        if (
            audio.ndim != 1
            or sample_rate != 24000
            or not len(audio)
            or not np.isfinite(audio).all()
            or not math.isfinite(float(np.max(np.abs(audio))))
            or np.max(np.abs(audio)) >= 1
        ):
            raise ValueError(f"Invalid B voice cache: {path}; remove it and regenerate")
        items.append(
            dict(
                scene=scene_index,
                text=text,
                audio=audio,
                sr=sample_rate,
                key=path.stem,
            )
        )
    return items, {
        **identity,
        "playback": {"speed": speed, "transform": TEMPO_VERSION},
        "cleanup": {
            "enabled": True,
            "filter": DENOISE_FILTER,
            "transform": DENOISE_VERSION,
            "order": "after tempo, before timeline and music",
        },
    }
