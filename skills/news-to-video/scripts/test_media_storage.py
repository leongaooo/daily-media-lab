import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from media_storage import clean_packs, job_guard, render_storage


class MediaStorageTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.job = self.root / "jobs/2026-11-27/episode"
        self.output = self.job / "output"
        self.pack = Path(
            "output/remotion/node_modules/.cache/webpack/"
            "remotion-production-4.0.542/aeebaeebaeebaeeb/0.pack"
        )
        target = self.job / self.pack
        target.parent.mkdir(parents=True)
        target.write_bytes(b"reviewed Webpack pack")
        (self.output / "video.mp4").write_bytes(b"delivery")
        self.report = self.root / "cleanup.json"

    def clean(self, *paths, apply=False):
        return clean_packs(
            self.job,
            paths,
            self.report,
            reason="Checked source, references and writer",
            apply=apply,
        )

    def test_only_reviewed_packs_are_removed(self):
        result = self.clean(
            self.pack, Path("../out.pack"), Path("output/video.mp4"), apply=True
        )
        self.assertEqual(
            [item["status"] for item in result["entries"]],
            ["removed", "skipped", "skipped"],
        )
        self.assertEqual(result["removed_file_bytes"], len(b"reviewed Webpack pack"))
        self.assertFalse((self.job / self.pack).exists())
        self.assertTrue((self.output / "video.mp4").exists())
        self.assertEqual(json.loads(self.report.read_text(encoding="utf8")), result)

    def test_inventory_leaves_pack_in_place(self):
        self.assertEqual(self.clean(self.pack)["entries"][0]["status"], "eligible")
        self.assertTrue((self.job / self.pack).exists())

    def test_active_job_blocks_cleanup(self):
        with job_guard(self.job), self.assertRaisesRegex(ValueError, "active"):
            self.clean(self.pack, apply=True)
        self.assertFalse(self.report.exists())
        self.assertTrue((self.job / self.pack).exists())

    def test_symlink_escape_is_skipped(self):
        target = self.job / self.pack
        external = self.root / "original"
        external.write_bytes(b"protected")
        target.unlink()
        try:
            target.symlink_to(external)
        except OSError as error:
            self.skipTest(f"Symlinks unavailable: {error}")
        self.assertEqual(
            self.clean(self.pack, apply=True)["entries"][0]["status"], "skipped"
        )
        self.assertEqual(external.read_bytes(), b"protected")

    def test_hardlinked_pack_is_skipped(self):
        external = self.root / "original"
        external.hardlink_to(self.job / self.pack)
        self.assertEqual(
            self.clean(self.pack, apply=True)["entries"][0]["status"], "skipped"
        )
        self.assertTrue(external.exists())

    def test_preflight_records_space_and_releases_lock_on_error(self):
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            with render_storage(self.job / "project.json", self.output, 1):
                self.assertTrue(
                    (self.job.parent / ".episode.media-production.lock").is_file()
                )
                raise RuntimeError("render failed")
        self.assertFalse((self.job.parent / ".episode.media-production.lock").exists())
        (report,) = self.output.glob("storage-preflight-*.json")
        self.assertGreater(
            json.loads(report.read_text(encoding="utf8"))["free_bytes"], 0
        )

    def test_budget_blocks_render_before_writing_output(self):
        output = self.job / "unused-output"
        with self.assertRaisesRegex(ValueError, "requested"):
            with render_storage(self.job / "project.json", output, 2**65):
                self.fail("Render entered despite the requested budget")
        self.assertFalse(output.exists())
