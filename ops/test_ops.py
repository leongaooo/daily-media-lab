"""OPS-01 纯路径与回执判定回归；不启动媒体工具、不读取私人配置。"""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from common import resolve_inside, sha256_file
from recovery_drill import check_receipt


class OpsUtilityTests(unittest.TestCase):
    def test_resolve_inside_rejects_escape_and_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sources").mkdir()
            (root / "sources" / "scene.blend").write_bytes(b"scene")
            self.assertEqual(
                resolve_inside(root, "sources/scene.blend"),
                root / "sources/scene.blend",
            )
            with self.assertRaises(ValueError):
                resolve_inside(root, "../outside.bin")
            with self.assertRaises(ValueError):
                resolve_inside(root, str(root / "sources" / "scene.blend"))

    def test_recovery_detects_missing_receipt_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = root / "frames" / "main" / "000001.png"
            frame.parent.mkdir(parents=True)
            frame.write_bytes(b"frame")
            shot = {
                "media": {"pattern": "frames/main/%06d.png", "source_first_frame": 1},
                "start_frame": 0,
                "end_frame": 1,
            }
            receipt = {"frames": {"frames/main/000001.png": sha256_file(frame)}}
            baseline = check_receipt({}, root, receipt, shot)
            self.assertTrue(baseline["pass"])
            receipt["frames"].clear()
            rejected = check_receipt({}, root, receipt, shot)
            self.assertFalse(rejected["pass"])
            self.assertEqual(rejected["missing_receipt"], ["frames/main/000001.png"])


if __name__ == "__main__":
    unittest.main()
