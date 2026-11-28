"""Make new news programmes or revalidate existing deliveries with one baseline."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

from episode import atomic_json, file_identity, read_json, verify_identity
from production_contract import (
    read_editorial,
    require_caption_text,
    resolve_baseline,
    verify_delivery_inputs,
)

RUNTIME = Path.home() / ".cache/news-to-video/runtime.json"


def locked_script(editorial, project):
    """Only new jobs must be identical to the locally locked programme draft."""
    state = editorial.episode
    stage = state.get("stage_receipts", {}).get("editorial_locked")
    identity = state.get("draft")
    if not stage or not identity or state.get("delivery_receipts"):
        raise ValueError("New production needs an editorial lock and an undelivered episode")
    verify_identity(identity)
    draft = read_json(identity["path"])
    if draft["episode_id"] != state["episode_id"]:
        raise ValueError("Locked draft belongs to a different episode")
    segments = [item for scene in project["scenes"] for item in scene["segments"]]
    for field in ("text", "spoken"):
        def words(units):
            text = "".join(unit.get(field, unit["text"]) for unit in units)
            return "".join(re.findall(r"\w", text))
        if words(draft["paragraphs"]) != words(segments):
            raise ValueError(f"Production {field} differs from the locked editorial draft")
    return identity


def freeze_narration(project, project_path, baseline, runtime_path):
    """Synthesize dry narration and measure cues for the formal production pass.

    Visual review can use estimated timings. Reuse an existing frozen master
    through external_final when preparing the technical preview and final cut.
    """
    from render import prepare_narration
    import soundfile

    audio = project_path.parent / "audio"
    if (audio / "freeze-receipt.json").exists():
        raise ValueError("Audio already frozen; use the existing receipt or a new job")
    voice = baseline.document["voice"]
    narration = {
        "title": project["title"],
        "scenes": project["scenes"],
        "voice": {"id": voice["id"], "speed": voice["generation_speed"]},
    }
    require_caption_text(narration["scenes"], baseline)
    cache = audio / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    _, _, _, cues, _, processing = prepare_narration(
        narration, read_json(runtime_path), cache, project_path.parent, audio, 24
    )
    if (processing["voice_id"], processing["backend"]) != (voice["id"], voice["backend"]):
        raise ValueError("Generated voice identity differs from the selected baseline")
    wave = audio / "voice.wav"
    info = soundfile.info(wave)
    atomic_json(audio / "cues.json", cues)
    receipt = {
        "sha256": file_identity(wave)["sha256"],
        "sample_rate": info.samplerate,
        "samples": info.frames,
        "channels": info.channels,
        "processing_identity": processing,
        "cue_count": len(cues),
    }
    atomic_json(audio / "freeze-receipt.json", receipt)
    atomic_json(audio / "voice-config.json", {
        **{key: value for key, value in receipt.items() if key != "cue_count"},
        "mode": "external_final",
        "path": "audio/voice.wav",
        "cues": "audio/cues.json",
        "playback_rate": 1.0,
    })
    return receipt


def compose(args, editorial, baseline):
    """Render once into an isolated output and identify the actual consumed artifacts."""
    from media_storage import render_storage
    import render

    binding = editorial.binding()
    source = None
    if args.mode == "revalidate":
        deliveries = editorial.episode.get("delivery_receipts", [])
        if not deliveries:
            raise ValueError("Revalidation requires a previously delivered episode")
        source = deliveries[-1]["artifact"]
        verify_identity(source)
        if Path(source["path"]).resolve() == (args.output / "video.mp4").resolve():
            raise ValueError("Revalidation needs a new output path")
    project = read_json(args.project)
    if args.mode == "new":
        binding["draft"] = locked_script(editorial, project)
    inputs = verify_delivery_inputs(project, args.project, editorial, baseline)
    options = render.argument_parser().parse_args([
        str(args.project), "--output", str(args.output), "--runtime", str(args.runtime),
    ])
    with render_storage(args.project, args.output, args.min_free_bytes) as job:
        # A complete output is immutable. An interrupted render may resume with the same inputs.
        receipt_path = args.output / "production-receipt.json"
        if receipt_path.exists():
            raise ValueError("The output path already contains a production delivery")
        pending = args.output / "production-inputs.json"
        expected = {**binding, "inputs": inputs, "baseline": baseline.identity()}
        if pending.exists():
            if read_json(pending) != expected:
                raise ValueError("Interrupted output belongs to different production inputs")
        else:
            if any(
                (args.output / name).exists()
                for name in ("video.mp4", "project.json", "validation.json")
            ):
                raise ValueError("Existing media requires a fresh production output path")
            atomic_json(pending, expected)
        render.run(
            options, reclaim_narrative_stage=job is not None,
            production_context=baseline.identity(),
        )
        if read_editorial(args.episode).binding() != editorial.binding():
            raise ValueError("Editorial bindings changed while rendering")
        verified = verify_delivery_inputs(
            read_json(args.project), args.project, editorial, baseline
        )
        if verified != inputs:
            raise ValueError("Production inputs changed while rendering")
        current = resolve_baseline(args.baseline, args.baseline_sha256)
        if current.identity() != baseline.identity():
            raise ValueError("Effective baseline changed while rendering")
        validation = read_json(args.output / "validation.json")
        frozen = validation.get("frozen_audio") or {}
        rail = validation["remotion_editorial"]
        if (
            validation.get("production_baseline") != baseline.identity()
            or not validation["full_decode_passed"]
            or frozen.get("sha256") != inputs["frozen_audio"]["sha256"]
            or frozen.get("cue_sha256") != inputs["cues"]["sha256"]
            or frozen.get("tts_invoked") is not False
            or frozen.get("playback_rate") != 1.0
            or validation["cue_count"] != inputs["cue_count"]
            or not validation["continuous_captions"]
            or rail["captions_in_video"] != baseline.document["captions"]["consumer"]
            or rail["picture_frame_count"] != inputs["frame_count"]
        ):
            raise ValueError("Composition receipt differs from actual baseline inputs")
        artifacts = {
            name: file_identity(args.output / name)
            for name in ("video.mp4", "captions.srt", "voice.wav", "timeline.json", "validation.json")
        }
        if artifacts["voice.wav"]["sha256"] != frozen["sha256"]:
            raise ValueError("Delivered voice bytes differ from the frozen input")
        if source and artifacts["video.mp4"]["sha256"] == source["sha256"]:
            raise ValueError("Revalidation reproduced the old delivery byte for byte")
        receipt = {
            "schema_version": 1,
            "kind": "production_delivery",
            "mode": args.mode,
            **expected,
            "artifacts": artifacts,
            "previous_delivery": source,
        }
        atomic_json(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("probe", "new", "revalidate"):
        command = modes.add_parser(mode)
        command.set_defaults(baseline=None, baseline_sha256=None)
        command.add_argument("--episode", type=Path, required=True)
        if mode == "probe":
            continue
        command.add_argument("--project", type=Path, required=True)
        command.add_argument("--output", type=Path)
        command.add_argument("--runtime", type=Path, default=Path(
            os.environ.get("NEWS_TO_VIDEO_RUNTIME", RUNTIME)
        ))
        command.add_argument("--min-free-bytes", type=int)
        command.add_argument("--freeze", action="store_true")
        if mode == "revalidate":
            command.add_argument("--baseline", type=Path)
            command.add_argument("--baseline-sha256")
    args = parser.parse_args()
    try:
        if (args.baseline is None) != (args.baseline_sha256 is None):
            raise ValueError("Candidate baseline and SHA-256 must be supplied together")
        baseline = resolve_baseline(args.baseline, args.baseline_sha256)
        editorial = read_editorial(args.episode.resolve())
        if args.mode == "probe":
            result = {
                **baseline.identity(), "episode_id": editorial.episode["episode_id"],
                **editorial.binding(),
            }
        else:
            args.project = args.project.resolve()
            if args.freeze:
                project = read_json(args.project)
                if args.mode == "new":
                    locked_script(editorial, project)
                result = freeze_narration(project, args.project, baseline, args.runtime)
            else:
                if args.output is None:
                    raise ValueError("Composition requires --output")
                args.output = args.output.resolve()
                result = compose(args, editorial, baseline)
        print(json.dumps(result, ensure_ascii=True), flush=True)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
