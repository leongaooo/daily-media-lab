"""从冻结的单声道干声提取整数采样窗口，不合成、重采样或处理人声。

窗口按 [start_sample, end_sample) 切片，保持原采样率和 float64 解码值，
另存为 DOUBLE WAV。窗口的文件字节与完整母版不同；回执分别记录二者
的完整文件 SHA256，不把新容器的哈希当成母版身份。
"""

import argparse
import hashlib
import json
from numbers import Integral
import os
from pathlib import Path
import tempfile

import numpy as np
import soundfile as sf


def _sha256(stream):
    stream.seek(0)
    return hashlib.file_digest(stream, "sha256").hexdigest()


def _validate_interval(start_sample, end_sample):
    for name, value in (
        ("start_sample", start_sample),
        ("end_sample", end_sample),
    ):
        # bool 是 int 的子类，但不是有效的采样位置。
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise ValueError(f"{name} must be an integer sample index")
    start_sample, end_sample = int(start_sample), int(end_sample)
    if start_sample < 0 or end_sample <= start_sample:
        raise ValueError("Sample interval must satisfy 0 <= start < end")
    return start_sample, end_sample


def _validate_paths(source, output):
    source_path = Path(source).expanduser().resolve(strict=True)
    if not source_path.is_file():
        raise ValueError("Source must be a regular audio file")

    output_candidate = Path(output).expanduser().absolute()
    if output_candidate.suffix.lower() != ".wav":
        raise ValueError("Output must be a new .wav file")
    receipt_candidate = output_candidate.with_name(
        output_candidate.name + ".identity.json"
    )
    for candidate in (output_candidate, receipt_candidate):
        resolved = candidate.resolve()
        aliases_source = resolved == source_path
        if candidate.exists() and candidate.samefile(source_path):
            aliases_source = True
        if aliases_source:
            raise ValueError("Output or identity receipt aliases the source")
        # lexists 也拒绝悬空符号链接，不能跟随它后覆盖另一条路径。
        if os.path.lexists(candidate):
            raise FileExistsError(f"Refusing to overwrite existing path: {candidate}")
        if not resolved.parent.is_dir():
            raise ValueError(f"Output parent directory must exist: {resolved.parent}")
    return source_path, output_candidate.resolve(), receipt_candidate.resolve()


def _read_source(source_path, start_sample, end_sample):
    """同一只读句柄绑定母版哈希、采样元数据和解码值，并拒绝观测到的变更。"""
    with source_path.open("rb") as source_stream:
        source_sha256 = _sha256(source_stream)
        source_stream.seek(0)
        with sf.SoundFile(source_stream) as audio:
            if audio.channels != 1:
                raise ValueError("Source must be a mono dry vocal master")
            if not audio.frames or end_sample > audio.frames:
                raise ValueError("Sample interval exceeds the nonempty source")
            metadata = {
                "path": str(source_path),
                "sha256": source_sha256,
                "sample_rate": audio.samplerate,
                "samples": audio.frames,
                "channels": audio.channels,
                "format": audio.format,
                "subtype": audio.subtype,
            }
            samples = audio.read(dtype="float64")

        if len(samples) != metadata["samples"]:
            raise ValueError("Source sample count changed while reading")
        if not np.isfinite(samples).all() or np.any(np.abs(samples) >= 1):
            raise ValueError("Source contains non-finite or full-scale/clipped samples")
        same_file = os.path.samestat(
            source_path.stat(), os.fstat(source_stream.fileno())
        )
        if not same_file or _sha256(source_stream) != source_sha256:
            raise ValueError(
                "Source changed while reading; use an immutable final master"
            )
    return samples[start_sample:end_sample], metadata


def _new_temp_file(parent, prefix, owned_files):
    descriptor, name = tempfile.mkstemp(dir=parent, prefix=prefix, suffix=".tmp")
    path = Path(name)
    owned_files.append((path, os.fstat(descriptor)))
    return os.fdopen(descriptor, "w+b"), path


def _remove_owned(path, identity):
    """仅清理仍指向本次创建文件的路径，保留被他方替换的路径。"""
    try:
        current = path.lstat()
    except FileNotFoundError:
        return
    if os.path.samestat(current, identity):
        path.unlink()


def _write_window(samples, sample_rate, stream):
    sf.write(stream, samples, sample_rate, format="WAV", subtype="DOUBLE")
    stream.flush()
    os.fsync(stream.fileno())
    stream.seek(0)
    recovered, recovered_rate = sf.read(stream, dtype="float64")
    if recovered_rate != sample_rate or not np.array_equal(recovered, samples):
        raise ValueError("Written window does not preserve the decoded source samples")
    return _sha256(stream)


def extract_review_window(source, start_sample, end_sample, output):
    """另存只读审片窗口及 <output>.identity.json，返回身份回执。

    入参和完整母版在任何临时文件创建前校验。临时文件与目标在同目录；
    硬链接发布保证既有目标不会被覆盖，文件系统不支持时直接失败。
    两个文件分别原子发布；普通异常时尝试撤销本次已发布文件。强制终止或
    断电不具备双文件事务保证，孤立产物须人工核对，不能自动覆盖重试。
    调用方负责提供已确认的最终干声；本函数不能推断混音来源或听感质量。
    """
    start_sample, end_sample = _validate_interval(start_sample, end_sample)
    source_path, output_path, receipt_path = _validate_paths(source, output)
    samples, source_identity = _read_source(source_path, start_sample, end_sample)
    sample_rate = source_identity["sample_rate"]
    temporary_files = []
    published_files = []
    try:
        audio_stream, audio_temp = _new_temp_file(
            output_path.parent, f".{output_path.name}.", temporary_files
        )
        with audio_stream:
            window_sha256 = _write_window(samples, sample_rate, audio_stream)

        identity = {
            "schema_version": 1,
            "kind": "frozen_voice_review_window",
            "source": source_identity,
            "window": {
                "path": str(output_path),
                "sha256": window_sha256,
                "sample_rate": sample_rate,
                "samples": len(samples),
                "channels": 1,
                "format": "WAV",
                "subtype": "DOUBLE",
                "start_sample": start_sample,
                "end_sample": end_sample,
                "interval": "[start_sample, end_sample)",
                "offset_samples": start_sample,
                "offset_seconds": start_sample / sample_rate,
            },
            "playback_rate": 1,
            "voice_transforms": [],
            "tts_invoked": False,
        }
        receipt_stream, receipt_temp = _new_temp_file(
            receipt_path.parent, f".{receipt_path.name}.", temporary_files
        )
        receipt_content = json.dumps(identity, ensure_ascii=False, indent=2) + "\n"
        with receipt_stream:
            receipt_stream.write(receipt_content.encode("utf-8"))
            receipt_stream.flush()
            os.fsync(receipt_stream.fileno())

        # os.replace 在竞争中会覆盖目标；硬链接要么新建成功，要么原样失败。
        for temporary, destination in (
            (audio_temp, output_path),
            (receipt_temp, receipt_path),
        ):
            file_identity = temporary.stat()
            os.link(temporary, destination)
            published_files.append((destination, file_identity))
    except BaseException as error:
        for path, file_identity in reversed(published_files):
            try:
                _remove_owned(path, file_identity)
            except OSError as cleanup_error:
                error.add_note(
                    f"Could not roll back owned output {path}: {cleanup_error}"
                )
        raise
    finally:
        for path, file_identity in reversed(temporary_files):
            _remove_owned(path, file_identity)
    return identity


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--start-sample", required=True, type=int)
    parser.add_argument("--end-sample", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        identity = extract_review_window(
            args.source, args.start_sample, args.end_sample, args.output
        )
    except (OSError, ValueError, sf.LibsndfileError) as error:
        parser.exit(1, f"review_window: {error}\n")
    print(json.dumps(identity, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
