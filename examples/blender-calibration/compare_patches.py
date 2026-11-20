"""比较真实PNG母版与最终视频抽帧的色片均值，不对照场景线性RGB猜码值。"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def identity(path):
    return {
        "path": Path(path).name,
        "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
    }


def rgb_image(path, expected_size):
    with Image.open(path) as image:
        if image.size != expected_size:
            raise ValueError(f"Expected {expected_size} without rescaling: {path}")
        return np.asarray(image.convert("RGB"), dtype=np.float64)


def compare(patches_path, master_path, decoded_path):
    """只比较色片内部均值；不能据此证明纹理、运动、物理显示器或视觉质量。"""
    fixture = json.loads(Path(patches_path).read_text(encoding="utf-8"))
    size = (fixture["width"], fixture["height"])
    master = rgb_image(master_path, size)
    decoded = rgb_image(decoded_path, size)
    rows = []
    for patch in fixture["patches"]:
        x0, y0, x1, y1 = patch["sample_box"]
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= 904):
            raise ValueError(
                f"Invalid or subtitle-overlapping sample box: {patch['patch_id']}"
            )
        reference_rgb = master[y0:y1, x0:x1].mean(axis=(0, 1))
        decoded_rgb = decoded[y0:y1, x0:x1].mean(axis=(0, 1))
        rows.append(
            {
                "patch_id": patch["patch_id"],
                "master_rgb_255": reference_rgb.tolist(),
                "decoded_rgb_255": decoded_rgb.tolist(),
                "max_mean_channel_error_255": float(
                    np.max(np.abs(reference_rgb - decoded_rgb))
                ),
            }
        )
    if not rows:
        raise ValueError("No calibration patch sample boxes were supplied")
    return {
        "fixture_id": fixture["fixture_id"],
        "comparison": "actual display-transformed PNG master versus decoded final-video frame; RGB code-value means on a 0..255 scale",
        "inputs": {
            "patches": identity(patches_path),
            "master": identity(master_path),
            "decoded": identity(decoded_path),
        },
        "patch_mean_max_error_255": max(
            row["max_mean_channel_error_255"] for row in rows
        ),
        "patches": rows,
        "limits": [
            "No automatic aesthetic or perceptual acceptance threshold.",
            "Scene-linear inputs are not expected sRGB output codes.",
            "Mean patch error does not prove texture, motion, gamma correctness across all images, monitor calibration, narration or fresh-machine reproducibility.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patches", required=True)
    parser.add_argument("--master", required=True)
    parser.add_argument("--decoded", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = Path(args.report).resolve()
    if report.exists() or report in {
        Path(value).resolve() for value in [args.patches, args.master, args.decoded]
    }:
        raise ValueError("Report must be a new output file, not an existing artifact")
    result = compare(args.patches, args.master, args.decoded)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Maximum patch-mean channel difference: {result['patch_mean_max_error_255']:.6f} / 255; interpret with the documented limits."
    )


if __name__ == "__main__":
    main()
