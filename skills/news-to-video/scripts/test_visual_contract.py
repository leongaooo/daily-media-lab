"""Regression coverage for executable plans and measured shot boundary allocation."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from visual_contract import assess
import remotion_visual


class VisualContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        for index in range(4):
            Image.new("RGB", (10, 10), (index * 50, 0, 0)).save(
                self.base / f"{index}.png"
            )
        self.project = {
            "visual_contract_version": 1,
            "scenes": [
                {
                    "composition": "timeline",
                    "story_world": {"id": "migration"},
                    "segments": [{"text": "准备"}, {"text": "变化"}],
                    "editorial_nodes": [{"title": "准备"}, {"title": "变化"}],
                    "subject_asset": "2.png",
                    "supporting_asset": "3.png",
                    "shots": [
                        {
                            "title": "环境",
                            "segment_start": 0,
                            "background_asset": "0.png",
                        },
                        {
                            "title": "变化",
                            "segment_start": 1,
                            "background_asset": "1.png",
                        },
                    ],
                }
            ],
        }

    def test_valid_plan_and_legacy_status(self):
        self.assertEqual(assess(self.project, self.base)["errors"], [])
        self.assertEqual(assess({"scenes": []})["status"], "legacy-not-assessed")

    def test_duplicate_composition_and_renamed_background_fail(self):
        self.project["scenes"].append(copy.deepcopy(self.project["scenes"][0]))
        self.assertTrue(
            any("compositions" in error for error in assess(self.project)["errors"])
        )
        self.project["scenes"].pop()
        (self.base / "renamed.png").write_bytes((self.base / "0.png").read_bytes())
        self.project["scenes"][0]["shots"][1]["background_asset"] = "renamed.png"
        self.assertTrue(
            any(
                "background" in error
                for error in assess(self.project, self.base)["errors"]
            )
        )

    def test_missing_asset_low_contrast_and_caption_gap_fail(self):
        scene = self.project["scenes"][0]
        scene["subject_asset"] = "missing.png"
        scene["palette"] = {"muted": "#161A22"}
        scene["shots"][1]["segment_start"] = 2
        errors = assess(self.project, self.base)["errors"]
        for expected in ("missing subject_asset", "contrast", "partition"):
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_all_grammars_stage_caption_bound_shots_and_assets(self):
        font = self.base / "font.ttf"
        font.write_bytes(b"font fixture copied without decoding")
        cues = [
            {"scene": 0, "text": "准备", "start": 0, "end": 0.51},
            {"scene": 0, "text": "变化", "start": 0.51, "end": 1.23},
        ]
        for grammar in (
            "hero_scene",
            "timeline",
            "system_map",
            "evidence_board",
            "workbench",
            "comparison",
            "story",
        ):
            self.project["scenes"][0]["composition"] = grammar
            payload = remotion_visual.stage(
                self.project, cues, 1.23, self.base, self.base / grammar, font
            )
            scene = payload["scenes"][0]
            self.assertEqual(scene["composition"], grammar)
            self.assertEqual(round(scene["shots"][0]["end"] * 24), 12)
            self.assertEqual(round(scene["shots"][1]["start"] * 24), 12)
            self.assertEqual(round(scene["shots"][-1]["end"] * 24), scene["duration"])
            self.assertTrue(scene["subject_asset"].startswith("assets/"))
            self.assertNotEqual(
                scene["shots"][0]["background_asset"],
                scene["shots"][1]["background_asset"],
            )
            self.assertIn("primary", scene["palette"])

    def test_shot_generation_uses_shared_world_and_distinct_asset_slots(self):
        import generate_images

        scene = self.project["scenes"][0]
        scene["negative_prompt"] = "no logos"
        for index, shot in enumerate(scene["shots"]):
            shot["image_generation"] = dict(
                role="background", prompt=f"control room view {index}"
            )
        jobs = generate_images.jobs_for(
            self.project, dict(base_url="https://example.test/v1", api_mode="images")
        )
        self.assertEqual([job["shot"] for job in jobs], [0, 1])
        self.assertEqual(len({job["asset_id"] for job in jobs}), 2)
        for job in jobs:
            self.assertIn("migration", job["payload"]["prompt"])
            self.assertIn("no logos", job["payload"]["prompt"])
            job["filename"] = f"generated-{job['shot']}.png"
            Image.new("RGB", (10, 10)).save(self.base / job["filename"])
        resolved = generate_images.apply_assets(
            self.project, self.base, jobs, self.base
        )
        shots = resolved["scenes"][0]["shots"]
        self.assertNotEqual(shots[0]["background_asset"], shots[1]["background_asset"])
        self.assertIn("resolved_sha256", shots[0]["image_generation"])

    def test_subframe_shot_is_rejected(self):
        font = self.base / "font.ttf"
        font.write_bytes(b"fixture")
        cues = [
            {"scene": 0, "text": "准备", "start": 0, "end": 0.001},
            {"scene": 0, "text": "变化", "start": 0.001, "end": 1},
        ]
        with self.assertRaisesRegex(ValueError, "frame boundaries"):
            remotion_visual.stage(
                self.project, cues, 1, self.base, self.base / "out", font
            )


if __name__ == "__main__":
    unittest.main()
