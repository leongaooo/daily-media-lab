"""Check planning consistency; this does not judge image continuity or aesthetics."""

import hashlib
import json


def narration_identity(project):
    """Ignore visual edits while retaining the approved words and audio settings."""
    content = {
        "spoken": [
            segment.get("spoken", segment["text"])
            for scene in project["scenes"]
            for segment in scene["segments"]
        ],
        "voice": project.get("voice", {}),
        "duration": project.get("duration"),
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def assess(project):
    """Versioned opt-in preserves old projects without claiming new compliance."""
    report = {
        "version": project.get("director_contract_version"),
        "status": "legacy-not-assessed",
        "errors": [],
        "worlds": {},
        "scope": "Planning metadata only; rendered images require visual review",
    }
    if "director_contract_version" not in project:
        return report
    errors = report["errors"]
    if project["director_contract_version"] != 1:
        errors.append("director_contract_version must be 1")
    if project.get("production_mode", "daily_editorial") != "daily_editorial":
        errors.append("Only daily_editorial is supported")
    if project.get("editorial", {}).get("captions", "bottom_rail") != "bottom_rail":
        errors.append("Director projects require the fixed bottom caption rail")
    if project.get("voice", {}).get("speed", 1.15) != 1.15:
        errors.append("Keep the approved B voice speed at 1.15")
    for index, scene in enumerate(project.get("scenes", [])):
        world = scene.get("story_world")
        required = ("id", "setting", "continuity_notes", "facts_boundary")
        if not isinstance(world, dict) or any(
            not isinstance(world.get(key), str) or not world[key].strip()
            for key in required
        ):
            errors.append(f"Scene {index + 1}: story_world needs {required}")
            continue
        identity = world["id"]
        previous = report["worlds"].get(identity)
        if previous and previous["definition"] != world:
            errors.append(f"Scene {index + 1}: inconsistent world {identity}")
        else:
            report["worlds"].setdefault(
                identity, {"definition": world, "scene_indices": []}
            )["scene_indices"].append(index)
        if (
            not isinstance(scene.get("visual_goal"), str)
            or not scene["visual_goal"].strip()
        ):
            errors.append(f"Scene {index + 1}: visual_goal is required")
        if scene.get("editorial_kind") == "story":
            segments = scene.get("segments", [])
            for shot in scene.get("shots", []):
                first = shot.get("segment_start")
                last = shot.get("segment_end", first)
                if (
                    type(first) is not int
                    or type(last) is not int
                    or not 0 <= first <= last < len(segments)
                ):
                    errors.append(
                        f"Scene {index + 1}: story shots need valid caption indices"
                    )
    report["status"] = "failed" if errors else "planning-validated"
    return report
