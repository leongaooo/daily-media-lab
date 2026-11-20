"""无GPU行为回归：最终音频身份、半帧边界、母版错误与内容失效。"""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import soundfile as sf

from frozen_audio import file_hash, frame_at, load_final
from narrative_media import seal, read_json, validate_manifest, stage_manifest
import render
import remotion_visual


class FrozenAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.audio = self.base / "vocal.wav"
        sf.write(
            self.audio, np.sin(np.arange(24001) / 19) * 0.1, 24000, subtype="FLOAT"
        )
        self.cues = self.base / "cues.json"
        self.cues.write_text(
            json.dumps([{"scene": 0, "text": "样本", "start": 0, "end": 24001 / 24000}])
        )
        self.project = {
            "title": "冻结音频回归",
            "scenes": [{"segments": [{"text": "样本"}]}],
            "voice": {
                "mode": "external_final",
                "path": "vocal.wav",
                "sha256": file_hash(self.audio),
                "sample_rate": 24000,
                "samples": 24001,
                "channels": 1,
                "processing_identity": {"voice": "synthetic-test"},
                "cues": "cues.json",
            },
        }

    def test_tail_sample_is_preserved_and_last_caption_covers_ceiling_frame(self):
        before = self.audio.read_bytes()
        duration, voice, _, cues, rate, identity, _ = load_final(
            self.project, self.base
        )
        self.assertEqual(len(voice), 24001)
        self.assertEqual(rate, 24000)
        self.assertEqual(duration, 25 / 24)
        self.assertEqual(cues[-1]["end_frame"], 25)
        self.assertEqual(before, self.audio.read_bytes())
        self.assertFalse(identity["tts_invoked"])
        self.assertEqual(identity["voice_transforms"], [])

    def test_half_frames_round_up_and_zero_interval_is_rejected(self):
        self.assertEqual(frame_at(1 / 48), 1)
        self.assertEqual(frame_at(2.5), 60)
        self.project["scenes"][0]["segments"].append({"text": "尾句"})
        self.cues.write_text(
            json.dumps(
                [
                    {"scene": 0, "text": "样本", "start": 0, "end": 0.001},
                    {"scene": 0, "text": "尾句", "start": 0.001, "end": 24001 / 24000},
                ]
            )
        )
        with self.assertRaisesRegex(ValueError, "zero frames"):
            load_final(self.project, self.base)

    def test_identity_and_playback_mismatch_fail_without_fallback(self):
        wrong = deepcopy(self.project)
        wrong["voice"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "checksum"):
            load_final(wrong, self.base)
        wrong = deepcopy(self.project)
        wrong["voice"]["playback_rate"] = 1.15
        with self.assertRaisesRegex(ValueError, "1.0"):
            load_final(wrong, self.base)

    def test_executor_bypasses_tts_and_reassembly_and_copies_exact_master(self):
        output = self.base / "output"
        output.mkdir()
        with (
            patch("render.make_voice", side_effect=AssertionError("TTS invoked")),
            patch("render.timeline", side_effect=AssertionError("reassembly invoked")),
        ):
            render.prepare_narration(
                self.project, {}, output / ".cache", self.base, output, 24
            )
        self.assertEqual((output / "voice.wav").read_bytes(), self.audio.read_bytes())

    def test_render_accepts_final_audio_without_private_voice_configuration(self):
        with patch(
            "render.validate_voice", side_effect=AssertionError("TTS voice branch")
        ):
            render.validate(self.project)


class NarrativeMasterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "scene.blend").write_bytes(b"test scene identity")
        (self.base / "frames").mkdir()
        for index in (1, 2):
            Image.new("RGB", (1920, 1080), (index * 40, 70, 120)).save(
                self.base / f"frames/{index:06}.png"
            )
        self.shot = {
            "shot_id": "s01",
            "story_world": "test",
            "start_frame": 0,
            "end_frame": 2,
            "source": {
                "path": "scene.blend",
                "sha256": file_hash(self.base / "scene.blend"),
            },
            "dependencies": [],
            "render": {
                "blender_version": "4.4.3",
                "engine": "BLENDER_EEVEE_NEXT",
                "seed": 0,
                "samples": 8,
                "denoise": False,
                "width": 1920,
                "height": 1080,
                "fps": 24,
                "display_transform": "AgX",
                "look": "None",
                "exposure": 0,
                "gamma": 1,
            },
            "media": {
                "role": "master",
                "pattern": "frames/%06d.png",
                "source_first_frame": 1,
                "bit_depth": 8,
                "color_space": "display-srgb",
                "alpha": "opaque",
            },
            "handles": {"head": 0, "tail": 0},
            "facts": {
                "kind": "metaphor",
                "label": "概念演绎",
                "evidence_ids": ["e1"],
                "prohibited_implications": [],
            },
            "receipt": "receipt.json",
        }
        self.manifest = {"schema_version": 1, "fps": 24, "shots": [self.shot]}
        self.path = self.base / "shots.json"
        self.save()
        seal(self.path)

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_byte_preserving_staging_and_frame_mapping(self):
        # 真实深目录复制；旧目录再加入长shot_id会越过Windows传统路径限制。
        self.shot["shot_id"] = "manufacturing-category"
        self.save()
        padding = 170 - len(str(self.base / "project-" / "public"))
        public = self.base / ("project-" + "x" * padding) / "public"
        staged = stage_manifest(
            {"narrative_manifest": "shots.json"}, self.base, public, 2
        )
        self.assertEqual(staged[0]["start_frame"], 0)
        self.assertEqual(staged[0]["end_frame"], 2)
        self.assertEqual(staged[0]["shot_id"], "manufacturing-category")
        for index, frame in enumerate(staged[0]["frames"], start=1):
            self.assertEqual(
                (public / frame).read_bytes(),
                (self.base / f"frames/{index:06}.png").read_bytes(),
            )

    def test_fullframe_staging_uses_integer_cues_without_legacy_node_slots(self):
        font = self.base / "font.ttf"
        font.write_bytes(b"staging font fixture")
        project = {
            "narrative_version": 1,
            "narrative_manifest": "shots.json",
            "scenes": [{"visual_direction": "流程只是文字，不是旧flow节点契约"}],
        }
        cues = [
            {
                "scene": 0,
                "text": "样本",
                "start": 0,
                "end": 2 / 24,
                "start_frame": 0,
                "end_frame": 2,
            }
        ]
        payload = remotion_visual.stage(
            project, cues, 2 / 24, self.base, self.base / "stage", font
        )
        self.assertEqual(payload["scenes"][0]["kind"], "narrative")
        self.assertEqual(payload["narrative_cues"][0]["end_frame"], 2)
        self.assertEqual(len(payload["narrative_shots"][0]["frames"]), 2)

    def test_missing_or_changed_frame_cannot_be_delivered(self):
        target = self.base / "frames/000002.png"
        target.write_bytes(b"")
        with self.assertRaises(ValueError):
            validate_manifest(self.manifest, self.base, 2)
        Image.new("RGB", (1920, 1080), (255, 0, 0)).save(target)
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_manifest(self.manifest, self.base, 2)

    def test_source_render_settings_and_proxy_role_invalidate_delivery(self):
        self.shot["render"]["samples"] = 64
        with self.assertRaisesRegex(ValueError, "identity changed"):
            validate_manifest(self.manifest, self.base, 2)
        self.shot["media"]["role"] = "proxy"
        with self.assertRaisesRegex(ValueError, "proxy"):
            validate_manifest(self.manifest, self.base, 2)

    def test_composition_cache_uses_live_frame_bytes_and_ignores_old_sequence_versions(
        self,
    ):
        folder = self.base / "stage-cache"
        live = folder / "public/narrative/s01/current/000000.png"
        live.parent.mkdir(parents=True)
        live.write_bytes(b"current pixels")
        payload = {
            "narrative_shots": [{"frames": ["narrative/s01/current/000000.png"]}]
        }
        before = remotion_visual.render_key(folder, payload)
        stale = folder / "public/narrative/s01/previous/000000.png"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old version")
        self.assertEqual(before, remotion_visual.render_key(folder, payload))
        live.write_bytes(b"changed pixels")
        self.assertNotEqual(before, remotion_visual.render_key(folder, payload))

    def test_worker_implementation_change_invalidates_unchanged_frame_receipts(self):
        worker = self.base / "isolated-worker.py"
        worker.write_text("render_logic = 1")
        with patch("narrative_media.WORKER_PATH", worker):
            seal(self.path)
            validate_manifest(self.manifest, self.base, 2)
            worker.write_text("render_logic = 2")
            with self.assertRaisesRegex(ValueError, "identity changed"):
                validate_manifest(self.manifest, self.base, 2)
            # An explicit import seal is a new technical receipt, never silent cache reuse.
            seal(self.path)
            validate_manifest(self.manifest, self.base, 2)

    def test_gap_and_wrong_total_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "frame count"):
            validate_manifest(self.manifest, self.base, 3)
        self.shot["start_frame"] = 1
        with self.assertRaisesRegex(ValueError, "without gaps"):
            validate_manifest(self.manifest, self.base, 2)


if __name__ == "__main__":
    unittest.main()
