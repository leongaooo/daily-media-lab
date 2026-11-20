"""独立环境音/音效事件；按明确时间与授权叠加，绝不修改冻结干声。"""

from pathlib import Path
import subprocess

import imageio_ffmpeg
import numpy as np

from frozen_audio import file_hash
from music_bed import speech_activity, duck_envelope


def resolve_event_tracks(tracks, events, fps):
    """将导演事件解析为独立轨的绝对时间；不改音频内容或播放倍率。

    事件绑定与旧绝对秒入口互斥，防止图板已经移动而声音仍沿用旧秒数。
    返回新字典，保留 timing 来源供实际混音回执追溯。
    """
    resolved = []
    for track in tracks:
        if "timing" not in track:
            resolved.append(dict(track))
            continue
        if "start" in track or "duration" in track:
            raise ValueError("Event-bound sound cannot also declare absolute timing")
        timing = track["timing"]
        boundaries = []
        for side, default_edge in (("start", "start"), ("end", "end")):
            event_name = timing.get(f"{side}_event")
            edge = timing.get(f"{side}_edge", default_edge)
            offset = timing.get(f"{side}_offset_frames", 0)
            if event_name not in events or edge not in ("start", "end"):
                raise ValueError("Sound timing must reference an existing event edge")
            if type(offset) is not int:
                raise ValueError("Sound event offsets must be integer frames")
            frame = events[event_name][f"{edge}_frame"] + offset
            if type(frame) is not int:
                raise ValueError("Sound events must use integer frames")
            boundaries.append(frame)
        start, end = boundaries
        if start < 0 or end <= start or fps != 24:
            raise ValueError("Sound event interval must be positive at 24fps")
        resolved.append(
            {**track, "start": start / fps, "duration": (end - start) / fps}
        )
    return resolved


def add_tracks(mixed, voice, sample_rate, tracks, base):
    """音轨使用绝对秒数；无隐式循环/变速，超过片尾或素材不足均拒绝。"""
    result = mixed.copy()
    receipts = []
    active = duck_envelope(speech_activity(voice, sample_rate), sample_rate)
    for track in tracks:
        required = {
            "track_id",
            "path",
            "sha256",
            "kind",
            "start",
            "duration",
            "gain_db",
            "source_url",
            "license",
            "attribution",
            "purpose",
        }
        if not required <= set(track) or track["kind"] not in ("ambience", "effect"):
            raise ValueError(
                "Sound track needs explicit timing, identity, license and narrative purpose"
            )
        if not all(
            track[key] for key in ("source_url", "license", "attribution", "purpose")
        ):
            raise ValueError("Sound track source/rights/purpose cannot be empty")
        start, duration, gain = track["start"], track["duration"], track["gain_db"]
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and np.isfinite(value)
            for value in (start, duration, gain)
        ):
            raise ValueError("Sound timing and gain must be finite numbers")
        fade_seconds = track.get("fade_seconds", 0.12)
        duck_db = track.get("duck_db", 6)
        for value, maximum in ((fade_seconds, 10), (duck_db, 24)):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not np.isfinite(value)
                or not 0 <= value <= maximum
            ):
                raise ValueError("Sound fade/duck must be finite nonnegative values")
        begin, length = round(start * sample_rate), round(duration * sample_rate)
        if (
            start < 0
            or duration <= 0
            or begin + length > len(result)
            or not -80 <= gain <= 0
        ):
            raise ValueError("Sound track range or gain invalid")
        path = Path(base) / track["path"]
        if file_hash(path) != track["sha256"]:
            raise ValueError("Sound track checksum mismatch")
        decoded = subprocess.check_output(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-v",
                "error",
                "-i",
                str(path),
                "-ac",
                "2",
                "-ar",
                str(sample_rate),
                "-f",
                "f32le",
                "pipe:1",
            ]
        )
        audio = np.frombuffer(decoded, dtype="<f4").reshape(-1, 2)
        if len(audio) < length or not np.isfinite(audio).all():
            raise ValueError("Sound source is too short or invalid; no implicit loop")
        layer = audio[:length].copy() * 10 ** (gain / 20)
        fade = min(round(sample_rate * fade_seconds), length // 2)
        if fade > 0:
            ramp = np.linspace(0, 1, fade)[:, None]
            layer[:fade] *= ramp
            layer[-fade:] *= ramp[::-1]
        layer *= (10 ** (-duck_db * active[begin : begin + length] / 20))[:, None]
        result[begin : begin + length] += layer
        receipts.append({**track, "decoded_samples_used": length, "design_sound": True})
    if np.max(np.abs(result)) >= 1:
        raise ValueError("Sound design clips the mix; lower explicit track gains")
    return result, receipts
