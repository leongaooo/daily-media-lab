"""生成媒体作业与跨作业缓存的只读审计报告。

审计只计算容量、文件类别和重复哈希；它没有删除选项。删除必须由维护者
根据报告逐项确认，避免误删冻结音轨、回执或其他作业的可恢复证据。
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import json

from common import iter_files, relative_posix, sha256_file, write_json


PROTECTED_PARTS = {"sources", "audio", "receipts", "output", "frames", "design"}
REPRODUCIBLE_PARTS = {"tmp", ".cache", "remotion", "__pycache__"}


def classify(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    if relative.parts and relative.parts[0] in PROTECTED_PARTS:
        return "protected"
    if relative.parts and relative.parts[0] in REPRODUCIBLE_PARTS:
        return "reproducible"
    return "metadata-or-unknown"


def audit(roots: list[Path]) -> dict:
    files: list[dict] = []
    hashes: defaultdict[str, list[str]] = defaultdict(list)
    totals = defaultdict(int)
    for root in roots:
        root = root.resolve()
        if not root.exists():
            files.append({"root": str(root), "status": "missing"})
            continue
        for path in iter_files(root):
            relative = relative_posix(path, root)
            size = path.stat().st_size
            category = classify(path, root)
            record = {
                "root": str(root),
                "path": relative,
                "bytes": size,
                "category": category,
            }
            files.append(record)
            totals[category] += size
            if size >= 1024 * 1024:
                digest = sha256_file(path)
                hashes[digest].append(f"{root}/{relative}")
                record["sha256"] = digest
    duplicates = [
        {"sha256": digest, "paths": paths, "bytes": Path(paths[0]).stat().st_size}
        for digest, paths in hashes.items()
        if len(paths) > 1
    ]
    return {
        "schema_version": 1,
        "roots": [str(root.resolve()) for root in roots],
        "files": files,
        "totals": dict(totals),
        "duplicate_groups": duplicates,
        "deletion_policy": "report-only; protected sources, audio, receipts, licenses and outputs require explicit per-file review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    write_json(args.report, report)
    print(
        json.dumps(
            {
                "files": len(report["files"]),
                "totals": report["totals"],
                "duplicates": len(report["duplicate_groups"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
