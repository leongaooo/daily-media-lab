"""Resolve installed baselines and verify the editorial and audiovisual inputs."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from daily_editorial import validate_plan
from episode import file_identity, read_json, validate_package, verify_identity

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BASELINE_NAME = "production-baseline.json"
ACTIVE_NAME = "active-production-baseline.json"
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Baseline:
    path: Path
    sha256: str
    document: dict
    selected_by: str

    def identity(self):
        return {
            "version": self.document["version"],
            "sha256": self.sha256,
            "selected_by": self.selected_by,
        }


def resolve_baseline(explicit=None, checksum=None):
    """Resolve a single installed baseline or a hash-pinned revalidation candidate."""
    expected_path = (ASSETS / BASELINE_NAME).resolve()
    if explicit is None:
        pointer = ASSETS / ACTIVE_NAME
        if not pointer.is_file():
            raise ValueError("The production baseline has not been activated")
        active = read_json(pointer)
        if active.get("schema_version") != 1:
            raise ValueError("Invalid active production baseline pointer")
        checksum = active.get("sha256")
    elif explicit.resolve() != expected_path:
        raise ValueError("Candidate must be the baseline bundled with this entry")

    if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
        raise ValueError("A SHA-256 pin is required for the production baseline")
    raw = expected_path.read_bytes()

    if hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError("Production baseline checksum mismatch")
    baseline = json.loads(raw.decode("utf-8-sig"))
    version = baseline.get("version")
    if baseline.get("schema_version") != 1 or not isinstance(version, str) or not version:
        raise ValueError("Unsupported production baseline version")
    if explicit is None and active.get("version") != version:
        raise ValueError("Active production baseline version differs from the payload")
    if baseline.get("frame") != {"width": 1920, "height": 1080, "fps": 24}:
        raise ValueError("Unsupported production frame contract")
    captions = baseline["captions"]
    if captions["consumer"] != "bottom_rail" or captions["y"] != [904, 1080]:
        raise ValueError("Unsupported production caption rail")
    if captions["max_visible_characters"] <= 0 or captions["max_seconds"] <= 0:
        raise ValueError("Production caption limits must be positive")
    if baseline["visual"] != {"consumer": "narrative_v1", "require_claim_links": True}:
        raise ValueError("Unsupported production visual consumer")
    if baseline["voice"]["playback_rate"] != 1.0:
        raise ValueError("Production final narration must play at 1.0")
    return Baseline(expected_path, checksum, baseline, "active" if explicit is None else "candidate")


@dataclass(frozen=True)
class Editorial:
    episode: dict
    identity: dict
    plan: dict
    packages: list
    evidence: dict
    claims: dict

    def binding(self):
        return {
            "episode": {
                **self.identity,
                "episode_id": self.episode["episode_id"],
                "revision": self.episode["revision"],
            },
            "plan": {**self.episode["editorial_plan"], "plan_id": self.plan["plan_id"]},
            "packages": self.packages,
            "evidence_ids": sorted(self.evidence),
        }


def read_editorial(episode_path):
    """Trust only the plan and evidence pack already registered by the episode."""
    identity = file_identity(episode_path)
    episode = read_json(episode_path)
    if episode.get("schema_version") != 1 or type(episode.get("revision")) is not int:
        raise ValueError("Invalid episode identity")
    plan_receipt = episode.get("editorial_plan")
    if not plan_receipt:
        raise ValueError("Episode has no registered editorial plan")
    verify_identity(plan_receipt)
    plan = validate_plan(read_json(plan_receipt["path"]))
    if plan["episode_id"] != episode["episode_id"]:
        raise ValueError("Editorial plan belongs to a different episode")

    evidence, claims, packages = {}, {}, episode["packages"]
    if not packages:
        raise ValueError("Episode must register at least one editorial package")
    for receipt in packages:
        verify_identity({key: receipt[key] for key in ("path", "bytes", "sha256")})
        package = validate_package(read_json(receipt["path"]))
        if (receipt["package_id"], receipt["domain"]) != (package["package_id"], package["domain"]):
            raise ValueError("Editorial package receipt disagrees with package identity")
        for item in package["news"]:
            for source in item["evidence"]:
                key = source["evidence_id"]
                if key in evidence:
                    raise ValueError(f"Duplicate episode evidence ID: {key}")
                evidence[key] = source
            for claim in item["claims"]:
                key = claim["claim_id"]
                if key in claims:
                    raise ValueError(f"Duplicate episode claim ID: {key}")
                claims[key] = set(claim["evidence_ids"])
    package_ids = [item["package_id"] for item in packages]
    if sorted(plan["editorial_package_ids"]) != sorted(set(package_ids)):
        raise ValueError("Editorial plan package IDs differ from the episode")
    if sorted(plan["evidence_ids"]) != sorted(evidence):
        raise ValueError("Editorial plan evidence IDs differ from the registered packages")
    return Editorial(episode, identity, plan, packages, evidence, claims)


def require_sources(project, editorial):
    sources = project.get("sources", [])
    source_urls = {item["id"]: item["url"] for item in sources}
    if len(source_urls) != len(sources) or source_urls != {
        key: record["url"] for key, record in editorial.evidence.items()
    }:
        raise ValueError("Production project evidence IDs or URLs do not match the episode")


def require_caption_text(scenes, baseline):
    limit = baseline.document["captions"]["max_visible_characters"]
    for number, segment in enumerate(
        (segment for scene in scenes for segment in scene["segments"]), start=1
    ):
        text = segment["text"]
        if not isinstance(text, str) or not text.strip() or "\n" in text:
            raise ValueError(f"Cue {number} must contain one semantic caption unit")
        if len("".join(text.split())) > limit:
            raise ValueError(f"Cue {number} exceeds {limit} visible characters")


def verify_delivery_inputs(project, project_path, editorial, baseline):
    """Run the same audio and narrative consumers used by the final composition."""
    from frozen_audio import load_final
    from narrative_media import validate_manifest

    if {"production_binding", "baseline_id", "baseline_version"} & project.keys():
        raise ValueError("Production baseline is selected by the entry, not the project")
    if project.get("narrative_version") != 1:
        raise ValueError("Production requires a sealed narrative/master consumer")
    if project.get("editorial", {}).get("captions", "bottom_rail") != "bottom_rail":
        raise ValueError("Production must render the bottom caption rail")
    require_sources(project, editorial)
    require_caption_text(project["scenes"], baseline)

    voice = project.get("voice", {})
    if voice.get("mode") != "external_final" or voice.get("playback_rate") != 1.0:
        raise ValueError("Production requires explicitly frozen dry audio at 1.0 playback")
    expected = baseline.document["voice"]
    processing = voice.get("processing_identity", {})
    if (
        processing.get("voice_id") != expected["id"]
        or processing.get("backend") != expected["backend"]
        or processing.get("playback", {}).get("speed") != expected["generation_speed"]
    ):
        raise ValueError("Final dry audio processing identity differs from the baseline")
    root = project_path.parent
    frozen_receipt_path = root / "audio/freeze-receipt.json"
    frozen_receipt = read_json(frozen_receipt_path)
    for key in ("sha256", "sample_rate", "samples", "channels", "processing_identity"):
        if frozen_receipt[key] != voice[key]:
            raise ValueError(f"Final dry audio does not match the generation receipt: {key}")
    duration, _, _, cues, _, _, audio = load_final(project, root)
    max_seconds = baseline.document["captions"]["max_seconds"]
    for index, cue in enumerate(cues, start=1):
        if cue["end"] - cue["start"] > max_seconds:
            raise ValueError(f"Cue {index} exceeds the {max_seconds}s caption interval")
    if frozen_receipt["cue_count"] != len(cues):
        raise ValueError("Final cue count differs from the generation receipt")

    path = (root / project["narrative_manifest"]).resolve()
    manifest = read_json(path)
    fps = baseline.document["frame"]["fps"]
    validate_manifest(manifest, path.parent, round(duration * fps), check_frames=False)
    for shot in manifest["shots"]:
        facts = shot["facts"]
        claim_ids = facts.get("claim_ids", [])
        if not claim_ids or not set(claim_ids) <= editorial.claims.keys():
            raise ValueError(f"Shot {shot['shot_id']} has unbound claims")
        supported = set().union(*(editorial.claims[key] for key in claim_ids))
        if set(facts["evidence_ids"]) != supported:
            raise ValueError(f"Shot {shot['shot_id']} evidence does not support its claims")
    return {
        "project": file_identity(project_path),
        "frozen_audio": file_identity(audio),
        "freeze_receipt": file_identity(frozen_receipt_path),
        "cues": file_identity(root / voice["cues"]),
        "visual": file_identity(path),
        "master_receipts": [
            file_identity(path.parent / shot["receipt"]) for shot in manifest["shots"]
        ],
        "frame_count": round(duration * fps),
        "cue_count": len(cues),
    }

def require_registered_composition(episode_path, outputs):
    """Bind newly recorded compositions to the active entry's delivery receipt."""
    if not (ASSETS / ACTIVE_NAME).is_file():
        return
    baseline = resolve_baseline()
    editorial = read_editorial(episode_path)
    videos = [identity for identity in outputs if Path(identity["path"]).suffix == ".mp4"]
    if len(videos) != 1:
        raise ValueError("A production composition must register exactly one MP4")
    video = videos[0]
    receipt_path = Path(video["path"]).with_name("production-receipt.json")
    receipt = read_json(receipt_path)
    if (
        receipt.get("kind") != "production_delivery"
        or receipt.get("mode") != "new"
        or receipt.get("baseline") != baseline.identity()
        or receipt.get("artifacts", {}).get("video.mp4") != video
    ):
        raise ValueError("Composition must come from the active production entry")
    for key in ("plan", "packages", "evidence_ids"):
        if receipt.get(key) != editorial.binding()[key]:
            raise ValueError(f"Composition {key} differs from the registered episode")
    episode = receipt["episode"]
    if (
        episode["episode_id"] != editorial.episode["episode_id"]
        or Path(episode["path"]).resolve() != episode_path.resolve()
        or receipt.get("draft") != editorial.episode["draft"]
    ):
        raise ValueError("Composition was produced for a different episode or draft")
    verify_identity(receipt["artifacts"]["validation.json"])
    validation = read_json(receipt["artifacts"]["validation.json"]["path"])
    if (
        validation.get("production_baseline") != baseline.identity()
        or validation.get("full_decode_passed") is not True
        or validation.get("artifacts", {}).get("video.mp4") != video
    ):
        raise ValueError("Composed media does not match the production render receipt")
