"""显式迁移旧项目到 B 声和成品音乐；已支持的公开音色保持不变。"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

from music_bed import DEFAULT_MUSIC, validate_music
from voice_backend import VOICE_ID, DEFAULT_SPEED, validate_voice
from public_voice import PUBLIC_VOICE_ID


def migrate(project):
    result = deepcopy(project)
    previous_voice = result.get("voice")
    previous_music = result.get("music")
    # 已支持的项目保留音色和倍率；旧引擎的倍率不继承到 B 声。
    speed = DEFAULT_SPEED
    voice_id = VOICE_ID
    if isinstance(previous_voice, dict) and previous_voice.get("id") in (
        VOICE_ID,
        PUBLIC_VOICE_ID,
    ):
        validate_voice(result)
        speed = previous_voice.get("speed", DEFAULT_SPEED)
        voice_id = previous_voice["id"]
    result["voice"] = {"id": voice_id, "speed": speed}
    legacy = previous_music or {}
    if "gain" in legacy or "tempo_multiplier" in legacy:
        result["music"] = (
            {"mode": "off"} if legacy.get("gain") == 0 else dict(DEFAULT_MUSIC)
        )
    else:
        result["music"] = dict(legacy) if legacy else dict(DEFAULT_MUSIC)
    validate_voice(result)
    validate_music(result["music"])
    report = {
        "voice_before": previous_voice,
        "voice_after": result["voice"],
        "music_before": previous_music,
        "music_after": result["music"],
        "timeline_requires_regeneration": previous_voice != result["voice"],
        "narration_and_visuals_changed": False,
    }
    return result, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    path = Path(parser.parse_args().project).resolve()
    original = json.loads(path.read_text(encoding="utf-8-sig"))
    updated, report = migrate(original)
    backup = path.with_name(path.stem + ".before-b-voice.json")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    path.with_name(path.stem + ".audio-migration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
