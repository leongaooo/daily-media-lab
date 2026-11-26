"""Measure managed media jobs and remove only explicitly reviewed Webpack packs."""

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
            "cleanup": "No files removed during render",
        }
        # One immutable entry per attempt retains earlier measurements.
        save_receipt(output / f"storage-preflight-{uuid4().hex}.json", report)
        yield


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--pack", type=Path, action="append", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--reason", required=True, help="Reference and active-writer review"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = clean_packs(
        args.job, args.pack, args.receipt, reason=args.reason, apply=args.apply
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
