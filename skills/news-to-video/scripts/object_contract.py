"""Validate the v2 object stage before audio; geometry and cue references are explicit.

Objects own identity and base geometry. Actions own state changes, and staging alone
converts cue-relative timing to frames. This module never interprets director prose.
"""

import math
from pathlib import Path
import re

from color_utils import contrast

KINDS = {
    "queue",
    "server",
    "database",
    "phone",
    "message",
    "document",
    "building",
    "box",
    "bar",
    "note",
}
ACTIONS = {"enter", "exit", "transfer", "move", "state", "emphasize", "value"}
TONES = {"primary", "accent", "warning", "muted"}
STAGE_KEYS = {"objects", "connections", "groups", "actions", "surface", "ink", "shadow"}
ACTION_KEYS = {
    "type",
    "target",
    "to",
    "segment",
    "at",
    "until",
    "label",
    "tone",
    "value",
    "x",
    "y",
    "evidence",
}
OBJECT_KEYS = {"id", "kind", "label", "x", "y", "tone", "value", "asset", "scale"}


def finite(value, minimum, maximum):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and minimum <= value <= maximum
    )


def color(value):
    return isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value)


def member(value, choices):
    return isinstance(value, str) and value in choices


def horizontal_extent(obj, label=None):
    return max(
        (135 if obj.get("kind") == "queue" else 80) * obj.get("scale", 1),
        len(label if label is not None else obj.get("label", "")) * 14,
    )


def assess(project, base, palette_for):
    report = dict(
        version=2,
        status="plan-validated",
        errors=[],
        scenes=[],
        scope="Object/cue plan checks; continuous rendered review required",
    )
    errors = report["errors"]
    scenes = project.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        errors.append("v2 requires nonempty scenes")
        return report
    for index, scene in enumerate(scenes):
        prefix = f"Scene {index + 1}: "
        if not isinstance(scene, dict):
            errors.append(prefix + "scene must be an object")
            continue
        if scene.get("composition") != "object_stage":
            errors.append(
                prefix + "v2 requires object_stage; use v1 for legacy compositions"
            )
        if not isinstance(scene.get("story_world"), dict) or not scene[
            "story_world"
        ].get("id"):
            errors.append(prefix + "story_world.id required")
        stage = scene.get("object_stage", {})
        if not isinstance(stage, dict):
            errors.append(prefix + "object_stage must be an object")
            continue
        if set(stage) - STAGE_KEYS:
            errors.append(prefix + "unknown object_stage fields")
        palette = palette_for(scene)
        ink, surface = stage.get("ink", "#F7F9FC"), stage.get(
            "surface", palette["background"]
        )
        if not all(color(value) for value in [*palette.values(), ink, surface]):
            errors.append(prefix + "invalid stage/palette color")
        else:
            for foreground in [
                ink,
                palette["muted"],
                *[palette[tone] for tone in TONES],
            ]:
                for background in [surface, palette["background"]]:
                    if contrast(foreground, background) < 4.5:
                        errors.append(prefix + "stage text contrast below 4.5:1")
        objects = stage.get("objects", [])
        if not isinstance(objects, list) or not 1 <= len(objects) <= 12:
            errors.append(prefix + "stage needs 1..12 objects")
            continue
        ids = set()
        if type(stage.get("shadow", True)) is not bool:
            errors.append(prefix + "shadow must be boolean")
        for obj in objects:
            if not isinstance(obj, dict):
                errors.append(prefix + "invalid object")
                continue
            if set(obj) - OBJECT_KEYS:
                errors.append(prefix + "unknown object fields")
            identity = obj.get("id")
            if not isinstance(identity, str) or not identity or identity in ids:
                errors.append(prefix + "object IDs must be unique nonempty strings")
            else:
                ids.add(identity)
            if (
                not member(obj.get("kind"), KINDS)
                or not isinstance(obj.get("label"), str)
                or not 0 < len(obj["label"]) <= 18
            ):
                errors.append(
                    prefix + "object needs supported kind and short label (1..18 chars)"
                )
            if not finite(obj.get("x"), 100, 1500) or not finite(
                obj.get("y"), 100, 420
            ):
                errors.append(prefix + "object center outside safe stage bounds")
            if not member(obj.get("tone", "primary"), TONES):
                errors.append(prefix + "unsupported object tone")
            if not finite(obj.get("scale", 1), 0.5, 1.5):
                errors.append(prefix + "object scale must be 0.5..1.5")
            elif finite(obj.get("x"), 0, 1600) and isinstance(obj.get("label"), str):
                extent = horizontal_extent(obj)
                if obj["x"] - extent < 0 or obj["x"] + extent > 1600:
                    errors.append(prefix + "object glyph/label exceeds stage width")
            if "asset" in obj and (
                not isinstance(obj["asset"], str)
                or (base and not (Path(base) / obj["asset"]).is_file())
            ):
                errors.append(prefix + "missing object asset")
            if not finite(obj.get("value", 0), 0, 100):
                errors.append(prefix + "object value must be 0..100")
        segments = scene.get("segments", [])
        shot_owners = scene.get("shots", [])
        for owner in [scene, *(shot_owners if isinstance(shot_owners, list) else [])]:
            if not isinstance(owner, dict):
                continue
            generation = owner.get("image_generation")
            if generation and not isinstance(generation, dict):
                errors.append(prefix + "image_generation must be an object")
            elif generation and generation.get("enabled", True):
                if generation.get("role") != "subject" or not member(
                    generation.get("object_id"), ids
                ):
                    errors.append(
                        prefix + "v2 generation needs subject role and valid object_id"
                    )
            if any(
                owner.get(key)
                for key in (
                    "image",
                    "background_image",
                    "background_asset",
                    "subject_asset",
                    "supporting_asset",
                )
            ):
                errors.append(
                    prefix
                    + "v2 binds images to objects[].asset, not legacy image slots"
                )
        if not isinstance(segments, list) or not segments:
            errors.append(prefix + "semantic segments required")
            continue
        connections = stage.get("connections", [])
        if not isinstance(connections, list):
            errors.append(prefix + "connections must be a list")
            connections = []
        for edge in connections:
            if (
                not isinstance(edge, dict)
                or not member(edge.get("from"), ids)
                or not member(edge.get("to"), ids)
                or not edge.get("evidence")
            ):
                errors.append(prefix + "connection needs valid endpoints and evidence")
        groups = stage.get("groups", [])
        if not isinstance(groups, list):
            errors.append(prefix + "groups must be a list")
            groups = []
        for group in groups:
            if (
                not isinstance(group, dict)
                or not isinstance(group.get("label"), str)
                or not finite(group.get("x"), 0, 1600)
                or not finite(group.get("y"), 0, 560)
                or not finite(group.get("width"), 1, 1600 - group.get("x", 0))
                or not finite(group.get("height"), 1, 560 - group.get("y", 0))
            ):
                errors.append(prefix + "group needs bounded rectangle and label")
        actions = stage.get("actions", [])
        if not isinstance(actions, list) or not actions:
            errors.append(prefix + "actions must be a nonempty list")
            actions = []
        tracks = {}
        for action in actions:
            if not isinstance(action, dict):
                errors.append(prefix + "action must be an object")
                continue
            kind = action.get("type")
            segment = action.get("segment")
            if set(action) - ACTION_KEYS:
                errors.append(prefix + "unknown action fields")
            valid_track = member(kind, ACTIONS) and member(action.get("target"), ids)
            if not valid_track:
                errors.append(prefix + "unsupported action or target")
            if type(segment) is not int or not 0 <= segment < len(segments):
                errors.append(prefix + "action must bind a local segment")
                continue
            start, end = action.get("at", 0), action.get("until", 0.6)
            if not finite(start, 0, 1) or not finite(end, 0, 1) or end <= start:
                errors.append(prefix + "action fractions require 0 <= at < until <= 1")
                continue
            if (
                not isinstance(action.get("evidence"), str)
                or not action["evidence"].strip()
            ):
                errors.append(prefix + "action evidence required")
            if kind == "transfer" and (
                not member(action.get("to"), ids)
                or action.get("to") == action.get("target")
            ):
                errors.append(prefix + "transfer destination missing")
            if kind == "move" and (
                not finite(action.get("x"), 100, 1500)
                or not finite(action.get("y"), 100, 420)
            ):
                errors.append(prefix + "move destination outside safe bounds")
            if kind == "value" and not finite(action.get("value"), 0, 100):
                errors.append(prefix + "animated value must be 0..100")
            if "tone" in action and not member(action["tone"], TONES):
                errors.append(prefix + "unsupported action tone")
            if "label" in action and (
                not isinstance(action["label"], str)
                or not 0 < len(action["label"]) <= 18
            ):
                errors.append(prefix + "action label must be 1..18 chars")
            if kind == "state" and not ("label" in action or "tone" in action):
                errors.append(prefix + "state needs label or tone change")
            if not valid_track:
                continue
            actor = next(
                obj
                for obj in objects
                if isinstance(obj, dict) and obj.get("id") == action["target"]
            )
            label = action.get("label", actor.get("label", ""))
            if finite(actor.get("scale", 1), 0.5, 1.5) and isinstance(label, str):
                extent = horizontal_extent(actor, label)
                destination = action.get("x") if kind == "move" else actor.get("x")
                if finite(destination, 0, 1600) and (
                    destination - extent < 0 or destination + extent > 1600
                ):
                    errors.append(prefix + "action glyph/label exceeds stage width")
            # State/geometry tracks cannot race. Separate transfers may run together.
            track_kind = "visibility" if kind in ("enter", "exit") else kind
            track = (action["target"], track_kind)
            spans = tracks.setdefault(track, [])
            if kind != "transfer" and any(
                segment == old_segment and start < old_end and end > old_start
                for old_segment, old_start, old_end in spans
            ):
                errors.append(prefix + "overlapping actions on the same object track")
            spans.append((segment, start, end))
        shots = scene.get("shots", [])
        if not isinstance(shots, list) or not 1 <= len(shots) <= 8:
            errors.append(prefix + "v2 needs 1..8 caption-bound shots")
            continue
        cursor = 0
        for shot in shots:
            if not isinstance(shot, dict):
                errors.append(prefix + "invalid shot")
                continue
            first, last = shot.get("segment_start"), shot.get(
                "segment_end", shot.get("segment_start")
            )
            if (
                type(first) is not int
                or type(last) is not int
                or first != cursor
                or not first <= last < len(segments)
            ):
                errors.append(prefix + "shots must partition caption segments")
                continue
            cursor = last + 1
            if not shot.get("title") or not shot.get("progression"):
                errors.append(prefix + "shot title and narrative progression required")
            if not any(
                isinstance(a, dict)
                and type(a.get("segment")) is int
                and first <= a["segment"] <= last
                for a in actions
            ):
                errors.append(
                    prefix
                    + "each shot needs an executable action, not a background change"
                )
            view = shot.get("stage_view", [0, 0, 1600, 560])
            if (
                not isinstance(view, list)
                or len(view) != 4
                or not all(finite(v, 0, 1600) for v in view)
                or view[2] < 600
                or view[3] < 220
                or view[0] + view[2] > 1600
                or view[1] + view[3] > 560
            ):
                errors.append(prefix + "stage_view must be a readable bounded viewport")
        if cursor != len(segments):
            errors.append(prefix + "shots do not cover captions")
        report["scenes"].append(
            dict(
                index=index,
                composition="object_stage",
                object_count=len(objects),
                action_count=len(actions),
                shot_count=len(shots),
            )
        )
    report["status"] = "failed" if errors else "plan-validated"
    return report


def measured_stage(scene, cues, start_frame, fps):
    """Cue fractions become absolute scene frames once; end states persist across shots."""
    import copy

    stage = copy.deepcopy(scene["object_stage"])
    for action in stage["actions"]:
        cue = cues[action["segment"]]
        first = round(cue["start"] * fps) - start_frame
        last = round(cue["end"] * fps) - start_frame
        action["start_frame"] = round(first + (last - first) * action.get("at", 0))
        action["end_frame"] = round(first + (last - first) * action.get("until", 0.6))
        if action["end_frame"] <= action["start_frame"]:
            raise ValueError(
                "Object action rounds to zero frames; extend its cue interval"
            )
    stage["actions"].sort(key=lambda action: action["start_frame"])
    return stage
