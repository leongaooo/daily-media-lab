"""从镜头清单启动固定Blender；逐帧回执支持中断后只恢复失效帧。"""

import argparse
from contextlib import nullcontext
import os
from pathlib import Path
import subprocess

from media_storage import job_guard, managed_job
from narrative_media import frame_paths, read_json, validate_manifest


def check_writes(base, shots, job):
    """Verify that the worker writes only within the job covered by its lock."""
    for shot in shots:
        receipt = base / shot["receipt"]
        outputs = [receipt, receipt.with_suffix(receipt.suffix + ".partial")]
        for frame in frame_paths(shot, base):
            outputs.extend((frame, frame.with_name(frame.stem + ".partial.png")))
        for output in outputs:
            absolute = Path(os.path.abspath(output))
            resolved = output.resolve()
            if job is None:
                if managed_job(absolute) or managed_job(resolved):
                    raise ValueError(
                        f"Managed output requires a job manifest: {output}"
                    )
            elif not absolute.is_relative_to(job) or resolved != absolute:
                raise ValueError(f"Blender output is outside the locked job: {output}")


def render_shots(path, blender, shots):
    worker = Path(__file__).with_name("blender_worker.py")
    for shot in shots:
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


def run(manifest_path, blender, shot_id=None):
    # Resolve old junction aliases so both production and cleanup use the same lock.
    path = Path(manifest_path).resolve()
    job = managed_job(path)
    with job_guard(job) if job else nullcontext():
        manifest = read_json(path)
        validate_manifest(manifest, path.parent, delivery=False, check_frames=False)
        shots = [
            shot
            for shot in manifest["shots"]
            if not shot_id or shot["shot_id"] == shot_id
        ]
        if not shots:
            raise ValueError("Unknown shot id")
        check_writes(path.parent, shots, job)
        render_shots(path, blender, shots)
        validate_manifest(manifest, path.parent, delivery=False, only_shot=shot_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--blender", required=True)
    parser.add_argument("--shot")
    args = parser.parse_args()
    run(args.manifest, args.blender, args.shot)
