"""版本化 Blender 镜头交接、逐帧身份及可恢复母版检查。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
from tempfile import NamedTemporaryFile

from PIL import Image

from frozen_audio import file_hash
from media_storage import plain_chain

WORKER_PATH = Path(__file__).with_name("blender_worker.py")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def source_identity(shot, base):
    """源blend包含相机/材质/动作；外链资产和模拟烘焙须逐项显式登记。"""
    sources = [shot["source"], *shot.get("dependencies", [])]
    for source in sources:
        if file_hash(base / source["path"]) != source["sha256"]:
            raise ValueError(f"Source/dependency checksum mismatch: {source['path']}")
    # 新项目把摄影实际消费的事件子集作为缓存依赖；旧项目不添空字段，
    # 避免仅升级联合导演校验就使既有无事件镜头全部失效。
    camera_contract = {
        key: shot[key]
        for key in ("camera_sha256", "camera_events_sha256", "camera_event_names")
        if key in shot
    }
    return digest(
        {
            "worker_sha256": file_hash(WORKER_PATH),
            "shot": {
                **{
                    key: shot[key]
                    for key in (
                        "source",
                        "dependencies",
                        "render",
                        "media",
                        "start_frame",
                        "end_frame",
                        "handles",
                    )
                },
                **camera_contract,
            },
        }
    )


def frame_paths(shot, base):
    media = shot["media"]
    count = shot["end_frame"] - shot["start_frame"]
    first = media["source_first_frame"]
    return [base / (media["pattern"] % frame) for frame in range(first, first + count)]


def inspect_frame(path, media, render):
    """解码完整PNG，并读IHDR真实位深；Pillow模式不能证明16位RGB。"""
    with Path(path).open("rb") as stream:
        header = stream.read(26)
    if len(header) != 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a complete PNG frame: {path}")
    width, height, depth, color_type = struct.unpack(">IIBB", header[16:26])
    if (width, height) != (render["width"], render["height"]) or depth != media[
        "bit_depth"
    ]:
        raise ValueError(f"Frame dimensions/bit depth mismatch: {path}")
    if color_type not in (2, 6):
        raise ValueError("Narrative PNG master must be RGB or RGBA")
    if media["alpha"] == "opaque" and color_type == 6:
        with Image.open(path) as picture:
            if picture.getextrema()[-1] != (255, 255):
                raise ValueError("Opaque master contains transparent pixels")
    with Image.open(path) as picture:
        picture.load()
    return file_hash(path)


def validate_manifest(
    manifest, base, total_frames=None, delivery=True, check_frames=True, only_shot=None
):
    """验证半开帧区间连续覆盖；代理、旧身份及缺帧不可作为正式母版。"""
    if manifest.get("schema_version") != 1 or manifest.get("fps") != 24:
        raise ValueError("Narrative manifest requires schema_version=1, fps=24")
    shots = manifest.get("shots", [])
    if not shots:
        raise ValueError("Narrative manifest needs shots")
    cursor = 0
    seen = set()
    for shot in shots:
        required = {
            "shot_id",
            "story_world",
            "start_frame",
            "end_frame",
            "source",
            "dependencies",
            "render",
            "media",
            "handles",
            "facts",
            "receipt",
        }
        if not required <= set(shot):
            raise ValueError(
                "Narrative shot missing required source/render/media/facts identity"
            )
        start, end = shot["start_frame"], shot["end_frame"]
        if (
            type(start) is not int
            or type(end) is not int
            or start != cursor
            or end <= start
        ):
            raise ValueError(
                "Narrative shots must partition the integer-frame program without gaps"
            )
        if shot["shot_id"] in seen or not shot["shot_id"] or not shot["story_world"]:
            raise ValueError("Shot ids must be unique and story_world must be named")
        if not isinstance(shot["shot_id"], str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,80}", shot["shot_id"]
        ):
            raise ValueError("shot_id must be a safe stable identifier")
        seen.add(shot["shot_id"])
        cursor = end
        media, render, facts = shot["media"], shot["render"], shot["facts"]
        if media.get("role") not in ("master", "proxy") or (
            delivery and media["role"] != "master"
        ):
            raise ValueError("A proxy cannot stand in for a delivery master")
        if render.get("fps") != 24 or (
            delivery and (render.get("width"), render.get("height")) != (1920, 1080)
        ):
            raise ValueError("Delivery masters require 1920x1080 at 24fps")
        if any(
            key not in render
            for key in (
                "blender_version",
                "engine",
                "seed",
                "samples",
                "denoise",
                "display_transform",
                "look",
                "exposure",
                "gamma",
            )
        ):
            raise ValueError(
                "Record the actual engine, version, sampling and display settings"
            )
        if (
            media.get("bit_depth") not in (8, 16)
            or media.get("color_space") != "display-srgb"
            or media.get("alpha") != "opaque"
        ):
            raise ValueError(
                "v1 supports opaque display-sRGB PNG masters with declared bit depth"
            )
        if (
            type(media.get("source_first_frame")) is not int
            or media["source_first_frame"] < 1
        ):
            raise ValueError("Blender source_first_frame starts at 1")
        if (
            facts.get("kind") not in ("observation", "explanation", "metaphor")
            or not facts.get("label")
            or not isinstance(facts.get("prohibited_implications"), list)
        ):
            raise ValueError(
                "Declare visual role, display label and prohibited factual implications"
            )
        if not isinstance(facts.get("evidence_ids"), list) or not facts["evidence_ids"]:
            raise ValueError("Shots must trace to evidence ids")
        if any(
            type(shot["handles"].get(key)) is not int or shot["handles"][key] < 0
            for key in ("head", "tail")
        ):
            raise ValueError(
                "Transition handles must be separate nonnegative frame counts"
            )
        identity = source_identity(shot, base)
        if check_frames and (only_shot is None or shot["shot_id"] == only_shot):
            receipt = read_json(base / shot["receipt"])
            if receipt.get("identity") != identity:
                raise ValueError(
                    "Shot render identity changed; re-render affected frames"
                )
            paths = frame_paths(shot, base)
            hashes = receipt.get("frames", {})
            if len(hashes) != len(paths):
                raise ValueError("Incomplete frame receipt")
            for path in paths:
                if inspect_frame(path, media, render) != hashes.get(
                    str(path.relative_to(base)).replace("\\", "/")
                ):
                    raise ValueError(
                        f"Frame content differs from sealed master: {path}"
                    )
    if total_frames is not None and cursor != total_frames:
        raise ValueError(
            "Narrative master range does not match frozen audio frame count"
        )
    return cursor


def seal(manifest_path, shot_id=None):
    """导入已渲染序列的显式封存操作，不推断其美术或事实已验收。"""
    path = Path(manifest_path).resolve()
    manifest = read_json(path)
    validate_manifest(manifest, path.parent, delivery=False, check_frames=False)
    for shot in manifest["shots"]:
        if shot_id and shot["shot_id"] != shot_id:
            continue
        identity = source_identity(shot, path.parent)
        frames = {
            str(frame.relative_to(path.parent)).replace("\\", "/"): inspect_frame(
                frame, shot["media"], shot["render"]
            )
            for frame in frame_paths(shot, path.parent)
        }
        atomic_json(
            path.parent / shot["receipt"],
            {"identity": identity, "frames": frames, "review": "technical-seal-only"},
        )


def stage_directories(manifest, base, public):
    """Resolve the renderer's immutable directory for each source identity."""
    for shot in manifest["shots"]:
        identity = source_identity(shot, base)
        # 完整身份包含源、局部取帧和全局边界。省略镜头名以缩短 Windows 路径。
        yield shot, identity, public / "narrative" / identity


def sealed_stage_pairs(manifest_path, public, total_frames, job):
    """List generated paths with their master sources and sealed frame digests."""
    manifest = read_json(manifest_path)
    base = manifest_path.parent
    validate_manifest(manifest, base, total_frames, check_frames=False)
    for shot, identity, destination in stage_directories(manifest, base, public):
        sources = frame_paths(shot, base)
        receipt_path = base / shot["receipt"]
        dependencies = [shot["source"], *shot["dependencies"]]
        # The stage cleanup lock must protect the retained inputs as well as the copies.
        for path in (
            receipt_path,
            *(base / dependency["path"] for dependency in dependencies),
            *sources,
        ):
            absolute = Path(os.path.abspath(path))
            if not absolute.is_relative_to(job):
                raise ValueError(
                    f"Stage recovery input is outside the locked job: {absolute}"
                )
            plain_chain(absolute)
        receipt = read_json(receipt_path)
        hashes = receipt.get("frames", {})
        if receipt.get("identity") != identity or len(hashes) != len(sources):
            raise ValueError(f"Missing sealed frame evidence for {shot['shot_id']}")
        for index, source in enumerate(sources):
            expected = hashes.get(source.relative_to(base).as_posix(), "")
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError(f"Missing sealed digest for {source}")
            yield destination / f"{index:06}.png", source, expected


def stage_manifest(project, base, public, total_frames):
    """逐字节拷贝母版，不经Pillow重存，不把代理或8位重编码冒充源母版。"""
    path = (base / project["narrative_manifest"]).resolve()
    manifest = read_json(path)
    validate_manifest(manifest, path.parent, total_frames)
    public = public.absolute()
    staged = []
    for shot, identity, destination in stage_directories(manifest, path.parent, public):
        parent = next(
            part
            for part in (destination, *destination.parents)
            if os.path.lexists(part)
        )
        plain_chain(parent)
        destination.mkdir(parents=True, exist_ok=True)
        frames = []
        for index, source in enumerate(frame_paths(shot, path.parent)):
            target = destination / f"{index:06}.png"
            if not target.is_file() or file_hash(target) != file_hash(source):
                # Replacing the staging name does not overwrite an existing linked file.
                with NamedTemporaryFile(dir=destination, delete=False) as handle:
                    temporary = Path(handle.name)
                try:
                    shutil.copyfile(source, temporary)
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
            frames.append(str(target.relative_to(public)).replace("\\", "/"))
        staged.append(
            {
                "shot_id": shot["shot_id"],
                "start_frame": shot["start_frame"],
                "end_frame": shot["end_frame"],
                "frames": frames,
                "label": shot["facts"]["label"],
                "evidence_ids": shot["facts"]["evidence_ids"],
                "master_identity": identity,
            }
        )
    return staged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--shot")
    args = parser.parse_args()
    if args.seal:
        seal(args.manifest, args.shot)
    else:
        path = Path(args.manifest).resolve()
        print(validate_manifest(read_json(path), path.parent))
