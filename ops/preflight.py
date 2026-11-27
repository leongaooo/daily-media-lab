"""执行一次可搬迁媒体作业的只读预检。

预检顺序固定为磁盘与临时目录、JSON／路径、Blender 镜头清单、冻结音频、
渲染 runtime。它不会下载模型、启动 TTS、渲染帧或删除缓存；报告中的
warning 不能被调用方改写成通过。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from common import read_json, relative_posix, write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "skills" / "news-to-video" / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))


def result_item(name: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, **extra}


def drive_check(path: Path, minimum_bytes: int) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    status = "pass" if usage.free >= minimum_bytes else "error"
    return result_item(
        f"disk:{path.anchor or path}",
        status,
        f"free={usage.free} bytes; required={minimum_bytes} bytes",
        free_bytes=usage.free,
        total_bytes=usage.total,
    )


def check_runtime(runtime_path: Path) -> list[dict[str, Any]]:
    runtime = read_json(runtime_path)
    checks: list[dict[str, Any]] = []
    for key in ("font", "remotion_install", "ffprobe"):
        value = runtime.get(key)
        if not isinstance(value, str) or not value.strip():
            checks.append(result_item(f"runtime:{key}", "error", "missing path"))
            continue
        path = Path(value)
        checks.append(
            result_item(
                f"runtime:{key}",
                "pass" if path.exists() else "error",
                str(path),
            )
        )
    return checks


def check_blender(blender: Path | None) -> dict[str, Any]:
    if blender is None:
        return result_item("blender", "warning", "not supplied; source-only preflight")
    if not blender.is_file():
        return result_item("blender", "error", f"missing executable: {blender}")
    try:
        completed = subprocess.run(
            [str(blender), "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return result_item("blender", "error", str(error))
    first_line = completed.stdout.splitlines()[0] if completed.stdout else "unknown"
    return result_item("blender", "pass", first_line)


def check_job(
    job: Path,
    runtime: Path | None,
    blender: Path | None,
    cache: Path | None,
    minimum_free_gib: float,
) -> dict[str, Any]:
    job = job.resolve()
    minimum_bytes = round(minimum_free_gib * 1024**3)
    checks: list[dict[str, Any]] = []
    checked_anchors: set[str] = set()
    for disk_path in (job, cache):
        if disk_path is None:
            continue
        anchor = Path(disk_path).resolve().anchor.lower()
        if anchor in checked_anchors:
            continue
        checked_anchors.add(anchor)
        checks.append(drive_check(Path(disk_path), minimum_bytes))
    if cache is not None:
        cache = cache.resolve()

    project_path = job / "project.json"
    shots_path = job / "shots.json"
    if not project_path.is_file() or not shots_path.is_file():
        checks.append(
            result_item(
                "job-entrypoints",
                "error",
                "project.json and shots.json are both required",
            )
        )
        return {"job": str(job), "checks": checks, "status": "error"}

    project = read_json(project_path)
    manifest = read_json(shots_path)
    checks.append(result_item("json", "pass", "project.json and shots.json parsed"))

    try:
        from frozen_audio import load_final
        from narrative_media import validate_manifest

        total_frames = max(
            (shot.get("end_frame", 0) for shot in manifest.get("shots", [])),
            default=0,
        )
        # narrative_media validates actual source, receipts and frame hashes when
        # check_frames=True; the manifest boundary is authoritative for duration.
        validate_manifest(
            manifest,
            job,
            total_frames=total_frames or None,
            delivery=True,
            check_frames=True,
        )
        if project.get("voice", {}).get("mode") == "external_final":
            load_final(project, job)
        checks.append(
            result_item(
                "media-contract",
                "pass",
                "manifest, sources, receipts, masters and frozen audio validated",
            )
        )
    except Exception as error:  # validation errors are reported, not hidden
        checks.append(result_item("media-contract", "error", str(error)))

    if runtime is not None:
        try:
            checks.extend(check_runtime(runtime.resolve()))
        except Exception as error:
            checks.append(result_item("runtime", "error", str(error)))
    checks.append(check_blender(blender.resolve() if blender else None))

    temporary_roots = {
        key: os.environ.get(key, "") for key in ("TEMP", "TMP") if os.environ.get(key)
    }
    for key, value in temporary_roots.items():
        path = Path(value).resolve()
        status = (
            "pass"
            if path.is_relative_to(job) or (cache and path.is_relative_to(cache))
            else "warning"
        )
        checks.append(
            result_item(
                f"{key.lower()}-placement",
                status,
                f"{path}; expected job/cache root for isolated production",
            )
        )

    errors = [check for check in checks if check["status"] == "error"]
    warnings = [check for check in checks if check["status"] == "warning"]
    return {
        "schema_version": 1,
        "job": str(job),
        "checked_from": relative_posix(project_path, job),
        "minimum_free_gib": minimum_free_gib,
        "checks": checks,
        "status": "error" if errors else ("warning" if warnings else "pass"),
        "errors": len(errors),
        "warnings": len(warnings),
        "scope": "read-only preflight; no rendering, download, TTS or cache deletion",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--minimum-free-gib", type=float, default=10.0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = check_job(
        args.job,
        args.runtime,
        args.blender,
        args.cache,
        args.minimum_free_gib,
    )
    if args.report:
        write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
