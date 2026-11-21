"""验证冻结采样精确性、源文件保护和审片窗口写入失败的边界。"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

import review_window
from review_window import extract_review_window


class ReviewWindowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "final-dry.wav"
        self.output = self.root / "review.wav"
        self.receipt = self.root / "review.wav.identity.json"
        self.samples = np.array(
            [0.0, -0.875, 0.125, 0.25, -0.5, 0.999, 0.03125, -0.125],
            dtype="float64",
        )
        sf.write(self.source, self.samples, 24000, subtype="DOUBLE")
        self.source_bytes = self.source.read_bytes()

    def assert_source_unchanged(self):
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def assert_no_outputs(self):
        self.assertFalse(os.path.lexists(self.output))
        self.assertFalse(os.path.lexists(self.receipt))
        self.assertEqual(list(self.root.glob(".*.tmp")), [])
        self.assert_source_unchanged()

    def test_exact_samples_and_identity_preserve_original(self):
        identity = extract_review_window(self.source, 2, 7, self.output)
        recovered, sample_rate = sf.read(self.output, dtype="float64")
        np.testing.assert_array_equal(recovered, self.samples[2:7])
        self.assertEqual(sample_rate, 24000)
        self.assertEqual(sf.info(self.output).subtype, "DOUBLE")
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8")), identity)
        self.assertEqual(identity["source"]["path"], str(self.source.resolve()))
        self.assertEqual(
            identity["source"]["sha256"],
            hashlib.sha256(self.source_bytes).hexdigest(),
        )
        self.assertEqual(identity["source"]["samples"], len(self.samples))
        self.assertEqual(identity["source"]["sample_rate"], 24000)
        self.assertEqual(identity["source"]["channels"], 1)
        self.assertEqual(identity["window"]["path"], str(self.output.resolve()))
        self.assertEqual(
            identity["window"]["sha256"],
            hashlib.sha256(self.output.read_bytes()).hexdigest(),
        )
        self.assertEqual(identity["window"]["samples"], 5)
        self.assertEqual(identity["window"]["start_sample"], 2)
        self.assertEqual(identity["window"]["end_sample"], 7)
        self.assertEqual(identity["window"]["offset_samples"], 2)
        self.assertEqual(identity["window"]["offset_seconds"], 2 / 24000)
        self.assertEqual(identity["playback_rate"], 1)
        self.assertEqual(identity["voice_transforms"], [])
        self.assertIs(identity["tts_invoked"], False)
        self.assertNotEqual(identity["window"]["sha256"], identity["source"]["sha256"])
        self.assertEqual(list(self.root.glob(".*.tmp")), [])
        self.assert_source_unchanged()

    def test_integer_pcm_is_preserved_without_quantizing_the_window(self):
        for subtype in ("PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"):
            with self.subTest(subtype=subtype):
                source = self.root / f"{subtype}.wav"
                output = self.root / f"{subtype}-window.wav"
                sf.write(source, self.samples, 44100, subtype=subtype)
                original = source.read_bytes()
                decoded, _ = sf.read(source, dtype="float64")
                extract_review_window(source, 0, len(decoded), output)
                recovered, rate = sf.read(output, dtype="float64")
                np.testing.assert_array_equal(recovered, decoded)
                self.assertEqual(rate, 44100)
                self.assertEqual(source.read_bytes(), original)

    def test_bad_intervals_fail_before_any_temporary_file(self):
        intervals = (
            (-1, 5),
            (3, 3),
            (4, 2),
            (0, 9),
            (8, 9),
            (False, 3),
            (0, True),
            (1.0, 3),
            (0, 3.0),
            ("0", 3),
            (0, None),
        )
        for start_sample, end_sample in intervals:
            with (
                self.subTest(start=start_sample, end=end_sample),
                patch("review_window.tempfile.mkstemp") as create_temp,
            ):
                with self.assertRaises(ValueError):
                    extract_review_window(
                        self.source, start_sample, end_sample, self.output
                    )
                create_temp.assert_not_called()
                self.assert_no_outputs()

    def test_stereo_source_rejected_before_writing(self):
        sf.write(self.source, np.column_stack((self.samples, self.samples)), 24000)
        self.source_bytes = self.source.read_bytes()
        with patch("review_window.tempfile.mkstemp") as create_temp:
            with self.assertRaisesRegex(ValueError, "mono"):
                extract_review_window(self.source, 0, 4, self.output)
            create_temp.assert_not_called()
        self.assert_no_outputs()

    def test_empty_nonfinite_and_clipped_sources_rejected(self):
        for invalid in ([], [np.nan], [np.inf], [-np.inf], [1.0], [-1.0], [1.2]):
            with self.subTest(samples=invalid):
                sf.write(self.source, np.asarray(invalid), 24000, subtype="DOUBLE")
                self.source_bytes = self.source.read_bytes()
                with patch("review_window.tempfile.mkstemp") as create_temp:
                    with self.assertRaises(ValueError):
                        extract_review_window(self.source, 0, 1, self.output)
                    create_temp.assert_not_called()
                self.assert_no_outputs()

    def test_existing_output_or_receipt_is_never_overwritten(self):
        for existing in (self.output, self.receipt):
            with self.subTest(existing=existing.name):
                existing.write_bytes(b"user-owned file")
                try:
                    with patch("review_window.tempfile.mkstemp") as create_temp:
                        with self.assertRaises(FileExistsError):
                            extract_review_window(self.source, 0, 4, self.output)
                        create_temp.assert_not_called()
                    self.assertEqual(existing.read_bytes(), b"user-owned file")
                    self.assert_source_unchanged()
                finally:
                    existing.unlink()
        self.assert_no_outputs()

    def test_source_as_output_and_hard_link_alias_rejected(self):
        with self.assertRaisesRegex(ValueError, "aliases"):
            extract_review_window(self.source, 0, 4, self.source)
        os.link(self.source, self.output)
        with self.assertRaisesRegex(ValueError, "aliases"):
            extract_review_window(self.source, 0, 4, self.output)
        self.assert_source_unchanged()
        self.assertFalse(self.receipt.exists())

    def test_receipt_alias_of_source_rejected(self):
        os.link(self.source, self.receipt)
        with self.assertRaisesRegex(ValueError, "aliases"):
            extract_review_window(self.source, 0, 4, self.output)
        self.assertFalse(self.output.exists())
        self.assert_source_unchanged()

    def test_symbolic_link_source_alias_is_rejected_when_supported(self):
        try:
            self.output.symlink_to(self.source)
        except OSError as error:
            self.skipTest(f"Host cannot create symbolic links: {error}")
        with self.assertRaisesRegex(ValueError, "aliases"):
            extract_review_window(self.source, 0, 4, self.output)
        self.assertTrue(self.output.is_symlink())
        self.assert_source_unchanged()

    def test_dangling_target_link_is_not_followed_when_supported(self):
        unknown = self.root / "unknown.wav"
        try:
            self.output.symlink_to(unknown)
        except OSError as error:
            self.skipTest(f"Host cannot create symbolic links: {error}")
        with self.assertRaises(FileExistsError):
            extract_review_window(self.source, 0, 4, self.output)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(unknown.exists())
        self.assert_source_unchanged()

    def test_audio_write_failure_removes_only_its_temporary_file(self):
        unknown = self.root / ".someone-elses.tmp"
        unknown.write_bytes(b"keep")

        def fail_write(stream, *args, **kwargs):
            stream.write(b"partial WAV")
            raise OSError("disk full")

        with patch("review_window.sf.write", side_effect=fail_write):
            with self.assertRaisesRegex(OSError, "disk full"):
                extract_review_window(self.source, 0, 4, self.output)
        self.assertEqual(unknown.read_bytes(), b"keep")
        unknown.unlink()
        self.assert_no_outputs()

    def test_receipt_publish_failure_rolls_back_own_audio(self):
        real_link = os.link

        def publish(source, destination):
            if Path(destination) == self.receipt:
                raise OSError("receipt publish failed")
            return real_link(source, destination)

        with patch("review_window.os.link", side_effect=publish):
            with self.assertRaisesRegex(OSError, "receipt publish failed"):
                extract_review_window(self.source, 0, 4, self.output)
        self.assert_no_outputs()

    def test_racing_receipt_is_preserved_and_own_audio_is_rolled_back(self):
        real_link = os.link

        def publish(source, destination):
            if Path(destination) == self.receipt:
                self.receipt.write_bytes(b"another writer")
            return real_link(source, destination)

        with patch("review_window.os.link", side_effect=publish):
            with self.assertRaises(FileExistsError):
                extract_review_window(self.source, 0, 4, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.receipt.read_bytes(), b"another writer")
        self.assertEqual(list(self.root.glob(".*.tmp")), [])
        self.assert_source_unchanged()

    def test_rollback_preserves_a_replaced_output(self):
        real_link = os.link

        def publish(source, destination):
            if Path(destination) == self.receipt:
                self.output.unlink()
                self.output.write_bytes(b"replacement owned by another writer")
                raise OSError("receipt publish failed")
            return real_link(source, destination)

        with patch("review_window.os.link", side_effect=publish):
            with self.assertRaisesRegex(OSError, "receipt publish failed"):
                extract_review_window(self.source, 0, 4, self.output)
        self.assertEqual(
            self.output.read_bytes(), b"replacement owned by another writer"
        )
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.glob(".*.tmp")), [])
        self.assert_source_unchanged()

    def test_cli_creates_the_requested_integer_window(self):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(review_window.__file__)),
                "--source",
                str(self.source),
                "--start-sample",
                "1",
                "--end-sample",
                "5",
                "--output",
                str(self.output),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        identity = json.loads(result.stdout)
        self.assertEqual(identity["window"]["samples"], 4)
        recovered, _ = sf.read(self.output, dtype="float64")
        np.testing.assert_array_equal(recovered, self.samples[1:5])
        self.assert_source_unchanged()


if __name__ == "__main__":
    unittest.main()
