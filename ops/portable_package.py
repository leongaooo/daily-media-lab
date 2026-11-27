"""把可公开搬迁的媒体作业源封装成相对路径 ZIP。

默认封装“可重渲源包”：项目 JSON、事件／镜头清单、可编辑源、冻结音频、
字幕、来源、许可和作者脚本。PNG序列、Remotion bundle、runtime、模型、
字体、Key、日志和临时目录需要显式选择，避免误把机器状态变成发布资产。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from common import read_json, relative_posix, resolve_inside, sha256_file, write_json


EXCLUDED_PARTS = {"tmp", ".cache", "__pycache__", "remotion"}
EXCLUDED_SUFFIXES = {".partial", ".blend1", ".log", ".pyc"}
FORBIDDEN_NAME_PARTS = (
    "runtime.local.json",
    "runtime.json",
    "api-key",
    "model.safetensors",
    "profile-",
    "weights/",
    ".safetensors",
    ".ttc",
    ".ttf",
)


def add_path(selected: set[str], root: Path, relative: str) -> None:
    path = resolve_inside(root, relative)
    if not path.is_file():
        raise FileNotFoundError(path)
    selected.add(relative_posix(path, root))


def collect(job: Path, include_media: bool) -> list[str]:
    selected: set[str] = set()
    for name in (
        "project.json",
        "shots.json",
        "README.md",
        "LICENSE",
        "rights.json",
        "events.json",
        "artifact-manifest.json",
        "quality-review.json",
        "technical-review.json",
        "source-dependency-review.json",
        "phase-repair-provenance.json",
    ):
        if (job / name).is_file():
            add_path(selected, job, name)
    project = read_json(job / "project.json")
    manifest = read_json(job / "shots.json")
    voice = project.get("voice", {})
    if voice.get("path"):
        add_path(selected, job, voice["path"])
    if voice.get("cues"):
        add_path(selected, job, voice["cues"])
    if project.get("narrative_manifest"):
        add_path(selected, job, project["narrative_manifest"])
    for shot in manifest.get("shots", []):
        add_path(selected, job, shot["source"]["path"])
        if shot.get("receipt"):
            add_path(selected, job, shot["receipt"])
        for dependency in shot.get("dependencies", []):
            add_path(selected, job, dependency["path"])
    for directory in ("sources", "audio", "design"):
        base = job / directory
        if base.is_dir():
            for path in base.rglob("*"):
                if (
                    path.is_file()
                    and not path.is_symlink()
                    and path.suffix.lower() not in EXCLUDED_SUFFIXES
                ):
                    selected.add(relative_posix(path, job))
    if include_media:
        for directory in ("output", "preview/output"):
            base = job / directory
            if base.is_dir():
                for path in base.rglob("*"):
                    if (
                        path.is_file()
                        and not path.is_symlink()
                        and "remotion" not in path.parts
                    ):
                        selected.add(relative_posix(path, job))
    return sorted(selected)


def validate_selected(job: Path, selected: list[str]) -> None:
    for name in selected:
        path = resolve_inside(job, name)
        lower = name.lower()
        if any(part.lower() in EXCLUDED_PARTS for part in path.relative_to(job).parts):
            raise ValueError(f"Reproducible cache or bundle selected: {name}")
        if path.suffix.lower() in EXCLUDED_SUFFIXES or any(
            part in lower for part in FORBIDDEN_NAME_PARTS
        ):
            raise ValueError(f"Potential machine/private asset selected: {name}")


def package(job: Path, destination: Path, include_media: bool) -> dict:
    job = job.resolve()
    selected = collect(job, include_media)
    validate_selected(job, selected)
    entries = [
        {
            "path": name,
            "bytes": (job / name).stat().st_size,
            "sha256": sha256_file(job / name),
        }
        for name in selected
    ]
    manifest = {
        "schema_version": 1,
        "job_kind": "portable-render-source",
        "include_media": include_media,
        "entries": entries,
        "runtime": "external placeholder; runtime, weights, fonts and keys excluded",
        "reproduction_boundary": "source package only; another machine, GPU and human review remain separate evidence",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = destination.with_suffix(".manifest.json")
    write_json(manifest_path, manifest)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5
    ) as archive:
        for entry in entries:
            archive.write(job / entry["path"], entry["path"])
        archive.writestr(
            "portable-manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        archive.writestr(
            "render-only-runtime.example.json",
            json.dumps(
                {
                    "font": "<readable-Chinese-font>",
                    "remotion_install": "<pinned-Remotion-install>",
                    "ffprobe": "<ffprobe-executable>",
                },
                indent=2,
            )
            + "\n",
        )
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        for entry in entries:
            if sha256_file_from_bytes(archive.read(entry["path"])) != entry["sha256"]:
                raise ValueError(f"ZIP hash mismatch: {entry['path']}")
    identity = {
        "archive": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "entries": len(entries),
        "include_media": include_media,
    }
    write_json(destination.with_suffix(".identity.json"), identity)
    return {**identity, "manifest": str(manifest_path)}


def sha256_file_from_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--include-media", action="store_true")
    args = parser.parse_args()
    report = package(args.job, args.output, args.include_media)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
