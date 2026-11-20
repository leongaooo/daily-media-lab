"""Validate executable editorial plans before voice work; never claim aesthetic approval."""

import hashlib
import re
from pathlib import Path
from color_utils import contrast

GRAMMARS = {
    "object_stage",
    "hero",
    "flow",
    "chart",
    "hero_scene",
    "timeline",
    "system_map",
    "evidence_board",
    "workbench",
    "comparison",
    "story",
}
CAMERAS = {"none", "slow-push", "slow-pan-right"}
DEFAULT_PALETTE = dict(
    background="#161A22",
    primary="#64D8CB",
    accent="#F4B860",
    warning="#EE8067",
    muted="#AAB6C4",
)
ASSET_KEYS = ("background_asset", "subject_asset", "supporting_asset")


def palette_for(scene):
    """Explicit renderer palette wins over the story world's inherited palette."""
    world = scene.get("story_world", {}).get("palette", {})
    if isinstance(world, list):
        world = dict(zip(("background", "primary", "accent", "muted"), world))
    return {**DEFAULT_PALETTE, **world, **scene.get("palette", {})}


def assess(project, base=None):
    report = dict(
        version=project.get("visual_contract_version"),
        status="legacy-not-assessed",
        errors=[],
        scenes=[],
        scope="Executable plan checks; rendered frames still need visual review",
    )
    if project.get("narrative_version") == 1:
        report.update(
            version="narrative-1", status="manifest-validated-at-media-preflight"
        )
        if not project.get("narrative_manifest"):
            report["errors"].append("narrative_manifest is required")
        if project.get("visual_contract_version") is not None:
            report["errors"].append(
                "Narrative v1 cannot claim legacy visual contract compliance"
            )
        return report
    if report["version"] is None:
        if any(
            isinstance(scene, dict)
            and scene.get("composition", scene.get("editorial_kind")) == "object_stage"
            for scene in project.get("scenes", [])
        ):
            report["status"] = "failed"
            report["errors"].append("object_stage requires visual_contract_version 2")
        return report
    if report["version"] == 2:
        from object_contract import assess as assess_objects

        return assess_objects(project, base, palette_for)
    errors = report["errors"]
    if report["version"] != 1:
        errors.append("visual_contract_version must be 1")
    previous_grammar = None
    previous_backgrounds = {}
    grammars = set()
    used_image = False
    for index, scene in enumerate(project.get("scenes", [])):
        prefix = f"Scene {index + 1}: "
        grammar = scene.get("composition", scene.get("editorial_kind", "hero_scene"))
        if grammar == "object_stage":
            errors.append(prefix + "object_stage requires visual_contract_version 2")
        grammars.add(grammar)
        if grammar not in GRAMMARS:
            errors.append(prefix + "unsupported composition")
        if grammar == previous_grammar:
            errors.append(
                prefix + "adjacent news scenes must use different main compositions"
            )
        previous_grammar = grammar
        world = scene.get("story_world", {}).get("id")
        if not world:
            errors.append(prefix + "story_world.id is required")
        palette = palette_for(scene)
        valid_colors = all(
            isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value)
            for value in palette.values()
        )
        if not valid_colors:
            errors.append(prefix + "palette requires six-digit sRGB hex colors")
        else:
            for name in ("primary", "accent", "warning", "muted"):
                if contrast(palette[name], palette["background"]) < 4.5:
                    errors.append(prefix + f"{name} text contrast below 4.5:1")
            if contrast("#F7F9FC", palette["background"]) < 4.5:
                errors.append(prefix + "body text contrast below 4.5:1")
        shots = scene.get("shots", [])
        if not 2 <= len(shots) <= 4:
            errors.append(prefix + "each news scene needs 2..4 caption-bound shots")
        expected_segment = 0
        for shot in shots:
            first = shot.get("segment_start")
            last = shot.get("segment_end", first)
            if (
                type(first) is not int
                or type(last) is not int
                or first != expected_segment
                or not first <= last < len(scene.get("segments", []))
            ):
                errors.append(
                    prefix
                    + "shots must partition caption segments without gaps or overlaps"
                )
                continue
            expected_segment = last + 1
            if not shot.get("title", "").strip():
                errors.append(prefix + "shot title is required")
            nodes = shot.get("nodes", scene.get("editorial_nodes", []))
            if any(
                not isinstance(node, dict)
                or not isinstance(node.get("title"), str)
                or not node["title"].strip()
                for node in nodes
            ):
                errors.append(prefix + "nodes need nonempty titles")
            focus = shot.get("focus", 0)
            if type(focus) is not int or focus < 0 or (nodes and focus >= len(nodes)):
                errors.append(prefix + "focus must reference an authored node")
            shot_grammar = shot.get("composition", grammar)
            if shot_grammar not in GRAMMARS:
                errors.append(prefix + "unsupported shot composition")
            if (
                shot_grammar
                in (
                    "timeline",
                    "flow",
                    "system_map",
                    "workbench",
                    "evidence_board",
                    "comparison",
                )
                and not 2 <= len(nodes) <= 5
            ):
                errors.append(
                    prefix
                    + "relationship compositions need 2..5 authored editorial_nodes"
                )
            # Bound label density to the geometry actually supported by each grammar.
            if shot_grammar in ("timeline", "flow", "workbench") and len(nodes) > 3:
                errors.append(
                    prefix + "timeline/flow/workbench support at most 3 readable nodes"
                )
            if shot_grammar == "comparison" and len(nodes) != 2:
                errors.append(prefix + "comparison needs exactly 2 evidenced states")
            camera = shot.get("camera_language", scene.get("camera_language", "none"))
            if camera not in CAMERAS:
                errors.append(prefix + "unsupported camera_language")
            background = shot.get("background_asset", scene.get("background_asset"))
            # Compare content identity too, so renamed copies cannot bypass diversity.
            identity = background
            if base and background and (Path(base) / background).is_file():
                identity = hashlib.sha256(
                    (Path(base) / background).read_bytes()
                ).hexdigest()
            if background and previous_backgrounds.get(world) == identity:
                errors.append(
                    prefix + "successive shots in one world reuse the same background"
                )
            previous_backgrounds[world] = identity
            for key in ASSET_KEYS:
                asset = shot.get(key, scene.get(key))
                if asset:
                    if base and not (Path(base) / asset).is_file():
                        errors.append(prefix + f"missing {key}: {asset}")
                    used_image = used_image or key in (
                        "background_asset",
                        "subject_asset",
                    )
            resolved_assets = [shot.get(key, scene.get(key)) for key in ASSET_KEYS]
            if len([value for value in resolved_assets if value]) != len(
                {value for value in resolved_assets if value}
            ):
                errors.append(
                    prefix
                    + "background, subject and supporting assets must have distinct roles"
                )
        if expected_segment != len(scene.get("segments", [])):
            errors.append(prefix + "shots do not cover all caption segments")
        for key in ASSET_KEYS:
            if not scene.get(key) and not all(shot.get(key) for shot in shots):
                errors.append(prefix + f"plan each shot asset role: {key}")
        report["scenes"].append(
            dict(
                index=index,
                composition=grammar,
                shot_count=len(shots),
                world_id=world,
                palette=palette,
            )
        )
    if len(project.get("scenes", [])) > 1 and len(grammars) < 2:
        errors.append("An episode needs at least two visual grammars")
    if project.get("reliable_image_available") and not used_image:
        errors.append(
            "Use at least one background or subject image when reliable imagery is available"
        )
    report["status"] = "failed" if errors else "plan-validated"
    return report


def require_valid(project, base=None):
    report = assess(project, base)
    if report["errors"]:
        raise ValueError("Visual contract: " + "; ".join(report["errors"]))
    return report
