"""Evidence packages and recoverable programme receipts; no network or media effects.

Production and delivery are separate events. Markdown ledgers retain their existing
headers and history; adoption annotations make a retry safe even if a crash occurs
after the ledger replacement but before the episode receipt is saved.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import subprocess
from urllib.parse import urlsplit
import uuid

from daily_editorial import validate_plan
from stability_gate import validate_stability_gate

ACCEPTANCE_CONTRACTS = {"legacy", "daily-v1"}
ANIMATIC_CHECKS = (
    "audio_present",
    "continuous_playback",
    "caption_protection",
    "before_middle_after",
    "source_boundary",
    "visual_path_consumed",
)

STAGE_DEPENDENCIES = {
    "editorial_locked": ["evidence_ready"],
    "audio_locked": ["editorial_locked"],
    "visual_ready": ["editorial_locked"],
    "animatic_reviewed": ["audio_locked", "visual_ready"],
    "masters_ready": ["animatic_reviewed"],
    "composed": ["masters_ready", "audio_locked"],
    "reviewed": ["composed"],
}
DELIVERY_KINDS = {"text": "文字稿", "script": "剧本", "video": "已制成视频"}


def digest(value):
    """Hash canonical JSON for stable receipt identities."""
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_identity(path):
    """Capture an actual nonempty artifact, never a planned output path."""
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise ValueError(f"Artifact must be a nonempty file: {resolved}")
    hasher = hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return {
        "path": str(resolved),
        "sha256": hasher.hexdigest(),
        "bytes": resolved.stat().st_size,
    }


def verify_identity(identity):
    actual = file_identity(identity["path"])
    if actual != identity:
        raise ValueError(f"Artifact identity changed: {identity['path']}")


def _identity_set(identities):
    return {(item["path"], item["sha256"], item["bytes"]) for item in identities}


def _has_identity(value, identities):
    return isinstance(value, dict) and (
        value.get("path"),
        value.get("sha256"),
        value.get("bytes"),
    ) in _identity_set(identities)


def _require_identity(value, label):
    if not isinstance(value, dict) or not {"path", "sha256", "bytes"} <= set(value):
        raise ValueError(f"{label} must contain a complete file identity")
    verify_identity(value)
    return value


def _motion_actions(motion):
    actions = {}
    for scene in motion.get("scenes", []):
        for action in scene.get("actions", []):
            action_id = action.get("action_id")
            if not action_id or action_id in actions:
                raise ValueError("Motion report actions need unique action_id values")
            actions[action_id] = {"scene": scene.get("scene"), **action}
    return actions


def validate_animatic_receipt(
    path, episode_id, inputs=(), outputs=None, require_stability=False
):
    """Validate a real short, voiced preview and its actual visual consumer.

    The receipt is evidence-shaped. It records media identities, the frozen-voice
    window, the renderer path and observed before/middle/after frames. It does not
    infer audience approval from those technical checks.
    """
    path = Path(path).resolve(strict=True)
    receipt_identity = file_identity(path)
    if outputs is not None and not _has_identity(receipt_identity, outputs):
        raise ValueError("Animatic receipt must be registered as a stage output")
    receipt = read_json(path)
    if receipt.get("schema_version") != 1 or receipt.get("kind") != "animatic_review":
        raise ValueError(
            "Animatic receipt requires schema_version=1 and kind=animatic_review"
        )
    if receipt.get("episode_id") != episode_id:
        raise ValueError("Animatic receipt episode_id does not match the episode")
    _required_text(receipt, ["baseline_id"], "Animatic receipt")
    _require_identity(receipt.get("baseline"), "Production baseline")
    scope = receipt.get("scope", {})
    _required_text(scope, ["semantic_goal"], "Animatic scope")
    if not scope.get("scenes") or any(
        type(index) is not int for index in scope["scenes"]
    ):
        raise ValueError("Animatic scope needs source scene indices")
    if not scope.get("evidence_ids") or not all(
        isinstance(item, str) and item for item in scope["evidence_ids"]
    ):
        raise ValueError("Animatic scope needs actual evidence IDs")
    visual_path = receipt.get("visual_path")
    if visual_path not in {"legacy", "object_stage", "narrative_v1"}:
        raise ValueError("Animatic receipt visual_path is unsupported")
    for key in ("preview", "project", "motion_report", "validation", "playback"):
        _require_identity(receipt.get(key), f"Animatic receipt {key}")
    if outputs is not None and not _has_identity(receipt["preview"], outputs):
        raise ValueError("Animatic preview must be an actual stage output")
    for key in ("baseline", "project", "motion_report", "validation", "playback"):
        if outputs is not None and not _has_identity(receipt[key], inputs):
            raise ValueError(f"Animatic receipt {key} is not a registered stage input")
    checks = receipt.get("checks")
    if not isinstance(checks, dict) or any(
        checks.get(key) is not True for key in ANIMATIC_CHECKS
    ):
        raise ValueError(
            "Animatic receipt must prove the voiced preview and caption-safe visual checks"
        )
    limitations = receipt.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("Animatic receipt must state unmeasured quality layers")
    stability_gate = receipt.get("stability_gate")
    if stability_gate is None and require_stability:
        raise ValueError("Stable daily acceptance requires a stability_gate")
    if stability_gate is not None:
        validate_stability_gate(stability_gate)
    window = receipt.get("voice_window")
    if not isinstance(window, dict):
        raise ValueError(
            "Animatic receipt must retain the frozen voice window identity"
        )
    for key in ("source", "window"):
        _require_identity(window.get(key), f"Animatic voice_window.{key}")
        if outputs is not None and not _has_identity(window[key], inputs):
            raise ValueError(
                f"Animatic voice_window.{key} is not a registered stage input"
            )
    if (
        type(window.get("start_sample")) is not int
        or type(window.get("end_sample")) is not int
        or window["start_sample"] < 0
        or window["end_sample"] <= window["start_sample"]
    ):
        raise ValueError(
            "Animatic voice window needs a positive integer sample interval"
        )

    motion = read_json(receipt["motion_report"]["path"])
    if motion.get("visual_path") != visual_path:
        raise ValueError("Animatic visual_path does not match the motion report")
    consumer = receipt.get("consumer")
    if not isinstance(consumer, dict):
        raise ValueError("Animatic receipt must name the real visual consumer")
    _require_identity(consumer.get("artifact"), "Animatic consumer")
    if outputs is not None and not _has_identity(consumer["artifact"], inputs):
        raise ValueError("Animatic consumer is not a registered stage input")
    reported = motion.get("consumer", {})
    if consumer.get("kind") != reported.get("kind") or consumer[
        "artifact"
    ] != reported.get("artifact"):
        raise ValueError(
            "Animatic consumer must match the source staged by the renderer"
        )
    if motion.get("status") != "rendered" or type(motion.get("frame_count")) is not int:
        raise ValueError("Animatic motion report must come from rendered frames")
    preview_project = read_json(receipt["project"]["path"])
    evidence_ids = {source.get("id") for source in preview_project.get("sources", [])}
    if not set(scope["evidence_ids"]) <= evidence_ids:
        raise ValueError(
            "Animatic scope references evidence absent from the preview project"
        )

    observations = receipt.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("Animatic receipt needs observed action or shot transitions")
    if visual_path == "object_stage":
        actions = _motion_actions(motion)
        for observation in observations:
            if not isinstance(observation, dict):
                raise ValueError("Animatic observations must be objects")
            action = actions.get(observation.get("action_id"))
            if not action:
                raise ValueError(
                    "Animatic observation must reference a rendered action_id"
                )
            for key in ("before_frame", "middle_frame", "after_frame"):
                if type(observation.get(key)) is not int:
                    raise ValueError(
                        "Animatic observations need integer before/middle/after frames"
                    )
            if not (
                observation["before_frame"] < action["start_frame"]
                and action["start_frame"]
                <= observation["middle_frame"]
                < action["end_frame"]
                and observation["after_frame"] >= action["end_frame"]
            ):
                raise ValueError(
                    "Animatic observation frames do not cover the action transition"
                )
            _required_text(
                observation, ["observed", "evidence"], "Animatic observation"
            )
            _validate_frame_samples(observation, motion["frame_count"])
    elif visual_path == "narrative_v1":
        shots = motion.get("narrative_shots", [])
        shot_ids = {shot.get("shot_id") for shot in shots}
        for observation in observations:
            if observation.get("shot_id") not in shot_ids:
                raise ValueError(
                    "Narrative animatic observation must reference a rendered shot_id"
                )
            _required_text(
                observation, ["observed", "evidence"], "Animatic observation"
            )
    else:
        for observation in observations:
            _required_text(
                observation, ["observed", "evidence"], "Animatic observation"
            )
    _validate_preview_media(receipt, preview_project, motion["frame_count"])
    validation = read_json(receipt["validation"]["path"])
    artifacts = validation.get("artifacts", {})
    if (
        validation.get("full_decode_passed") is not True
        or validation.get("remotion_editorial", {}).get("captions_in_video")
        != "bottom_rail"
        or artifacts.get("video.mp4") != receipt["preview"]
        or artifacts.get("motion-report.json") != receipt["motion_report"]
        or artifacts.get("voice.wav", {}).get("sha256") != window["window"]["sha256"]
    ):
        raise ValueError(
            "Animatic validation must bind the decoded voiced MP4, motion and caption rail"
        )
    playback = read_json(receipt["playback"]["path"])
    if (
        playback.get("media_sha256") != receipt["preview"]["sha256"]
        or playback.get("ended") is not True
        or playback.get("muted") is not False
        or playback.get("rate") != 1
        or playback.get("decodedFrames") != motion["frame_count"]
        or type(playback.get("updates")) is not int
        or playback["updates"] < 2
        or any(event[0] in {"seeking", "error"} for event in playback.get("events", []))
    ):
        raise ValueError(
            "Animatic playback must cover this MP4 continuously at original speed"
        )
    return receipt


def _validate_frame_samples(observation, frame_count):
    for phase in ("before", "middle", "after"):
        if not 0 <= observation[f"{phase}_frame"] < frame_count:
            raise ValueError("Animatic observation lies outside the rendered preview")
        identity = observation.get("frames", {}).get(phase)
        _require_identity(identity, f"Animatic {phase} frame")
        if Path(identity["path"]).suffix.lower() != ".png":
            raise ValueError("Animatic frame samples must be extracted PNGs")


def _validate_preview_media(receipt, project, frame_count):
    """Check actual stream types, frame/sample mapping, and the original PCM window."""
    import imageio_ffmpeg
    import numpy as np
    import soundfile as sf

    window = receipt["voice_window"]
    source_path = window["source"]["path"]
    window_path = window["window"]["path"]
    start, end = window["start_sample"], window["end_sample"]
    with sf.SoundFile(source_path) as source, sf.SoundFile(window_path) as voice:
        if (
            source.channels != 1
            or voice.channels != 1
            or source.samplerate != voice.samplerate
            or end > source.frames
            or voice.frames != end - start
            or frame_count
            != (voice.frames * 24 + voice.samplerate - 1) // voice.samplerate
            or project.get("voice", {}).get("sha256") != window["window"]["sha256"]
        ):
            raise ValueError(
                "Preview voice window does not match frozen PCM or frame count"
            )
        source.seek(start)
        actual = voice.read(dtype="float64")
        if not np.any(actual) or not np.array_equal(
            actual, source.read(end - start, dtype="float64")
        ):
            raise ValueError(
                "Preview window must preserve the audible frozen source samples"
            )
    preview = Path(receipt["preview"]["path"])
    if preview.suffix.lower() != ".mp4":
        raise ValueError("Animatic requires a voiced MP4")
    # Decode both required stream types. A renamed storyboard or silent MP4 cannot pass.
    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(preview),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
    )
    if result.returncode:
        raise ValueError("Animatic must decode with both video and audio streams")


def _required_text(item, keys, label):
    if not isinstance(item, dict):
        raise ValueError(f"{label} must be an object")
    for key in keys:
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError(f"{label}.{key} must be nonempty text")


def _url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Expected a source HTTP(S) URL: {value}")


def validate_package(package):
    """Validate referential integrity; source truth still requires editorial review."""
    if package.get("schema_version") != 1 or package.get("domain") not in {
        "idc",
        "web3",
    }:
        raise ValueError("Evidence package needs schema_version=1 and domain=idc|web3")
    _required_text(package, ["package_id"], "package")
    coverage = package.get("coverage", {})
    _required_text(coverage, ["start", "end", "timezone"], "coverage")
    if "limitations" not in coverage:
        raise ValueError(
            "coverage.limitations must explicitly describe coverage limits"
        )
    if not isinstance(package.get("news"), list) or not package["news"]:
        raise ValueError("Evidence package needs at least one verified news item")
    ids = set()
    topics = set()
    urls = set()
    for news in package["news"]:
        _required_text(news, ["news_id", "topic_key", "canonical_url", "delta"], "news")
        _url(news["canonical_url"])
        if news["topic_key"] in topics or news["canonical_url"] in urls:
            raise ValueError("One event must not appear twice in an evidence package")
        topics.add(news["topic_key"])
        urls.add(news["canonical_url"])
        if "limitations" not in news or "material_constraints" not in news:
            raise ValueError("News must declare limitations and material_constraints")
        groups = [
            ("evidence", "evidence_id"),
            ("claims", "claim_id"),
            ("paragraphs", "paragraph_id"),
        ]
        ids_to_add = [news["news_id"]]
        for group, id_key in groups:
            if not isinstance(news.get(group), list) or not news[group]:
                raise ValueError(f"News needs nonempty {group}")
            for record in news[group]:
                _required_text(record, [id_key], group)
                ids_to_add.append(record[id_key])
        if len(set(ids_to_add)) != len(ids_to_add) or ids.intersection(ids_to_add):
            raise ValueError(
                "Evidence, claim, news and paragraph IDs must be package-unique"
            )
        ids.update(ids_to_add)
        evidence_ids = {item["evidence_id"] for item in news["evidence"]}
        claim_ids = {item["claim_id"] for item in news["claims"]}
        for evidence in news["evidence"]:
            _required_text(
                evidence,
                ["url", "publisher", "readable_excerpt", "source_type"],
                "evidence",
            )
            _url(evidence["url"])
            if "published_at" not in evidence or "event_date" not in evidence:
                raise ValueError(
                    "Evidence must distinguish publication and event dates; null means unknown"
                )
        for claim in news["claims"]:
            _required_text(claim, ["text"], "claim")
            if (
                not claim.get("evidence_ids")
                or not set(claim["evidence_ids"]) <= evidence_ids
            ):
                raise ValueError("Claim references missing evidence")
        for paragraph in news["paragraphs"]:
            _required_text(paragraph, ["text"], "paragraph")
            if (
                not paragraph.get("claim_ids")
                or not set(paragraph["claim_ids"]) <= claim_ids
            ):
                raise ValueError("Paragraph references missing claims")
    return package


def _package_receipts(paths):
    receipts = []
    seen_ids = set()
    seen_package_ids = set()
    seen_topics = set()
    seen_urls = set()
    for path in paths:
        package = validate_package(read_json(path))
        if package["package_id"] in seen_package_ids:
            raise ValueError("Package IDs must be unique within an episode")
        seen_package_ids.add(package["package_id"])
        for news in package["news"]:
            local_ids = {news["news_id"]}
            for group, id_key in [
                ("evidence", "evidence_id"),
                ("claims", "claim_id"),
                ("paragraphs", "paragraph_id"),
            ]:
                local_ids.update(item[id_key] for item in news[group])
            if (
                local_ids.intersection(seen_ids)
                or news["topic_key"] in seen_topics
                or news["canonical_url"] in seen_urls
            ):
                raise ValueError(
                    "Cross-package duplicate event; merge its evidence before programme assembly"
                )
            seen_ids.update(local_ids)
            seen_topics.add(news["topic_key"])
            seen_urls.add(news["canonical_url"])
        receipts.append(
            {
                "package_id": package["package_id"],
                "domain": package["domain"],
                **file_identity(path),
            }
        )
    if not receipts:
        raise ValueError("At least one evidence package is required")
    return receipts


def atomic_json(path, value):
    """Replace within the same directory so interrupted writes keep the old receipt."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(
        path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _atomic_bytes(path, data):
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def exclusive(path):
    """Refuse a competing writer. A leftover lock requires owner verification, not timeout deletion."""
    lock_path = Path(str(path) + ".lock")
    owner = {"pid": os.getpid(), "nonce": uuid.uuid4().hex}
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ValueError(
            f"Writer lock exists; inspect its owner before recovery: {lock_path}"
        ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(owner, stream)
        yield
    finally:
        if lock_path.exists() and read_json(lock_path) == owner:
            lock_path.unlink()


def _current(path, revision):
    state = read_json(path)
    if state.get("schema_version") != 1 or state.get("revision") != revision:
        raise ValueError("Episode revision mismatch; reread before writing")
    verify_episode(state)
    return state


def create_episode(
    path,
    episode_id,
    request,
    packages,
    confirmed_script=None,
    acceptance_contract="daily-v1",
    editorial_plan=None,
):
    """Create internal evidence-ready state without claiming user delivery."""
    if not isinstance(episode_id, str) or not episode_id.strip() or not request:
        raise ValueError("Episode needs a stable episode_id and the actual request")
    if acceptance_contract not in ACCEPTANCE_CONTRACTS:
        raise ValueError("Unknown acceptance contract")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive(path):
        if path.exists():
            raise ValueError(
                "Episode already exists; resume it instead of replacing its identity"
            )
        package_receipts = _package_receipts(packages)
        state = {
            "schema_version": 1,
            "episode_id": episode_id,
            "revision": 1,
            "acceptance_contract": acceptance_contract,
            "request": request,
            "packages": package_receipts,
            "stage_receipts": {
                "evidence_ready": {
                    "outputs": package_receipts,
                    "evidence": [
                        "Package references validated; factual review remains editorial responsibility"
                    ],
                }
            },
            "delivery_receipts": [],
            "adoption_receipts": [],
            "failure_receipts": [],
        }
        if editorial_plan:
            plan_identity = file_identity(editorial_plan)
            plan = read_json(editorial_plan)
            validate_plan(plan)
            if plan["episode_id"] != episode_id:
                raise ValueError("Editorial plan episode_id does not match the episode")
            state["editorial_plan"] = plan_identity
        if confirmed_script:
            state["confirmed_script"] = file_identity(confirmed_script)
        atomic_json(path, state)
    return state


def verify_episode(state):
    """Detect changed dependencies before resuming; never relabel stale output as current."""
    acceptance_contract = state.get("acceptance_contract", "legacy")
    if acceptance_contract not in ACCEPTANCE_CONTRACTS:
        raise ValueError("Unknown episode acceptance contract")
    for package in state["packages"]:
        verify_identity({key: package[key] for key in ["path", "sha256", "bytes"]})
        validate_package(read_json(package["path"]))
    if state.get("editorial_plan"):
        verify_identity(state["editorial_plan"])
        plan = read_json(state["editorial_plan"]["path"])
        validate_plan(plan)
        if plan["episode_id"] != state["episode_id"]:
            raise ValueError("Editorial plan episode_id does not match the episode")
    if state.get("confirmed_script"):
        verify_identity(state["confirmed_script"])
    for receipt in state["stage_receipts"].values():
        for artifact in receipt.get("inputs", []) + receipt.get("outputs", []):
            verify_identity({key: artifact[key] for key in ["path", "sha256", "bytes"]})
        if receipt.get("review_receipt"):
            verify_identity(
                {
                    key: receipt["review_receipt"][key]
                    for key in ["path", "sha256", "bytes"]
                }
            )
    if (
        acceptance_contract == "daily-v1"
        and "animatic_reviewed" in state["stage_receipts"]
    ):
        stage = state["stage_receipts"]["animatic_reviewed"]
        review_path = stage.get("review_receipt", {}).get("path")
        if not review_path:
            raise ValueError("Daily acceptance requires an animatic review receipt")
        validate_animatic_receipt(
            review_path,
            state["episode_id"],
            stage.get("inputs", []),
            stage.get("outputs", []),
            require_stability=state.get("stability_gate_version") == 1,
        )
    if acceptance_contract == "daily-v1" and "reviewed" in state["stage_receipts"]:
        validate_delivery_review(state, state["stage_receipts"]["reviewed"])
    for receipt in state["delivery_receipts"]:
        verify_identity(receipt["artifact"])
    return state


def draft_episode(path, revision, paragraphs, output):
    """Edit an internal draft only before lock; existing confirmed scripts are immutable inputs."""
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        if (
            state.get("confirmed_script")
            or "editorial_locked" in state["stage_receipts"]
        ):
            raise ValueError(
                "Narration is confirmed or locked; visual work cannot rewrite it"
            )
        claims = set()
        paragraph_ids = set()
        for package in state["packages"]:
            for news in read_json(package["path"])["news"]:
                claims.update(item["claim_id"] for item in news["claims"])
        for paragraph in paragraphs:
            _required_text(paragraph, ["paragraph_id", "text"], "draft paragraph")
            if paragraph["paragraph_id"] in paragraph_ids:
                raise ValueError("Draft paragraph IDs must remain unique")
            paragraph_ids.add(paragraph["paragraph_id"])
            if (
                not paragraph.get("claim_ids")
                or not set(paragraph["claim_ids"]) <= claims
            ):
                raise ValueError("Edited draft must retain traceable claim references")
        if not paragraphs:
            raise ValueError("Draft needs paragraphs")
        destination = Path(output).resolve()
        current_draft = state.get("draft", {}).get("path")
        if destination == path.resolve() or (
            destination.exists() and str(destination) != current_draft
        ):
            raise ValueError(
                "Draft output must be new or this episode's existing unlocked draft"
            )
        atomic_json(
            Path(output), {"episode_id": state["episode_id"], "paragraphs": paragraphs}
        )
        state["draft"] = file_identity(output)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def validate_delivery_review(state, stage):
    """Bind the reviewed MP4 and SRT to the validated formal render of this animatic."""
    review_identity = stage.get("review_receipt")
    if not review_identity or review_identity not in stage["outputs"]:
        raise ValueError(
            "Daily acceptance requires a registered delivery review receipt"
        )
    review = read_json(review_identity["path"])
    if review.get("schema_version") != 1 or review.get("kind") != "delivery_review":
        raise ValueError(
            "Daily review requires schema_version=1 and kind=delivery_review"
        )
    if review.get("episode_id") != state["episode_id"]:
        raise ValueError("Daily review belongs to another episode")
    composed = state["stage_receipts"]["composed"]["outputs"]
    for key in ("video", "captions", "validation"):
        if (
            not review.get(key)
            or review[key] not in composed
            or review[key] not in stage["inputs"]
        ):
            raise ValueError(f"Daily review must cover the actual composed {key}")
    validation = read_json(review["validation"]["path"])
    production = validation.get("acceptance", {})
    animatic = state["stage_receipts"]["animatic_reviewed"]["review_receipt"]
    if (
        production.get("animatic") != animatic
        or validation.get("full_decode_passed") is not True
    ):
        raise ValueError(
            "Composition requires a formal decode report bound to the reviewed animatic"
        )
    animatic_review = read_json(animatic["path"])
    review_gate = review.get("stability_gate")
    animatic_gate = animatic_review.get("stability_gate")
    if state.get("stability_gate_version") == 1:
        if review_gate is None:
            raise ValueError("Stable daily delivery review requires a stability_gate")
        validate_stability_gate(review_gate)
        if review_gate != animatic_gate:
            raise ValueError("Delivery review stability_gate differs from the animatic")
    elif review_gate is not None:
        validate_stability_gate(review_gate)
    if (
        validation.get("artifacts", {}).get("video.mp4") != review["video"]
        or validation.get("artifacts", {}).get("captions.srt") != review["captions"]
    ):
        raise ValueError("Delivery video or captions differ from the formal render")
    inspected = review.get("scene_reviews")
    if not isinstance(inspected, list) or not inspected:
        raise ValueError("Daily review requires scene observations")
    for item in inspected:
        _required_text(item, ["observation"], "Delivery scene review")
        for frame in item.get("frames", []):
            _require_identity(frame, "Delivery frame sample")
        if not item.get("frames"):
            raise ValueError(
                "Delivery scene observations require encoded frame samples"
            )
    if not review.get("limitations"):
        raise ValueError("Daily review requires the remaining quality limits")


def record_stage(
    path, revision, stage, outputs, evidence, inputs=(), review_receipt=None
):
    """Record verified artifacts and dependencies after the executor actually completes a stage."""
    if stage not in STAGE_DEPENDENCIES or not evidence:
        raise ValueError("Known stage and concrete completion evidence required")
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        missing = set(STAGE_DEPENDENCIES[stage]) - state["stage_receipts"].keys()
        if missing:
            raise ValueError(f"Stage dependencies not ready: {sorted(missing)}")
        input_identities = [file_identity(item) for item in inputs]
        output_identities = [file_identity(item) for item in outputs]
        receipt = {
            "inputs": input_identities,
            "outputs": output_identities,
            "evidence": evidence,
        }
        if not receipt["outputs"]:
            raise ValueError("Stage receipt must identify actual outputs")
        if (
            state.get("acceptance_contract", "legacy") == "daily-v1"
            and stage == "animatic_reviewed"
        ):
            if not review_receipt:
                raise ValueError(
                    "Daily acceptance requires --review-receipt for animatic_reviewed"
                )
            validate_animatic_receipt(
                review_receipt,
                state["episode_id"],
                input_identities,
                output_identities,
                require_stability=state.get("stability_gate_version") == 1,
            )
            receipt["review_receipt"] = file_identity(review_receipt)
        if stage == "editorial_locked":
            narration = state.get("confirmed_script") or state.get("draft")
            if not narration or narration not in receipt["outputs"]:
                raise ValueError(
                    "Editorial lock must include the current draft or confirmed script identity"
                )
            verify_identity(narration)
        if stage == "reviewed":
            if state.get("acceptance_contract") == "daily-v1":
                if not review_receipt:
                    raise ValueError(
                        "Daily acceptance requires --review-receipt for reviewed"
                    )
                receipt["review_receipt"] = file_identity(review_receipt)
                validate_delivery_review(state, receipt)
            composed_outputs = state["stage_receipts"]["composed"]["outputs"]
            if not any(item in composed_outputs for item in receipt["inputs"]):
                raise ValueError(
                    "Review must identify the actual composed artifact(s) it inspected"
                )
        existing = state["stage_receipts"].get(stage)
        if existing:
            if existing != receipt:
                raise ValueError(
                    "Completed stage identity differs; fork an episode revision instead of overwriting a lock"
                )
            return state
        if stage == "composed":
            # Old receipts stay verifiable after activation. New compositions must
            # come from the production entry before review or ledger adoption.
            from production_contract import require_registered_composition

            require_registered_composition(path, output_identities)
        state["stage_receipts"][stage] = receipt
        state["revision"] += 1
        atomic_json(path, state)
        return state


def record_delivery(
    path, revision, kind, artifact, delivered_to, delivered_at, evidence
):
    """Declare an actual user-facing delivery; an internal render is not delivery evidence."""
    if kind not in DELIVERY_KINDS or not delivered_to or not evidence:
        raise ValueError(
            "Delivery needs kind, destination and actual delivery evidence"
        )
    if datetime.fromisoformat(delivered_at).tzinfo is None:
        raise ValueError("Delivery timestamp must include a timezone")
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        required = "reviewed" if kind == "video" else "editorial_locked"
        if required not in state["stage_receipts"]:
            raise ValueError(f"Delivery requires completed {required}")
        identity = file_identity(artifact)
        output_stage = "composed" if kind == "video" else "editorial_locked"
        eligible = state["stage_receipts"][output_stage]["outputs"]
        if identity not in eligible:
            raise ValueError("Delivered artifact must be an identified stage output")
        if (
            kind == "video"
            and identity not in state["stage_receipts"]["reviewed"]["inputs"]
        ):
            raise ValueError(
                "Delivered video identity was not covered by the recorded review"
            )
        if kind == "video" and state.get("acceptance_contract") == "daily-v1":
            review = read_json(
                state["stage_receipts"]["reviewed"]["review_receipt"]["path"]
            )
            if review["video"] != identity:
                raise ValueError(
                    "Delivered video differs from the daily review receipt"
                )
        receipt = {
            "kind": kind,
            "artifact": identity,
            "delivered_to": delivered_to,
            "delivered_at": delivered_at,
            "evidence": evidence,
        }
        receipt["delivery_id"] = digest(
            {
                "episode_id": state["episode_id"],
                "kind": kind,
                "sha256": identity["sha256"],
            }
        )
        existing = next(
            (
                item
                for item in state["delivery_receipts"]
                if item["delivery_id"] == receipt["delivery_id"]
            ),
            None,
        )
        if existing:
            return state
        state["delivery_receipts"].append(receipt)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def record_failure(path, revision, stage, reason, resume_from, inputs=()):
    """Keep a recoverable failure without falsely advancing a successful stage."""
    if stage not in {*STAGE_DEPENDENCIES, "adoption"} or not reason or not resume_from:
        raise ValueError(
            "Failure requires a known stage, actual reason and recovery location"
        )
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        receipt = {
            "stage": stage,
            "reason": reason,
            "resume_from": resume_from,
            "inputs": [file_identity(item) for item in inputs],
        }
        # A repeated report should not create new revisions or erase prior evidence.
        failures = state.setdefault("failure_receipts", [])
        if receipt in failures:
            return state
        failures.append(receipt)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def _cell(value):
    return (
        str(value if value is not None else "未知")
        .replace("|", "&#124;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def ledger_update(text, domain, news, delivery, episode_id):
    """Pure, history-preserving ledger patch; retry detects the inline adoption identity."""
    adoption_id = digest(
        {
            "episode_id": episode_id,
            "news_id": news["news_id"],
            "delivery_id": delivery["delivery_id"],
        }
    )
    marker = f"<!-- media-adoption:{adoption_id} -->"
    if marker in text:
        return text, adoption_id
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    columns = 7 if domain == "idc" else 10
    topic_column = 4
    first_separator = None
    existing_index = None
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [item.strip() for item in line.strip().strip("|").split("|")]
        if len(cells) != columns:
            continue
        if all(item and set(item) <= {"-", ":", " "} for item in cells):
            if first_separator is None:
                first_separator = index
        elif cells[topic_column] == _cell(news["topic_key"]):
            existing_index = index
            break
    if first_separator is None:
        raise ValueError(
            "Ledger header not recognized; refusing a destructive format migration"
        )
    annotation = f"{DELIVERY_KINDS[delivery['kind']]}；episode={episode_id}；{delivery['artifact']['path']}；sha256={delivery['artifact']['sha256']}；{marker}"
    if existing_index is not None:
        original = lines[existing_index].rstrip()
        lines[existing_index] = original[:-1].rstrip() + "；" + _cell(annotation) + " |"
    else:
        primary = news["evidence"][0]
        day = delivery["delivered_at"][:10]
        common = [
            day,
            news["canonical_url"],
            news.get("title", news["news_id"]),
            primary["publisher"],
            news["topic_key"],
        ]
        if domain == "idc":
            cells = common + [
                news.get("category", "IDC"),
                news["delta"] + "；" + annotation,
            ]
        else:
            cells = common + [
                news.get("project", "未指定"),
                news.get("version", "未指定"),
                f"发布{primary['published_at']}；事件{primary['event_date']}",
                news["delta"],
                annotation,
            ]
        lines.insert(
            first_separator + 1, "| " + " | ".join(_cell(item) for item in cells) + " |"
        )
    return (
        newline.join(lines) + (newline if text.endswith(("\n", "\r")) else ""),
        adoption_id,
    )


def commit_adoption(
    path, revision, domain, ledger_path, delivery_id, expected_ledger_sha256=None
):
    """Commit one domain after delivery; independent domain receipts support mixed-episode recovery."""
    path = Path(path)
    ledger_path = Path(ledger_path)
    with exclusive(path):
        state = _current(path, revision)
        delivery = next(
            (
                item
                for item in state["delivery_receipts"]
                if item["delivery_id"] == delivery_id
            ),
            None,
        )
        if not delivery:
            raise ValueError("No actual delivery receipt; candidates cannot be adopted")
        packages = [item for item in state["packages"] if item["domain"] == domain]
        if not packages:
            raise ValueError("Episode has no evidence package for this domain")
        with exclusive(ledger_path):
            identity = file_identity(ledger_path)
            if expected_ledger_sha256 and identity["sha256"] != expected_ledger_sha256:
                raise ValueError("Ledger changed; reread before adoption")
            original = ledger_path.read_bytes().decode("utf-8-sig")
            updated = original
            adoption_ids = []
            for package in packages:
                for news in read_json(package["path"])["news"]:
                    updated, adoption_id = ledger_update(
                        updated, domain, news, delivery, state["episode_id"]
                    )
                    adoption_ids.append(adoption_id)
            if updated != original:
                prefix = (
                    b"\xef\xbb\xbf"
                    if ledger_path.read_bytes().startswith(b"\xef\xbb\xbf")
                    else b""
                )
                _atomic_bytes(ledger_path, prefix + updated.encode("utf-8"))
            receipt = {
                "domain": domain,
                "delivery_id": delivery_id,
                "ledger_path": str(ledger_path.resolve()),
                "adoption_ids": adoption_ids,
            }
            if receipt not in state["adoption_receipts"]:
                state["adoption_receipts"].append(receipt)
                state["revision"] += 1
                atomic_json(path, state)
            return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-package")
    validate.add_argument("package")
    create = sub.add_parser("init")
    create.add_argument("episode")
    create.add_argument("--episode-id", required=True)
    create.add_argument("--request", required=True)
    create.add_argument("--package", action="append", required=True)
    create.add_argument("--confirmed-script")
    create.add_argument(
        "--acceptance-contract",
        choices=sorted(ACCEPTANCE_CONTRACTS),
        default="daily-v1",
    )
    create.add_argument(
        "--editorial-plan",
        help="Validated daily editorial choices to bind to this episode",
    )
    for name in ["verify", "draft", "stage", "deliver", "adopt", "fail"]:
        command = sub.add_parser(name)
        command.add_argument("episode")
        if name != "verify":
            command.add_argument("--revision", type=int, required=True)
        if name == "draft":
            command.add_argument(
                "--paragraphs",
                required=True,
                help="JSON list or object containing paragraphs",
            )
            command.add_argument("--output", required=True)
        elif name == "stage":
            command.add_argument("--name", choices=STAGE_DEPENDENCIES, required=True)
            command.add_argument("--input", action="append", default=[])
            command.add_argument("--output", action="append", required=True)
            command.add_argument("--evidence", action="append", required=True)
            command.add_argument("--review-receipt")
        elif name == "deliver":
            command.add_argument("--kind", choices=DELIVERY_KINDS, required=True)
            command.add_argument("--artifact", required=True)
            command.add_argument("--to", required=True)
            command.add_argument(
                "--at", required=True, help="ISO timestamp with timezone"
            )
            command.add_argument("--evidence", required=True)
        elif name == "adopt":
            command.add_argument("--domain", choices=["idc", "web3"], required=True)
            command.add_argument("--ledger", required=True)
            command.add_argument("--delivery-id", required=True)
            command.add_argument("--ledger-sha256")
        elif name == "fail":
            command.add_argument(
                "--name", choices=[*STAGE_DEPENDENCIES, "adoption"], required=True
            )
            command.add_argument("--reason", required=True)
            command.add_argument("--resume-from", required=True)
            command.add_argument("--input", action="append", default=[])
    args = parser.parse_args()
    if args.command == "validate-package":
        package = validate_package(read_json(args.package))
        result = {
            "package_id": package["package_id"],
            "valid_structure": True,
            "factual_review": "not_proven_by_schema",
        }
    elif args.command == "init":
        result = create_episode(
            args.episode,
            args.episode_id,
            args.request,
            args.package,
            args.confirmed_script,
            args.acceptance_contract,
            args.editorial_plan,
        )
    elif args.command == "verify":
        result = verify_episode(read_json(args.episode))
    elif args.command == "draft":
        paragraphs = read_json(args.paragraphs)
        if isinstance(paragraphs, dict):
            paragraphs = paragraphs["paragraphs"]
        result = draft_episode(args.episode, args.revision, paragraphs, args.output)
    elif args.command == "stage":
        result = record_stage(
            args.episode,
            args.revision,
            args.name,
            args.output,
            args.evidence,
            args.input,
            getattr(args, "review_receipt", None),
        )
    elif args.command == "deliver":
        result = record_delivery(
            args.episode,
            args.revision,
            args.kind,
            args.artifact,
            args.to,
            args.at,
            args.evidence,
        )
    elif args.command == "fail":
        result = record_failure(
            args.episode,
            args.revision,
            args.name,
            args.reason,
            args.resume_from,
            args.input,
        )
    else:
        result = commit_adoption(
            args.episode,
            args.revision,
            args.domain,
            args.ledger,
            args.delivery_id,
            args.ledger_sha256,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
