"""免费授权成品音乐的本地选择、响度配平与人声避让；不生成短音伴奏。"""

import json
import hashlib
import math
from pathlib import Path
import secrets
import subprocess

import imageio_ffmpeg
import numpy as np


SKILL = Path(__file__).resolve().parent.parent
DEFAULT_MUSIC = {
    "mode": "pool",
    "style": "business",
    "relative_db": -19.0,
    "duck_db": 2,
}


def validate_music(config):
    if not isinstance(config, dict):
        raise ValueError("music must be an object")
    allowed = {"mode", "style", "track_id", "relative_db", "duck_db", "start_seconds"}
    if set(config) - allowed:
        raise ValueError(
            "Legacy music gain/tempo is retired; run migrate_audio.py first"
        )
    if config.get("mode", "pool") not in ("pool", "off"):
        raise ValueError("music.mode must be pool or off")
    if config.get("style", "business") not in ("business", "news", "documentary"):
        raise ValueError("music.style must be business, news or documentary")
    for key, default, minimum, maximum in (
        ("relative_db", DEFAULT_MUSIC["relative_db"], -40, -10),
        ("duck_db", DEFAULT_MUSIC["duck_db"], 0, 12),
        ("start_seconds", 0, 0, 86400),
    ):
        value = config.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not minimum <= value <= maximum
        ):
            raise ValueError(f"music.{key} must be finite within {minimum}..{maximum}")


def select_track(config, runtime, title):
    """随机选择受限音乐池中的曲目；显式曲目仍保持完全确定。"""
    manifest_path = Path(
        runtime.get("music_manifest", SKILL / "assets/music-pool/manifest.json")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    tracks = manifest["tracks"]
    ids = [track["id"] for track in tracks]
    if len(ids) != len(set(ids)):
        raise ValueError("Music manifest has duplicate track IDs")
    if config.get("track_id"):
        candidates = [track for track in tracks if track["id"] == config["track_id"]]
    else:
        random_ids = manifest.get("random_track_ids", [])
        if manifest.get("selection_mode") == "random" and random_ids:
            candidates = [track for track in tracks if track["id"] in random_ids]
        else:
            candidates = [
                track
                for track in tracks
                if config.get("style", "business") in track["styles"]
            ]
    if not candidates:
        raise ValueError(
            "No matching licensed music; select a known track or explicitly use mode=off"
        )
    candidates.sort(key=lambda track: track["id"])
    track = dict(
        candidates[0]
        if config.get("track_id")
        else secrets.SystemRandom().choice(candidates)
    )
    required = ("source_url", "license_url", "attribution", "sha256", "artist", "title")
    if track.get("license") != "CC BY 4.0" or any(
        not track.get(key) for key in required
    ):
        raise ValueError(
            "Music requires a verified CC BY 4.0 source and complete attribution"
        )
    path = (manifest_path.parent / track["file"]).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != track["sha256"]:
        raise ValueError(f"Music checksum mismatch: {track['id']}")
    return path, track


def loop_bed(audio, frame_count, sample_rate):
    """原速使用整首音乐；超过曲长才循环，接缝做一秒重叠淡化。"""
    if len(audio) >= frame_count:
        return audio[:frame_count].copy(), 0
    if len(audio) < sample_rate * 2:
        raise ValueError(
            "Music excerpt must be at least two seconds for natural looping"
        )
    overlap = min(sample_rate, len(audio) // 4)
    fade = np.linspace(0, 1, overlap)[:, None]
    result = np.zeros((frame_count, 2), dtype=np.float32)
    result[: len(audio)] = audio
    end = len(audio)
    loops = 0
    while end < frame_count:
        start = end - overlap
        count = min(len(audio), frame_count - start)
        result[start:end] = result[start:end] * (1 - fade) + audio[:overlap] * fade
        result[end : start + count] = audio[overlap:count]
        end = start + count
        loops += 1
    return result, loops


def duck_envelope(gate, sample_rate):
    """100Hz 控制轨先保留半秒停顿，再平滑过渡，避免逐字抽吸音量。"""
    hop = max(1, round(sample_rate / 100))
    coarse = np.asarray(gate[::hop] > 0, dtype=float)
    held = np.convolve(np.pad(coarse, (49, 0)), np.ones(50), mode="valid") > 0
    smooth = np.convolve(
        np.pad(held.astype(float), (15, 15), mode="edge"),
        np.ones(31) / 31,
        mode="valid",
    )
    return np.interp(np.arange(len(gate)), np.arange(len(smooth)) * hop, smooth)


def speech_activity(speech, sample_rate):
    """按20ms RMS高于-36dBFS识别人声；静音不因片段边界被标为讲话。

    返回与PCM等长的布尔轨，只检测能量，不是语音识别。半秒保持与平滑
    由duck_envelope执行；弱尾音可能低于门限，不能据此裁切原声。
    """
    hop = max(1, round(sample_rate * 0.02))
    padded = np.pad(speech, (0, (-len(speech)) % hop)).reshape(-1, hop)
    energy = np.sqrt(np.mean(padded**2, axis=1))
    return np.repeat(energy > 10 ** (-36 / 20), hop)[: len(speech)]


def mix_audio(voice, gate, sample_rate, config, runtime, title):
    """以实际PCM活跃段配平音乐；gate仅保留时间线接口和长度契约。

    旧gate覆盖整段合成音频及停顿，曾导致全程避让；现在从PCM检测活动，
    不改变语音内容。显式relative_db/duck_db优先，缺省采用已试听参数。
    """
    validate_music(config)
    speech = np.asarray(voice, dtype=np.float32)
    if not len(speech) or not np.isfinite(speech).all() or len(gate) != len(speech):
        raise ValueError("Voice and gate must be finite, nonempty and equally long")
    mixed = np.repeat(speech[:, None], 2, axis=1)
    if config.get("mode", "pool") == "off":
        return mixed, {"music_mode": "off", "peak": float(np.max(np.abs(mixed)))}, None
    path, track = select_track(config, runtime, title)
    start = config.get("start_seconds", track.get("start_seconds", 0))
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-v",
        "error",
        "-ss",
        str(start),
        "-i",
        str(path),
        "-af",
        "highpass=f=90,equalizer=f=220:t=q:w=0.7:g=-3",
        "-ac",
        "2",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    decoded = subprocess.run(command, capture_output=True, check=True)
    audio = np.frombuffer(decoded.stdout, dtype="<f4").reshape(-1, 2)
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Selected music cannot be decoded at the requested offset")
    bed, loops = loop_bed(audio, len(speech), sample_rate)
    active = speech_activity(speech, sample_rate)
    if not active.any():
        raise ValueError(
            "No active speech energy; cannot balance music against narration"
        )
    speech_rms = float(np.sqrt(np.mean(speech[active] ** 2)))
    music_rms = float(np.sqrt(np.mean(bed**2)))
    if speech_rms < 1e-6 or music_rms < 1e-6:
        raise ValueError("Silent narration or music cannot be loudness-balanced")
    relative_db = config.get("relative_db", DEFAULT_MUSIC["relative_db"])
    duck_db = config.get("duck_db", DEFAULT_MUSIC["duck_db"])
    target_music_rms = speech_rms * 10 ** (relative_db / 20)
    bed *= target_music_rms / music_rms
    duck = duck_envelope(active, sample_rate)
    bed *= (10 ** (-duck_db * duck / 20))[:, None]
    seconds = np.arange(len(speech)) / sample_rate
    fades = np.clip(seconds / 0.8, 0, 1) * np.clip(
        (len(speech) / sample_rate - seconds) / 1.5, 0, 1
    )
    bed *= fades[:, None]
    mixed += bed
    peak = float(np.max(np.abs(mixed)))
    protection = min(1.0, 0.94 / max(peak, 1e-6))
    mixed *= protection
    metrics = {
        "music_mode": "pool",
        "track_id": track["id"],
        "track_title": track["title"],
        "music_sha256": track["sha256"],
        "relative_db": relative_db,
        "duck_db": duck_db,
        "music_target_rms": target_music_rms,
        "normalization": "speech-active RMS; not LUFS",
        "activity_detection": "20ms RMS > -36dBFS; 500ms hold; smoothed duck",
        "speech_activity_percent": float(np.mean(active) * 100),
        "fully_ducked_percent": float(np.mean(duck > 0.99) * 100),
        "loops": loops,
        "start_seconds": start,
        "sample_rate": sample_rate,
        "channels": 2,
        "peak": float(np.max(np.abs(mixed))),
        "peak_protection_gain": protection,
        "voice_rms": speech_rms,
        "music_rms": float(np.sqrt(np.mean(bed**2))),
        "license": track["license"],
        "source_url": track["source_url"],
    }
    return mixed, metrics, track


def write_attribution(output, track):
    """每次重混覆盖署名文件；关闭音乐也明确清空旧曲目署名。"""
    if track is None:
        text = "本次未使用背景音乐。\n"
    else:
        text = (
            "以下音乐署名请随视频发布，保留作者、作品、来源与授权链接：\n\n"
            f"{track['attribution']}\n"
            f"来源：{track['source_url']}\n"
            f"授权：{track['license_url']}\n"
            "改动：裁切或循环、均衡、音量调整、淡入淡出，与口播混音。\n"
        )
    (Path(output) / "音乐署名.txt").write_text(text, encoding="utf-8")
