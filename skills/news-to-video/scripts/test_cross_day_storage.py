"""Replay the cross-day policy without opening any real media job."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from cross_day_storage import choices, govern


class CrossDayStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.root = self.directory / "media"
        self.root.mkdir()
        self.as_of = date(2026, 11, 26)

    def fixture(self, path):
        folder = self.root / path
        folder.mkdir(parents=True)
        (folder / "media.mp4").write_bytes(b"synthetic")
        return folder

    def replay(self, review, name, apply=False):
        return govern(self.root, self.as_of, review, self.directory / name, apply=apply)

    def test_dry_run_apply_and_protection(self):
        old = self.fixture("jobs/2026-11-25/old")
        active = self.fixture("jobs/2026-11-24/active")
        (active.parent / ".active.media-production.lock").touch()
        cache = self.fixture("cache/2026-11-25/reusable")
        current = self.fixture("jobs/2026-11-26/current")
        unowned = self.fixture("cache/undated")
        material = self.fixture("jobs/2026-11-20/reference")
        review = {
            "jobs/2026-11-25/old": {"action": "remove", "reason": "retired"},
            "jobs/2026-11-24/active": {"action": "remove", "reason": "still writing"},
            "cache/2026-11-25/reusable": {"action": "remove", "reason": "rebuildable"},
            "jobs/2026-11-26/current": {"action": "remove", "reason": "current"},
            "jobs/2026-11-20/reference": {"action": "retain", "reason": "baseline"},
        }
        preview = self.replay(review, "dry-run.json")
        self.assertEqual(preview["eligible_bytes"], 18)
        self.assertTrue(old.is_dir())
        actual = self.replay(review, "apply.json", apply=True)
        states = {item["path"]: item["status"] for item in actual["entries"]}
        self.assertEqual(actual["removed_file_bytes"], 18)
        self.assertFalse(old.exists())
        self.assertFalse(cache.exists())
        self.assertEqual(states["jobs/2026-11-24/active"], "skipped")
        for path in (active, current, unowned, material):
            self.assertTrue(path.is_dir())

    def test_nested_lock_and_unreviewed_older_job(self):
        nested = self.fixture("jobs/2026-11-25/nested")
        (nested / "LOCK").touch()
        unreviewed = self.fixture("jobs/2026-11-24/unreviewed")
        review = {"jobs/2026-11-25/nested": {"action": "remove", "reason": "fixture"}}
        result = self.replay(review, "apply.json", apply=True)
        self.assertEqual(
            [item["status"] for item in result["entries"]], ["retained", "skipped"]
        )
        self.assertTrue(nested.is_dir())
        self.assertTrue(unreviewed.is_dir())

    def test_current_dependency_overrides_earlier_remove_review(self):
        baseline = self.fixture("jobs/2026-11-25/baseline")
        old = self.fixture("jobs/2026-11-25/old")
        governance = self.root / "governance"
        governance.mkdir()
        (governance / "active-media-inputs.json").write_text(
            json.dumps(
                [
                    {
                        "path": "jobs/2026-11-25/baseline",
                        "action": "retain",
                        "reason": "current input",
                    }
                ]
            ),
            encoding="utf-8",
        )
        review = {
            "jobs/2026-11-25/baseline": {"action": "remove", "reason": "old review"},
            "jobs/2026-11-25/old": {"action": "remove", "reason": "retired"},
        }
        result = self.replay(review, "active-check.json", apply=True)
        rows = {row["path"]: row for row in result["entries"]}
        self.assertEqual(rows["jobs/2026-11-25/baseline"]["reason"], "current input")
        self.assertTrue(baseline.exists())
        self.assertFalse(old.exists())

    def test_unknown_or_duplicate_review_does_not_delete(self):
        job = self.fixture("jobs/2026-11-25/reviewed")
        review = {
            "jobs/2026-11-25/reviewed": {"action": "remove", "reason": "test"},
            "../unowned": {"action": "remove", "reason": "test"},
        }
        with self.assertRaises(ValueError):
            self.replay(review, "apply.json", apply=True)
        self.assertTrue(job.is_dir())
        path = self.directory / "choices.json"
        row = {"path": "jobs/2026-11-25/reviewed", "action": "remove", "reason": "test"}
        path.write_text(json.dumps([row, row]), encoding="utf-8")
        with self.assertRaises(ValueError):
            choices(path)


if __name__ == "__main__":
    unittest.main()
