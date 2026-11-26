"""Verify the Blender runner and cross-day maintenance use the same job lock."""

from datetime import date
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from blender_render import run
from cross_day_storage import govern
from frozen_audio import file_hash
from media_storage import job_guard
from narrative_media import seal


class BlenderStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.job = self.root / "jobs" / "2026-11-25" / "episode"
        self.manifest = self.job / "preview" / "shots.json"
        self.lock = self.job.parent / ".episode.media-production.lock"

    def write_manifest(self, path, receipt="receipts/sample.json"):
        path.parent.mkdir(parents=True, exist_ok=True)
        source = path.parent / "scene.blend"
        source.write_bytes(b"synthetic Blender source")
        document = {
            "schema_version": 1,
            "fps": 24,
            "shots": [
                {
                    "shot_id": "sample",
                    "story_world": "test",
                    "start_frame": 0,
                    "end_frame": 1,
                    "source": {"path": source.name, "sha256": file_hash(source)},
                    "dependencies": [],
                    "render": {
                        "width": 8,
                        "height": 8,
                        "fps": 24,
                        "blender_version": "4.4.3",
                        "engine": "BLENDER_EEVEE_NEXT",
                        "seed": 0,
                        "samples": 1,
                        "denoise": False,
                        "display_transform": "Standard",
                        "look": "None",
                        "exposure": 0,
                        "gamma": 1,
                    },
                    "media": {
                        "role": "proxy",
                        "pattern": "frames/%06d.png",
                        "source_first_frame": 1,
                        "bit_depth": 8,
                        "color_space": "display-srgb",
                        "alpha": "opaque",
                    },
                    "handles": {"head": 0, "tail": 0},
                    "facts": {
                        "kind": "explanation",
                        "label": "test",
                        "evidence_ids": ["test"],
                        "prohibited_implications": [],
                    },
                    "receipt": receipt,
                }
            ],
        }
        path.write_text(json.dumps(document), encoding="utf-8")

    def write_frame(self, manifest):
        frame = manifest.parent / "frames" / "000001.png"
        frame.parent.mkdir()
        Image.new("RGB", (8, 8)).save(frame)
        seal(manifest)

    def test_nested_blender_render_blocks_cross_day_retirement(self):
        self.write_manifest(self.manifest)

        def simulate_blender(command, *, check):
            self.assertTrue(check)
            self.assertEqual(command[-2:], [str(self.manifest), "sample"])
            self.assertTrue(self.lock.is_file())
            retired = self.job.relative_to(self.root).as_posix()
            review = {retired: {"action": "remove", "reason": "test fixture"}}
            report = govern(
                self.root,
                date(2026, 11, 26),
                review,
                self.root / "retirement.json",
                apply=True,
            )
            entry = next(item for item in report["entries"] if item["path"] == retired)
            self.assertEqual(entry["status"], "skipped")
            self.write_frame(self.manifest)

        with patch("blender_render.subprocess.run", side_effect=simulate_blender):
            run(self.manifest, "blender", "sample")
        self.assertFalse(self.lock.exists())

    def test_existing_job_lock_blocks_blender_and_failed_render_releases_its_lock(self):
        self.write_manifest(self.manifest)
        failure = subprocess.CalledProcessError(1, "blender")
        with patch("blender_render.subprocess.run", side_effect=failure) as child:
            with job_guard(self.job), self.assertRaisesRegex(
                ValueError, "Job is active"
            ):
                run(self.manifest, "blender")
            child.assert_not_called()

            with self.assertRaises(subprocess.CalledProcessError):
                run(self.manifest, "blender")
            child.assert_called_once()
        self.assertFalse(self.lock.exists())

    def test_managed_output_cannot_escape_its_lock_in_either_direction(self):
        self.write_manifest(self.manifest, str(self.root / "external.json"))
        unmanaged = self.root / "standalone" / "shots.json"
        self.write_manifest(unmanaged, str(self.job / "external.json"))

        with patch("blender_render.subprocess.run") as child:
            with self.assertRaisesRegex(ValueError, "outside the locked job"):
                run(self.manifest, "blender")
            with self.assertRaisesRegex(ValueError, "requires a job manifest"):
                run(unmanaged, "blender")
            child.assert_not_called()
        self.assertFalse(self.lock.exists())

    def test_standalone_package_renders_without_a_job_lock(self):
        unmanaged = self.root / "standalone" / "shots.json"
        self.write_manifest(unmanaged)

        def simulate_blender(command, *, check):
            self.assertTrue(check)
            self.assertEqual(command[-2], str(unmanaged))
            self.assertFalse(self.lock.exists())
            self.write_frame(unmanaged)

        with patch("blender_render.subprocess.run", side_effect=simulate_blender):
            run(unmanaged, "blender")


if __name__ == "__main__":
    unittest.main()
