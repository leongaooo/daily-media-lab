"""Inventory and retire reviewed, dated news-to-video jobs and caches."""

import argparse
import json
import os
import shutil
import stat

from datetime import date
from pathlib import Path

from media_storage import is_day, job_guard, plain_chain


def review_key(value):
    path = Path(value)
    if path.drive or path.root or ".." in path.parts:
        raise ValueError(f"Use a media-root-relative review path: {value}")
    return Path(os.path.normcase(path)).as_posix()


def choices(path):
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    result = {}
    for row in rows:
        key = review_key(row["path"])
        if (
            key in result
            or row["action"] not in {"remove", "retain"}
            or not row["reason"].strip()
        ):
            raise ValueError(f"Invalid or duplicate review: {key}")
        result[key] = row
    return result


def active_inputs(root):
    # A dated review can remove a job only when the current dependency list permits it.
    governance = root / "governance"
    if not governance.exists() and not governance.is_symlink():
        return {}
    plain_chain(governance)
    path = governance / "active-media-inputs.json"
    if not path.exists() and not path.is_symlink():
        return {}
    plain_chain(path)
    protected = choices(path)
    if any(row["action"] != "retain" for row in protected.values()):
        raise ValueError("The active media input list may only retain paths")
    return protected


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def candidates(root):
    for scope in ("jobs", "cache"):
        parent = root / scope
        if not parent.exists():
            continue
        plain_chain(parent)
        for day in sorted(parent.iterdir()):
            if is_link(day) or not day.is_dir() or not is_day(day.name):
                yield day, None
                continue
            for path in sorted(day.iterdir()):
                cutoff_key = date.fromisoformat(day.name)
                if path.name.endswith(".media-production.lock"):
                    yield path, None
                elif path.is_dir() or is_link(path):
                    yield path, cutoff_key
                else:
                    yield path, None


def tree_state(path):
    """Count apparent regular-file bytes without traversing links or junctions."""
    if is_link(path):
        return 0, str(path.relative_to(path.parent))
    if path.is_file():
        return path.stat().st_size, None
    total = 0
    blocker = None

    def fail(error):
        raise error

    for parent, directories, files in os.walk(path, followlinks=False, onerror=fail):
        for name in (*directories, *files):
            child = Path(parent) / name
            if is_link(child) or name == "LOCK" or name.endswith(".lock"):
                blocker = blocker or str(child.relative_to(path))
                if name in directories:
                    directories.remove(name)
            elif name in files:
                total += child.stat().st_size
    return total, blocker


def govern(root, as_of, review, receipt, *, apply=False):
    root = root.absolute()
    plain_chain(root)
    if root.resolve() != root or not root.is_dir():
        raise ValueError("Use the absolute, resolved media root")
    receipt = receipt.absolute()
    plain_chain(receipt.parent)
    if receipt.is_relative_to(root / "jobs") or receipt.is_relative_to(root / "cache"):
        raise ValueError("Use a receipt outside the jobs being retired")
    protected = active_inputs(root)
    review = {review_key(name): row for name, row in review.items()}
    inventory = list(candidates(root))
    names = {review_key(path.relative_to(root)) for path, _ in inventory}
    if unknown := review.keys() - names:
        raise ValueError(
            f"Reviews reference paths outside this inventory: {sorted(unknown)}"
        )
    before = shutil.disk_usage(root).free
    rows = []
    # Reserve a new receipt before applying. Append results in memory and flush
    # the report even if an individual removal fails.
    with receipt.open("x", encoding="utf-8") as journal:
        for path, day in inventory:
            name = path.relative_to(root).as_posix()
            key = review_key(name)
            reviewed = review.get(key)
            row = {"path": name, "status": "retained", "bytes": 0}
            rows.append(row)
            try:
                size, blocker = tree_state(path)
                row["bytes"] = size
                lock = path.parent / f".{path.name}.media-production.lock"
                if day is None:
                    row["reason"] = "Undated entry, unowned file, or production lock"
                elif day >= as_of:
                    row["reason"] = "Current or future production date"
                elif key in protected:
                    row["reason"] = protected[key]["reason"]
                elif blocker or lock.exists():
                    row.update(
                        status="skipped", reason=f"Link or lock: {blocker or lock.name}"
                    )
                elif not reviewed or reviewed["action"] == "retain":
                    row["reason"] = (
                        reviewed["reason"]
                        if reviewed
                        else "Ownership and references need review"
                    )
                elif apply:
                    with job_guard(path):
                        if (current := active_inputs(root).get(key)) is not None:
                            row["reason"] = current["reason"]
                            continue
                        plain_chain(path)
                        if path.resolve() != path or not path.is_relative_to(root):
                            raise ValueError(
                                "Candidate moved outside the resolved root"
                            )
                        _, blocker = tree_state(path)
                        if blocker:
                            raise ValueError(f"Link or lock appeared: {blocker}")
                        shutil.rmtree(path)
                        if path.exists():
                            raise OSError("Candidate remains after removal")
                    row.update(status="removed", reason=reviewed["reason"])
                else:
                    row.update(status="eligible", reason=reviewed["reason"])
            except (OSError, ValueError) as error:
                row.update(status="skipped", reason=str(error))
        after = shutil.disk_usage(root).free
        result = {
            "root": str(root),
            "date": as_of.isoformat(),
            "mode": "apply" if apply else "dry-run",
            "free_before_bytes": before,
            "free_after_bytes": after,
            "free_delta_bytes": after - before,
            "eligible_bytes": sum(
                row["bytes"] for row in rows if row["status"] == "eligible"
            ),
            "removed_file_bytes": sum(
                row["bytes"] for row in rows if row["status"] == "removed"
            ),
            "entries": rows,
        }
        json.dump(result, journal, ensure_ascii=False, indent=2)
        journal.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    govern(
        arguments.root,
        arguments.as_of,
        choices(arguments.review),
        arguments.receipt,
        apply=arguments.apply,
    )


if __name__ == "__main__":
    main()
