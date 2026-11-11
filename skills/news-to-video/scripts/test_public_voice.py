"""公开音色必须能独立工作，并在配置混用、权重损坏时停止。"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from public_voice import PUBLIC_VOICE_ID, checksum, download_model, load_public_profile
from voice_backend import make_voice, validate_voice


class PublicVoiceTests(unittest.TestCase):
    def test_setup_failure_keeps_existing_runtime(self):
        from types import SimpleNamespace
        from setup_public_voice import setup_public

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / "runtime.json"
            runtime.write_text('{"existing": true}', encoding="utf-8")
            executable = Path(__file__)
            args = SimpleNamespace(
                model=folder,
                download=False,
                cache=folder,
                render_python=executable,
                tts_python=executable,
                font=executable,
                ffprobe=None,
            )
            with patch(
                "setup_public_voice.load_public_profile",
                side_effect=ValueError("checksum mismatch"),
            ):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    setup_public(args)
            self.assertEqual(runtime.read_text(), '{"existing": true}')
            self.assertEqual(list(root.iterdir()), [runtime])

    def test_audio_migration_preserves_explicit_public_voice(self):
        from migrate_audio import migrate

        voice = {"id": PUBLIC_VOICE_ID, "speed": 1.0}
        updated, report = migrate({"voice": voice})
        self.assertEqual(updated["voice"], voice)
        self.assertFalse(report["timeline_requires_regeneration"])

    def test_public_profile_needs_no_private_reference_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = root / "config.json"
            model.write_text("{}", encoding="utf-8")
            profile = root / "profile.json"
            profile.write_text(
                json.dumps({"id": PUBLIC_VOICE_ID, "model_dir": folder}),
                encoding="utf-8",
            )
            pinned = {
                "files": {"config.json": checksum(model)},
                "model": "test-model",
                "revision": "test-revision",
                "speaker": "Uncle_Fu",
                "language": "Chinese",
                "settings": {"seed": 2026},
                "license": "Apache-2.0",
                "source_url": "https://example.test/model",
            }
            runtime = {"voice_id": PUBLIC_VOICE_ID, "voice_profile": str(profile)}
            with patch("public_voice.policy", return_value=pinned):
                loaded, identity = load_public_profile(runtime)
                self.assertNotIn("reference_audio", loaded)
                self.assertEqual(identity["speaker"], "Uncle_Fu")
                model.write_text("tampered", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    load_public_profile(runtime, verify_weights=False)
                model.unlink()
                with self.assertRaises(FileNotFoundError):
                    load_public_profile(runtime)

    def test_explicit_selection_cannot_silently_use_other_runtime(self):
        validate_voice({"voice": {"id": PUBLIC_VOICE_ID}})
        for invalid_id in ([], {}, True, None):
            with self.subTest(invalid_id=invalid_id), self.assertRaises(ValueError):
                validate_voice({"voice": {"id": invalid_id}})
        for project_id, runtime_id in (
            (PUBLIC_VOICE_ID, "b-male-v1"),
            ("b-male-v1", PUBLIC_VOICE_ID),
        ):
            with patch("voice_backend.load_profile") as load:
                with self.assertRaisesRegex(ValueError, "refusing silent"):
                    make_voice(
                        {"voice": {"id": project_id}},
                        {"voice_id": runtime_id},
                        Path("unused"),
                    )
                load.assert_not_called()

    def test_failed_download_preserves_previous_file_and_cleans_partial(self):
        import io

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "model.safetensors"
            target.write_bytes(b"previous")
            pinned = {
                "model": "test-model",
                "revision": "test-revision",
                "files": {target.name: "incorrect-checksum"},
            }
            with (
                patch("public_voice.policy", return_value=pinned),
                patch(
                    "public_voice.urllib.request.urlopen",
                    return_value=io.BytesIO(b"bad"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    download_model(folder)
            self.assertEqual(target.read_bytes(), b"previous")
            self.assertFalse(list(Path(folder).glob("*.partial")))


if __name__ == "__main__":
    unittest.main()
