"""在内存回执副本中演练“缺一帧→拒绝→恢复”的恢复边界。

演练不删除作业中的任何媒体，只修改内存中的 receipt 副本。它证明回执
检测器能发现缺项并在恢复原始回执后重新通过；不证明 Blender 已在新机器上
安装，也不替代真实断电续渲。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from common import read_json, sha256_file, write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "skills" / "news-to-video" / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))


def check_receipt(manifest: dict, root: Path, receipt: dict, shot: dict) -> dict:
    pattern = shot["media"]["pattern"]
    first = shot["media"]["source_first_frame"]
    expected = [
        pattern % frame
        for frame in range(first, first + shot["end_frame"] - shot["start_frame"])
    ]
    missing_receipt = [key for key in expected if key not in receipt.get("frames", {})]
    bad_hash = []
    for key in expected:
        path = root / key
        if key in receipt.get("frames", {}) and (
            not path.is_file() or sha256_file(path) != receipt["frames"][key]
        ):
            bad_hash.append(key)
    return {
        "expected": len(expected),
        "missing_receipt": missing_receipt,
        "bad_hash": bad_hash,
        "pass": not missing_receipt and not bad_hash,
    }


def drill(job: Path) -> dict:
    manifest = read_json(job / "shots.json")
    shot = manifest["shots"][0]
    receipt_path = job / shot["receipt"]
    original = read_json(receipt_path)
    baseline = check_receipt(manifest, job, original, shot)
    if not baseline["pass"]:
        raise ValueError(f"Baseline receipt is not complete: {baseline}")
    simulated = json.loads(json.dumps(original))
    missing_key = next(iter(simulated["frames"]))
    del simulated["frames"][missing_key]
    rejected = check_receipt(manifest, job, simulated, shot)
    recovered = check_receipt(manifest, job, original, shot)
    return {
        "schema_version": 1,
        "job": str(job.resolve()),
        "shot_id": shot["shot_id"],
        "baseline": baseline,
        "simulated_missing_key": missing_key,
        "simulated_rejection": rejected,
        "recovered": recovered,
        "source_unchanged": True,
        "scope": "in-memory receipt copy only; no frame deletion and no Blender execution",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = drill(args.job.resolve())
    write_json(args.report, report)
    print(
        json.dumps(
            {
                "baseline": report["baseline"]["pass"],
                "rejected_missing": bool(
                    report["simulated_rejection"]["missing_receipt"]
                ),
                "recovered": report["recovered"]["pass"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return (
        0
        if report["baseline"]["pass"]
        and report["simulated_rejection"]["missing_receipt"]
        and report["recovered"]["pass"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
