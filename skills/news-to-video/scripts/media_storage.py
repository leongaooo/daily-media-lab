"""Measure managed jobs and reclaim verified Remotion intermediates."""

import argparse
import json
import os
import re
import shutil
import stat
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from uuid import uuid4


def plain_chain(path):
    """Reject links and Windows junctions before following any job-relative path."""
    for part in (*reversed(path.parents), path):
        meta = part.lstat()
        attributes = getattr(meta, "st_file_attributes", 0)
        if stat.S_ISLNK(meta.st_mode) or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"Link or reparse point: {part}")


def is_day(name):
    try:
        return date.fromisoformat(name).isoformat() == name
    except ValueError:
        return False


def managed_job(path):
    path = Path(os.path.abspath(path))
    for candidate in (path, *path.parents):
        day = candidate.parent
        if day.parent.name == "jobs" and is_day(day.name):
            return candidate
    return None


@contextmanager
def job_guard(job):
    plain_chain(job)
    # Keep the lock beside the job so complete retirement can hold it until
    # after the directory is gone.
    lock = job.parent / f".{job.name}.media-production.lock"
    try:
        with lock.open("x", encoding="ascii") as handle:
            handle.write("media_storage\n")
    except FileExistsError as error:
        raise ValueError(f"Job is active or its lock needs review: {lock}") from error
    try:
        plain_chain(job)
        yield
    finally:
        lock.unlink()


def save_receipt(path, report):
    with path.open("x", encoding="utf8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


@contextmanager
def render_storage(project, output, min_free_bytes=None):
    """Hold the same job lock during rendering and cache maintenance."""
    output = Path(os.path.abspath(output))
    job = managed_job(output)
    if job is None:
        if min_free_bytes is not None:
            raise ValueError(
                "A media jobs/YYYY-MM-DD/<episode> output is required for this budget"
            )
        yield
        return
    if not job.exists():
        parent = next(path for path in job.parents if path.exists())
        plain_chain(parent)
        job.mkdir(parents=True, exist_ok=True)
    with job_guard(job):
        parent = next(path for path in (output, *output.parents) if path.exists())
        plain_chain(parent)
        free = shutil.disk_usage(job).free
        if min_free_bytes is not None and free < min_free_bytes:
            raise ValueError(f"{job}: {free} free bytes, requested {min_free_bytes}")
        output.mkdir(parents=True, exist_ok=True)
        report = {
            "job": str(job),
            "project": str(project.absolute()),
            "output": str(output),
            "free_bytes": free,
            "requested_free_bytes": min_free_bytes,
            "cleanup": "No files removed during storage preflight",
        }
        # One immutable entry per attempt retains earlier measurements.
        save_receipt(output / f"storage-preflight-{uuid4().hex}.json", report)
        yield job


def inspect_pack(job, relative):
    parts = relative.parts
    # Only numeric Webpack chunks and the corresponding index are disposable.
    # Browser downloads, assets, compiled videos and review images have separate lifecycles.
    if (
        relative.is_absolute()
        or ".." in parts
        or len(parts) < 6
        or parts[-5:-3] != (".cache", "webpack")
        or parts[-7:-5] != ("remotion", "node_modules")
        or not re.fullmatch(r"remotion-production-[\w.-]+", parts[-3])
        or not re.fullmatch(r"[0-9a-f]{16,64}", parts[-2])
        or not re.fullmatch(r"(?:[0-9]+|index)\.pack(?:\.old)?", parts[-1])
    ):
        raise ValueError("Outside the supported job-local Remotion Webpack pack paths")
    target = job / relative
    plain_chain(target)
    meta = target.stat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
        raise ValueError("Expected an ordinary file with one link")
    return target, meta


def clean_packs(job, packs, receipt, *, reason, apply=False):
    job = Path(os.path.abspath(job))
    if managed_job(job) != job or not reason.strip():
        raise ValueError("Provide an existing dated media job and a review reason")
    plain_chain(receipt.absolute().parent)
    with job_guard(job), receipt.open("x", encoding="utf8") as journal:
        before = shutil.disk_usage(job).free
        entries = []
        for relative in dict.fromkeys(packs):
            entry = {"path": str(relative)}
            try:
                target, meta = inspect_pack(job, relative)
                entry["bytes"] = meta.st_size
                if apply:
                    target.unlink()
                entry["status"] = "removed" if apply else "eligible"
            except (OSError, ValueError) as error:
                entry.update(status="skipped", reason=str(error))
            entries.append(entry)
        after = shutil.disk_usage(job).free
        report = {
            "job": str(job),
            "review_reason": reason,
            "mode": "apply" if apply else "preview",
            "free_before_bytes": before,
            "free_after_bytes": after,
            "free_delta_bytes": after - before,
            "removed_file_bytes": sum(
                row["bytes"] for row in entries if row["status"] == "removed"
            ),
            "recovery": "Run the same render from the original project and pinned Remotion runtime",
            "entries": entries,
        }
        json.dump(report, journal, ensure_ascii=False, indent=2)
        journal.write("\n")
    return report


def inspect_stage_pair(target, original, expected):
    from frozen_audio import file_hash

    original = Path(os.path.abspath(original))
    plain_chain(original)
    plain_chain(target)
    source_meta = original.stat()
    target_meta = target.stat()
    if not stat.S_ISREG(source_meta.st_mode) or not stat.S_ISREG(target_meta.st_mode):
        raise ValueError("Expected regular source and staging files")
    if target_meta.st_nlink != 1 or target_meta.st_size != source_meta.st_size:
        raise ValueError("Staged copy is shared or differs in size from its master")
    if file_hash(original) != expected or file_hash(target) != expected:
        raise ValueError("Frame differs from the sealed master")
    return target_meta.st_size


def clean_rendered_stage(project, base, output, receipt, *, reason, apply=False):
    """Reclaim the exact staged PNGs of a decoded deliverable under its job lock."""
    from frozen_audio import file_hash
    from narrative_media import read_json, sealed_stage_pairs

    job = managed_job(output)
    if job is None or project.get("narrative_version") != 1 or not reason.strip():
        raise ValueError("Expected a managed narrative output and a review reason")
    lock = job.parent / f".{job.name}.media-production.lock"
    if not lock.is_file():
        raise ValueError("The render or maintenance entry point must hold the job lock")
    plain_chain(output)
    plain_chain(receipt.parent)
    validation_path = output / "validation.json"
    video_path = output / "video.mp4"
    plain_chain(validation_path)
    plain_chain(video_path)
    validation = read_json(validation_path)
    artifact = validation.get("artifacts", {}).get("video.mp4", {})
    total_frames = validation.get("remotion_editorial", {}).get("picture_frame_count")
    if (
        validation.get("full_decode_passed") is not True
        or type(total_frames) is not int
        or total_frames < 1
        or artifact.get("sha256") != file_hash(video_path)
    ):
        raise ValueError(
            "Cleanup requires the decoded delivery and its verified identity"
        )
    public = output / "remotion" / "public"
    stage_root = public / "narrative"
    manifest_path = Path(os.path.abspath(base / project["narrative_manifest"]))
    if not manifest_path.is_relative_to(job):
        raise ValueError(f"Stage manifest is outside the locked job: {manifest_path}")
    plain_chain(manifest_path)
    pairs = list(sealed_stage_pairs(manifest_path, public, total_frames, job))
    if any(
        Path(os.path.abspath(original)).is_relative_to(stage_root)
        for _, original, _ in pairs
    ):
        raise ValueError("Staging contains source master frames")
    before = shutil.disk_usage(job).free
    entries = []
    with receipt.open("x", encoding="utf8") as journal:
        for target, original, expected in pairs:
            entry = {
                "path": target.relative_to(job).as_posix(),
                "source": str(Path(os.path.abspath(original))),
                "sha256": expected,
            }
            try:
                entry["bytes"] = inspect_stage_pair(target, original, expected)
                if apply:
                    target.unlink()
                entry["status"] = "removed" if apply else "eligible"
            except (OSError, ValueError) as error:
                entry.update(status="skipped", reason=str(error))
            entries.append(entry)
        after = shutil.disk_usage(job).free
        report = {
            "job": str(job),
            "output": str(output),
            "manifest": str(manifest_path),
            "review_reason": reason,
            "mode": "apply" if apply else "preview",
            "free_before_bytes": before,
            "free_after_bytes": after,
            "free_delta_bytes": after - before,
            "removed_file_bytes": sum(
                row["bytes"] for row in entries if row["status"] == "removed"
            ),
            "recovery": "Rerun render.py from the original project with --keep-narrative-stage",
            "entries": entries,
        }
        json.dump(report, journal, ensure_ascii=False, indent=2)
        journal.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pack", type=Path, action="append")
    target.add_argument("--stage-output", type=Path)
    parser.add_argument(
        "--project", type=Path, help="Original render project for --stage-output"
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--reason", required=True, help="Reference and active-writer review"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    receipt = Path(os.path.abspath(args.receipt))
    if args.stage_output is None:
        report = clean_packs(
            args.job, args.pack, receipt, reason=args.reason, apply=args.apply
        )
    else:
        from narrative_media import read_json

        job = Path(os.path.abspath(args.job))
        output = Path(os.path.abspath(args.stage_output))
        if args.project is None or managed_job(output) != job:
            parser.error("--stage-output requires --project and an output inside --job")
        project_path = Path(os.path.abspath(args.project))
        with job_guard(job):
            plain_chain(project_path)
            report = clean_rendered_stage(
                read_json(project_path),
                project_path.parent,
                output,
                receipt,
                reason=args.reason,
                apply=args.apply,
            )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
