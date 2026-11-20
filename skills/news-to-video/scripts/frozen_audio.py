"""冻结最终口播入口：验证身份并帧化 cue，不运行合成或任何人声处理。"""

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

FPS = 24


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def frame_at(seconds):
    """绝对时间只在入口转换一次；恰好半帧统一向上。"""
    value = Decimal(str(seconds))
    if not value.is_finite() or value < 0:
        raise ValueError("Time must be finite and nonnegative")
    # JSON浮点里的1/48会略低于半帧；只纠正机器表示量级的边界误差。
    boundary = value * FPS
    fraction = boundary % 1
    if abs(fraction - Decimal("0.5")) <= Decimal("1e-12"):
        boundary += Decimal("1e-12")
    return int(boundary.to_integral_value(rounding=ROUND_HALF_UP))


def external_mode(project):
    return project.get("voice", {}).get("mode") == "external_final"


def validate_config(voice):
    required = {
        "mode",
        "path",
        "sha256",
        "sample_rate",
        "samples",
        "channels",
        "processing_identity",
        "cues",
    }
    if set(voice) - required - {"playback_rate"} or not required <= set(voice):
        raise ValueError(
            "external_final requires path/hash/sample metadata/processing_identity/cues"
        )
    if voice.get("playback_rate", 1.0) != 1.0:
        raise ValueError("Frozen final narration playback_rate must be 1.0")
    if (
        not isinstance(voice["processing_identity"], dict)
        or not voice["processing_identity"]
    ):
        raise ValueError("Record completed voice processing identity")
    for key in ("sample_rate", "samples", "channels"):
        if type(voice[key]) is not int or voice[key] <= 0:
            raise ValueError(f"voice.{key} must be a positive integer")
    if voice["channels"] != 1:
        raise ValueError(
            "Final narration must be a mono dry vocal master, not an old mix"
        )


def load_final(project, base):
    """返回原采样PCM及公共整数帧时间线；源文件从不写入。

    cues 是实测句级区间，不推断词级动作。末帧向上覆盖尾音；只扩展
    最后一条字幕的显示区间，不补间隔、不重拼或拉伸原始人声。
    """
    config = project["voice"]
    validate_config(config)
    path = (Path(base) / config["path"]).resolve()
    if file_hash(path) != config["sha256"]:
        raise ValueError("Final narration checksum mismatch")
    info = sf.info(path)
    actual = {
        "sample_rate": info.samplerate,
        "samples": info.frames,
        "channels": info.channels,
    }
    if any(config[key] != value for key, value in actual.items()):
        raise ValueError("Final narration sample metadata mismatch")
    voice, sample_rate = sf.read(path, dtype="float32")
    if not len(voice) or not np.isfinite(voice).all() or np.max(np.abs(voice)) >= 1:
        raise ValueError("Final narration is empty, non-finite or clipped")
    frames = (info.frames * FPS + info.samplerate - 1) // info.samplerate
    duration = frames / FPS
    if project.get("duration") is not None and project["duration"] != duration:
        raise ValueError(
            "Frozen narration duration cannot be padded or shortened by project.duration"
        )
    cue_path = (Path(base) / config["cues"]).resolve()
    raw = json.loads(cue_path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("Final narration needs measured cues")
    segments = [
        (i, segment["text"])
        for i, scene in enumerate(project["scenes"])
        for segment in scene["segments"]
    ]
    if len(raw) != len(segments):
        raise ValueError("Cues must map every narration segment exactly once")
    cues = []
    for index, (cue, expected) in enumerate(zip(raw, segments)):
        start, end = cue["start"], cue["end"]
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in (start, end)
        ):
            raise ValueError("Cue times must be finite numbers")
        if cue.get("scene") != expected[0] or cue.get("text") != expected[1]:
            raise ValueError("Cue text/scene does not match the frozen project")
        if (
            start < 0
            or end <= start
            or end > duration
            or (index and start != raw[index - 1]["end"])
        ):
            raise ValueError(
                "Cues must be positive, continuous and within the final audio timeline"
            )
        begin, finish = frame_at(start), frame_at(end)
        if finish <= begin:
            raise ValueError("Cue collapses to zero frames; review semantic boundaries")
        cues.append(
            {
                **cue,
                "audio_start": start,
                "audio_end": end,
                "start_frame": begin,
                "end_frame": finish,
            }
        )
    if raw[0]["start"] != 0 or abs(raw[-1]["end"] - info.duration) > 1 / sample_rate:
        raise ValueError(
            "Measured cues must cover the complete final vocal sample range"
        )
    cues[-1]["end_frame"] = frames
    for cue in cues:
        cue["start"] = cue["start_frame"] / FPS
        cue["end"] = cue["end_frame"] / FPS
    identity = {
        **actual,
        "sha256": config["sha256"],
        "processing_identity": config["processing_identity"],
        "playback_rate": 1.0,
        "cue_sha256": file_hash(cue_path),
        "tts_invoked": False,
        "voice_transforms": [],
    }
    return duration, voice, np.zeros(len(voice)), cues, sample_rate, identity, path
