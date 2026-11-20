"""从镜头清单启动固定Blender；逐帧回执支持中断后只恢复失效帧。"""

import argparse
from pathlib import Path
import subprocess

from narrative_media import read_json, validate_manifest


def run(manifest_path, blender, shot_id=None):
    path = Path(manifest_path).resolve()
    manifest = read_json(path)
    validate_manifest(manifest, path.parent, delivery=False, check_frames=False)
    if shot_id and not any(shot["shot_id"] == shot_id for shot in manifest["shots"]):
        raise ValueError("Unknown shot id")
    worker = Path(__file__).with_name("blender_worker.py")
    for shot in manifest["shots"]:
        if shot_id and shot["shot_id"] != shot_id:
            continue
        subprocess.run(
            [
                str(blender),
                "--background",
                str(path.parent / shot["source"]["path"]),
                "--python-exit-code",
                "1",
                "--python",
                str(worker),
                "--",
                str(path),
                shot["shot_id"],
            ],
            check=True,
        )
    validate_manifest(manifest, path.parent, delivery=False, only_shot=shot_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--blender", required=True)
    parser.add_argument("--shot")
    args = parser.parse_args()
    run(args.manifest, args.blender, args.shot)
