"""Regression tests for daily production preview receipts."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import render
from test_episode import package

import episode


class AnimaticContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.episode_id = "daily-fixture"
        self.preview = self.root / "preview.mp4"
        self.project = self.root / "preview-project.json"
        self.motion = self.root / "preview-motion.json"
        self.voice = self.root / "voice.wav"
        self.window = self.root / "voice-window.wav"
        self.consumer = self.root / "ObjectStage.tsx"
        self.baseline = self.root / "baseline.md"
        self.validation = self.root / "validation.json"
        self.playback = self.root / "playback.json"
        for path in (self.preview, self.project, self.motion, self.voice, self.window):
            path.write_bytes(path.name.encode("utf-8"))
        self.baseline.write_text("Synthetic accepted baseline", encoding="utf-8")
        episode.atomic_json(self.project, {"sources": [{"id": "fixture-e1"}]})
        self.consumer.write_text("export const consumed = true;", encoding="utf-8")
        self.motion.write_text(
            json.dumps(
                {
                    "visual_path": "object_stage",
                    "consumer": {
                        "kind": "object_stage",
                        "artifact": self.identity(self.consumer),
                    },
                    "status": "rendered",
                    "frame_count": 48,
                    "scenes": [
                        {
                            "scene": 0,
                            "actions": [
                                {
                                    "action_id": "scene-0-action-0",
                                    "start_frame": 10,
                                    "end_frame": 20,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        episode.atomic_json(
            self.validation,
            {
                "full_decode_passed": True,
                "remotion_editorial": {"captions_in_video": "bottom_rail"},
                "artifacts": {
                    "video.mp4": self.identity(self.preview),
                    "motion-report.json": self.identity(self.motion),
                    "voice.wav": self.identity(self.window),
                },
            },
        )
        episode.atomic_json(
            self.playback,
            {
                "media_sha256": self.identity(self.preview)["sha256"],
                "ended": True,
                "muted": False,
                "rate": 1,
                "decodedFrames": 48,
                "updates": 6,
                "events": [["playing", 0], ["pause", 2]],
            },
        )
        self.image = self.root / "frame.png"
        Image.new("RGB", (16, 16), "navy").save(self.image)

    def identity(self, path):
        return episode.file_identity(path)

    def receipt(self, observations=None):
        return {
            "schema_version": 1,
            "kind": "animatic_review",
            "episode_id": self.episode_id,
            "baseline_id": "synthetic-accepted-baseline",
            "baseline": self.identity(self.baseline),
            "scope": {
                "scenes": [0],
                "evidence_ids": ["fixture-e1"],
                "semantic_goal": "Fixture moves into a bay",
            },
            "validation": self.identity(self.validation),
            "playback": self.identity(self.playback),
            "visual_path": "object_stage",
            "preview": self.identity(self.preview),
            "project": self.identity(self.project),
            "motion_report": self.identity(self.motion),
            "voice_window": {
                "source": self.identity(self.voice),
                "window": self.identity(self.window),
                "start_sample": 0,
                "end_sample": 100,
            },
            "consumer": {
                "kind": "object_stage",
                "artifact": self.identity(self.consumer),
            },
            "checks": {key: True for key in episode.ANIMATIC_CHECKS},
            "limitations": ["No user approval or cross-device listening recorded"],
            "observations": observations
            or [
                {
                    "action_id": "scene-0-action-0",
                    "before_frame": 9,
                    "middle_frame": 15,
                    "after_frame": 20,
                    "observed": "Object enters and remains identifiable",
                    "frames": {
                        key: self.identity(self.image)
                        for key in ("before", "middle", "after")
                    },
                    "evidence": "frames 9, 15, 20",
                }
            ],
        }

    def write_receipt(self, value):
        path = self.root / "animatic-review.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def available(self, receipt_path):
        return [
            self.identity(path)
            for path in (
                receipt_path,
                self.preview,
                self.project,
                self.motion,
                self.voice,
                self.window,
                self.consumer,
                self.baseline,
                self.validation,
                self.playback,
            )
        ]

    def test_identity_receipt_with_media_boundary(self):
        path = self.write_receipt(self.receipt())
        available = self.available(path)
        # The private integration and public renderer smoke exercise actual media.
        with patch("episode._validate_preview_media") as media_check:
            checked = episode.validate_animatic_receipt(
                path, self.episode_id, inputs=available, outputs=available
            )
        media_check.assert_called_once()
        self.assertEqual(checked["baseline_id"], "synthetic-accepted-baseline")

    def test_stable_daily_receipt_requires_explicit_layer_gate(self):
        path = self.write_receipt(self.receipt())
        available = self.available(path)
        with patch("episode._validate_preview_media"):
            with self.assertRaisesRegex(ValueError, "requires a stability_gate"):
                episode.validate_animatic_receipt(
                    path,
                    self.episode_id,
                    inputs=available,
                    outputs=available,
                    require_stability=True,
                )

    def test_full_contract_rejects_non_media(self):
        path = self.write_receipt(self.receipt())
        with self.assertRaises(Exception) as error:
            episode.validate_animatic_receipt(path, self.episode_id)
        self.assertIn("Format not recognised", str(error.exception))

    def test_new_episode_refuses_storyboard_for_animatic(self):
        state_path = self.root / "episode.json"
        package_path = self.root / "package.json"
        episode.atomic_json(package_path, package())
        state = episode.create_episode(
            state_path,
            self.episode_id,
            "Synthetic video",
            [package_path],
            confirmed_script=self.project,
        )
        state = episode.record_stage(
            state_path,
            state["revision"],
            "editorial_locked",
            [self.project],
            ["Fixture"],
        )
        for name in ("audio_locked", "visual_ready"):
            state = episode.record_stage(
                state_path,
                state["revision"],
                name,
                [self.project],
                ["Fixture"],
            )
        with self.assertRaisesRegex(ValueError, "requires --review-receipt"):
            episode.record_stage(
                state_path,
                state["revision"],
                "animatic_reviewed",
                [self.image],
                ["Storyboard"],
            )

    def test_daily_render_requires_receipt_and_keeps_historical_entry(self):
        self.assertIsNone(
            render.validate_formal_acceptance({}, self.project, self.root)
        )
        daily = {"acceptance_contract": "daily-v1", "episode_id": self.episode_id}
        with self.assertRaisesRegex(ValueError, "requires baseline_id"):
            render.validate_formal_acceptance(daily, self.project, self.root)

    def test_missing_before_middle_after_is_rejected(self):
        path = self.write_receipt(
            self.receipt(
                [
                    {
                        "action_id": "scene-0-action-0",
                        "before_frame": 10,
                        "middle_frame": 15,
                        "after_frame": 20,
                        "observed": "incomplete before state",
                        "evidence": "fixture",
                    }
                ]
            )
        )
        available = self.available(path)
        with self.assertRaisesRegex(ValueError, "cover the action transition"):
            episode.validate_animatic_receipt(
                path, self.episode_id, inputs=available, outputs=available
            )

    def test_receipt_cannot_use_unregistered_preview(self):
        path = self.write_receipt(self.receipt())
        available = [self.identity(path), self.identity(self.project)]
        with self.assertRaisesRegex(ValueError, "actual stage output"):
            episode.validate_animatic_receipt(
                path, self.episode_id, inputs=available, outputs=available
            )


if __name__ == "__main__":
    unittest.main()
