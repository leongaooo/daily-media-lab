"""OPS-01 的无第三方依赖基础工具。

这些函数只处理路径、JSON、哈希和报告数据。媒体契约的实际校验仍由
``skills/news-to-video/scripts`` 中的权威校验器负责，避免工程化入口复制一套
会逐渐漂移的节目规则。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path) -> str:
    """以分块方式读取文件，避免为计算身份把大媒体整体载入内存。"""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    """读取 UTF-8 JSON；OPS 报告不接受隐式编码或宽松 JSON。"""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    """原子替换一份人类可读的 JSON 报告。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def resolve_inside(root: Path, relative: str) -> Path:
    """解析相对资产并拒绝绝对路径、越界路径和符号链接。

    可搬迁包只允许在作业根内重新建立相同相对路径；符号链接会把这个
    保证变成依赖宿主外部状态，因此即使目标最终落在根目录内也拒绝。
    """

    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive:
        raise ValueError(f"Absolute asset path is not portable: {relative}")
    path = (root / candidate).resolve(strict=False)
    root_resolved = root.resolve()
    if not path.is_relative_to(root_resolved):
        raise ValueError(f"Asset path escapes job root: {relative}")
    current = root_resolved
    for part in path.relative_to(root_resolved).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink asset is not portable: {relative}")
    return path


def iter_files(root: Path) -> Iterable[Path]:
    """返回普通文件，跳过目录链接，避免扫描到作业根外。"""

    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            yield path


def relative_posix(path: Path, root: Path) -> str:
    """输出跨平台包清单使用的正斜杠相对路径。"""

    return path.resolve().relative_to(root.resolve()).as_posix()
