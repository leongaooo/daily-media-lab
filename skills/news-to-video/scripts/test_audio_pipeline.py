"""覆盖声音禁止回退、旧项目迁移、授权失败和音乐避让等可观察行为。"""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import sys

import numpy as np
import soundfile as sf

from migrate_audio import migrate
from music_bed import (
    DEFAULT_MUSIC,
    duck_envelope,
    loop_bed,
    mix_audio,
    select_track,
    speech_activity,
    validate_music,
    write_attribution,
)
from voice_backend import (
    audio_key,
    denoise_clip,
    load_profile,
    make_voice,
    tempo_clip,
    validate_voice,
)
from setup_runtime import setup


class VoicePolicyTests(unittest.TestCase):
    def test_long_script_uses_bounded_processes_and_reuses_completed_audio(self):
        project = {
            "voice": {"id": "b-male-v1", "speed": 1.0},
            "scenes": [
                {"segments": [{"text": f"口播片段{index}"} for index in range(9)]}
            ],
        }
        sizes = []

        def synthesize(command, **kwargs):
            request = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
            sizes.append(len(request["jobs"]))
            self.assertLessEqual(len(request["jobs"]), 8)
            for job in request["jobs"]:
                sf.write(job["output"], np.ones(1000, dtype="float32") * 0.1, 24000)

        with tempfile.TemporaryDirectory() as folder:
            runtime = {"tts_python": sys.executable}
            with (
                patch(
                    "voice_backend.load_profile",
                    return_value=({}, {"voice_id": "b-male-v1"}),
                ),
                patch("voice_backend.subprocess.run", side_effect=synthesize),
                patch("voice_backend.denoise_clip", side_effect=lambda path: path),
            ):
                items, _ = make_voice(project, runtime, Path(folder))
                self.assertEqual(len(items), 9)
                self.assertEqual(sizes, [8, 1])
                make_voice({**project, "music": {"mode": "off"}}, runtime, Path(folder))
                self.assertEqual(sizes, [8, 1])

    def test_setup_wrong_reference_preserves_existing_working_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile = root / "profiles/b-male-v1/reference.wav"
            profile.parent.mkdir(parents=True)
            profile.write_bytes(b"previous approved reference")
            runtime = root / "runtime.json"
            runtime.write_text('{"existing": true}', encoding="utf-8")
            wrong = root / "wrong.wav"
            wrong.write_bytes(b"incorrect A reference")
            transcript = root / "transcript.txt"
            transcript.write_text("incorrect transcript", encoding="utf-8")
            args = SimpleNamespace(
                cache=str(root),
                font=str(wrong),
                render_python=str(wrong),
                tts_python=str(wrong),
                model=str(root),
                reference=str(wrong),
                reference_text=str(transcript),
            )
            with self.assertRaisesRegex(ValueError, "not the approved B"):
                setup(args)
            self.assertEqual(profile.read_bytes(), b"previous approved reference")
            self.assertEqual(runtime.read_text(encoding="utf-8"), '{"existing": true}')

    def test_omitted_voice_is_b_but_old_ids_cannot_reach_synthesis(self):
        validate_voice({})
        for voice in ({"id": "zm_010"}, {"id": "A"}, {"speed": 0}):
            with (
                self.subTest(voice=voice),
                patch("voice_backend.subprocess.run") as run,
            ):
                with self.assertRaises(ValueError):
                    make_voice({"voice": voice}, {}, Path("unused"))
                run.assert_not_called()

    def test_missing_profile_fails_without_alternate_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = {
                "voice_id": "b-male-v1",
                "voice_profile": str(Path(folder) / "absent.json"),
            }
            with patch("voice_backend.subprocess.run") as run:
                with self.assertRaises(FileNotFoundError):
                    make_voice({}, runtime, Path(folder))
                run.assert_not_called()

    def test_changed_reference_rejected_before_model_load(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "changed.wav").write_bytes(b"different reference")
            profile = {
                "id": "b-male-v1",
                "reference_audio": str(path / "changed.wav"),
                "reference_text": "changed",
            }
            (path / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "approved"):
                load_profile(
                    {
                        "voice_id": "b-male-v1",
                        "voice_profile": str(path / "profile.json"),
                    }
                )

    def test_voice_cache_excludes_music_and_changes_with_reference_or_settings(self):
        identity = {
            "voice_id": "b-male-v1",
            "reference_sha256": "one",
            "settings": {"seed": 2026},
        }
        first = audio_key("同一句口播", identity)
        self.assertEqual(first, audio_key("同一句口播", deepcopy(identity)))
        changed = deepcopy(identity)
        changed["reference_sha256"] = "two"
        self.assertNotEqual(first, audio_key("同一句口播", changed))
        changed = deepcopy(identity)
        changed["settings"]["seed"] = 10
        self.assertNotEqual(first, audio_key("同一句口播", changed))

    def test_migration_preserves_narration_visuals_and_explicit_silence(self):
        project = {
            "voice": {"id": "zm_010", "speed": 1.25},
            "music": {"gain": 0},
            "scenes": [{"segments": [{"text": "原文"}], "image": "keep.png"}],
        }
        snapshot = deepcopy(project)
        updated, report = migrate(project)
        self.assertEqual(project, snapshot)
        self.assertEqual(updated["scenes"], project["scenes"])
        self.assertEqual(updated["voice"], {"id": "b-male-v1", "speed": 1.15})
        self.assertEqual(updated["music"], {"mode": "off"})
        self.assertTrue(report["timeline_requires_regeneration"])

    def test_speed_validation_and_native_reproduction(self):
        for speed in (0.5, 1.0, 1.15, 1.25, 2.0):
            validate_voice({"voice": {"speed": speed}})
        for speed in (True, "1.25", None, float("nan"), float("inf"), 0.49, 2.01):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                validate_voice({"voice": {"speed": speed}})
        updated, _ = migrate({"voice": {"id": "b-male-v1", "speed": 1.0}})
        self.assertEqual(updated["voice"]["speed"], 1.0)

    def test_real_tempo_shortens_duration_preserves_pitch_and_isolates_cache(self):
        sample_rate = 24000
        tone = 0.2 * np.sin(2 * np.pi * 180 * np.arange(sample_rate * 4) / sample_rate)
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / "raw.wav"
            sf.write(raw, tone, sample_rate, subtype="FLOAT")
            original = raw.read_bytes()
            fast = tempo_clip(raw, 1.25)
            audio, rate = sf.read(fast)
            self.assertAlmostEqual(len(audio) / rate, 3.2, delta=0.06)
            spectrum = np.abs(np.fft.rfft(audio))
            peak_hz = np.fft.rfftfreq(len(audio), 1 / rate)[np.argmax(spectrum)]
            self.assertAlmostEqual(peak_hz, 180, delta=1)
            self.assertEqual(raw.read_bytes(), original)
            with patch("voice_backend.subprocess.run") as run:
                self.assertEqual(tempo_clip(raw, 1.25), fast)
                self.assertEqual(tempo_clip(raw, 1.0), raw)
                run.assert_not_called()
            self.assertNotEqual(tempo_clip(raw, 1.5), fast)

    def test_speed_change_uses_raw_b_cache_without_synthesis(self):
        identity = {"voice_id": "b-male-v1"}
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / f"{audio_key('口播', identity)}.wav"
            tone = 0.2 * np.sin(2 * np.pi * 180 * np.arange(48000) / 24000)
            sf.write(raw, tone, 24000)
            with patch("voice_backend.load_profile", return_value=({}, identity)):
                items, metadata = make_voice(
                    {"scenes": [{"segments": [{"text": "口播"}]}]},
                    {"tts_python": sys.executable},
                    Path(folder),
                )
            self.assertEqual(metadata["playback"]["speed"], 1.15)
            self.assertTrue(metadata["cleanup"]["enabled"])
            self.assertTrue(items[0]["key"].startswith("denoise-"))
            self.assertLess(len(items[0]["audio"]), len(tone))
            self.assertTrue(raw.exists())

    def test_denoise_reduces_noise_preserves_length_tail_and_raw_cache(self):
        sample_rate = 24000
        rng = np.random.default_rng(2026)
        audio = rng.normal(0, 0.004, sample_rate * 3).astype("float32")
        tone = 0.15 * np.sin(2 * np.pi * 180 * np.arange(sample_rate) / sample_rate)
        audio[sample_rate : sample_rate * 2] += tone
        # 音频最后一小段保留讲话，检查延迟补偿没有吞掉字尾。
        audio[-2400:] += tone[:2400]
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / "raw.wav"
            sf.write(raw, audio, sample_rate, subtype="FLOAT")
            snapshot = raw.read_bytes()
            cleaned = denoise_clip(raw)
            output, rate = sf.read(cleaned)
            self.assertEqual(rate, sample_rate)
            self.assertEqual(len(output), len(audio))
            self.assertEqual(raw.read_bytes(), snapshot)
            self.assertLess(
                np.std(output[2400 : sample_rate - 2400]),
                0.8 * np.std(audio[2400 : sample_rate - 2400]),
            )
            self.assertGreater(np.corrcoef(output[-1800:], audio[-1800:])[0, 1], 0.98)
            with patch("voice_backend.subprocess.run") as run:
                self.assertEqual(denoise_clip(raw), cleaned)
                run.assert_not_called()
            sf.write(raw, audio * 0.9, sample_rate, subtype="FLOAT")
            self.assertNotEqual(denoise_clip(raw), cleaned)

    def test_denoise_failure_does_not_leave_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / "raw.wav"
            sf.write(raw, np.ones(2400, dtype="float32") * 0.1, 24000)

            def fail(command, **kwargs):
                Path(command[-1]).write_bytes(b"partial")
                raise RuntimeError("filter failed")

            with patch("voice_backend.subprocess.run", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "filter failed"):
                    denoise_clip(raw)
            self.assertEqual(list(Path(folder).glob("denoise-*")), [])


class MusicBehaviorTests(unittest.TestCase):
    def test_pcm_activity_releases_music_despite_full_timeline_gate(self):
        sample_rate = 24000
        voice = np.zeros(sample_rate * 6, dtype="float32")
        voice[sample_rate : sample_rate * 3] = 0.2 * np.sin(
            np.arange(sample_rate * 2) * 2 * np.pi * 160 / sample_rate
        )
        activity = speech_activity(voice, sample_rate)
        self.assertFalse(activity[:sample_rate].any())
        self.assertTrue(activity[sample_rate : sample_rate * 3].all())
        self.assertFalse(activity[sample_rate * 3 :].any())
        duck = duck_envelope(activity, sample_rate)
        self.assertLess(duck[round(0.3 * sample_rate)], 0.01)
        self.assertGreater(duck[sample_rate * 2], 0.99)
        self.assertLess(duck[sample_rate * 5], 0.01)
        mixed, metrics, _ = mix_audio(
            voice, np.ones(len(voice)), sample_rate, {}, {}, "approved defaults"
        )
        self.assertEqual(DEFAULT_MUSIC["relative_db"], -19.0)
        self.assertEqual(metrics["relative_db"], -19.0)
        self.assertEqual(metrics["duck_db"], 2)
        self.assertLess(metrics["fully_ducked_percent"], 60)
        self.assertEqual(mixed.shape, (len(voice), 2))

    def test_legacy_or_nonfinite_music_settings_are_rejected(self):
        for config in (
            {"gain": 0.025},
            {"tempo_multiplier": 1.3},
            {"relative_db": float("nan")},
            {"duck_db": -1},
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                validate_music(config)

    def test_unknown_track_missing_license_or_tampered_audio_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            data = {
                "tracks": [{"id": "test", "styles": ["business"], "license": "unknown"}]
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            runtime = {"music_manifest": str(path)}
            with self.assertRaisesRegex(ValueError, "No matching"):
                select_track({"track_id": "absent"}, runtime, "title")
            with self.assertRaisesRegex(ValueError, "CC BY"):
                select_track({}, runtime, "title")
            track = data["tracks"][0]
            track.update(
                license="CC BY 4.0",
                source_url="https://example.test/song",
                license_url="https://creativecommons.org/licenses/by/4.0/",
                attribution="credit",
                sha256="invalid",
                artist="author",
                title="song",
                file="song.mp3",
            )
            (path.parent / "song.mp3").write_bytes(b"tampered")
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                select_track({}, runtime, "title")

    def test_default_selection_is_restricted_random_pool(self):
        allowed = {"voice-over-under", "tech-live", "inspired"}
        runtime = {
            "music_manifest": str(
                Path(
                    r"C:\Users\xc_sc\.agents\skills\news-to-video\assets\music-pool\manifest.json"
                )
            )
        }
        selected = {
            select_track({}, runtime, f"title-{index}")[1]["id"] for index in range(12)
        }
        self.assertTrue(selected)
        self.assertTrue(selected <= allowed)

    def test_short_pause_holds_duck_and_long_pause_releases(self):
        gate = np.zeros(6000)
        gate[:1000] = 1
        gate[1200:2000] = 1
        duck = duck_envelope(gate, 1000)
        self.assertGreater(duck[1100], 0.95)
        self.assertLess(duck[4000], 0.01)
        self.assertLess(np.max(np.abs(np.diff(duck))), 0.01)

    def test_looping_keeps_shape_and_bounds_join_discontinuity(self):
        samples = np.sin(np.arange(2500) * 0.02).astype("float32")
        stereo = np.repeat(samples[:, None], 2, axis=1)
        bed, loops = loop_bed(stereo, 7200, 1000)
        self.assertEqual(bed.shape, (7200, 2))
        self.assertGreater(loops, 0)
        self.assertLess(np.max(np.abs(np.diff(bed[:, 0]))), 0.05)

    def test_explicit_off_does_not_read_pool_and_clears_old_credit(self):
        voice = np.ones(1000, dtype="float32") * 0.1
        with patch("music_bed.select_track") as select:
            mixed, metrics, track = mix_audio(
                voice, np.ones(1000), 1000, {"mode": "off"}, {}, "title"
            )
            select.assert_not_called()
        np.testing.assert_array_equal(mixed[:, 0], voice)
        self.assertEqual(metrics["music_mode"], "off")
        with tempfile.TemporaryDirectory() as folder:
            write_attribution(folder, None)
            self.assertIn(
                "未使用", (Path(folder) / "音乐署名.txt").read_text(encoding="utf-8")
            )

    def test_real_pool_is_decodable_quiet_and_stereo_with_complete_credit(self):
        sample_rate = 24000
        voice = 0.2 * np.sin(np.arange(sample_rate * 3) * 2 * np.pi * 160 / sample_rate)
        mixed, metrics, track = mix_audio(
            voice,
            np.ones(len(voice)),
            sample_rate,
            {"track_id": "voice-over-under", "relative_db": -20, "duck_db": 4},
            {},
            "integration",
        )
        self.assertEqual(mixed.shape, (len(voice), 2))
        self.assertTrue(np.isfinite(mixed).all())
        self.assertEqual(metrics["relative_db"], -20)
        self.assertEqual(metrics["duck_db"], 4)
        self.assertLessEqual(np.max(np.abs(mixed)), 0.94)
        self.assertLess(metrics["music_rms"], metrics["voice_rms"] * 0.1)
        self.assertEqual(track["license"], "CC BY 4.0")
        with tempfile.TemporaryDirectory() as folder:
            write_attribution(folder, track)
            text = (Path(folder) / "音乐署名.txt").read_text(encoding="utf-8")
            for required in (
                track["title"],
                track["artist"],
                track["source_url"],
                track["license_url"],
                "改动",
            ):
                self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
