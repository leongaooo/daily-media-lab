"""Protect cue bindings, persistent source staging and v1/v2 behavior boundaries."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

import remotion_visual
from object_contract import measured_stage
from score_visuals import assess as assess_selection
from visual_contract import assess


class ObjectStageTests(unittest.TestCase):
    def setUp(self):
        self.project = json.loads(
            (Path(__file__).parents[1] / "assets/object-stage-example.json").read_text(
                encoding="utf-8"
            )
        )
        self.scene = self.project["scenes"][0]

    def errors(self):
        return assess(self.project)["errors"]

    def test_example_validates_with_no_forced_background_or_photo(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(assess_selection(self.project)["errors"], [])

    def test_unknown_action_and_unbound_evidence_fail(self):
        action = self.scene["object_stage"]["actions"][0]
        action.update(type="spin_magic", evidence="")
        errors = self.errors()
        self.assertTrue(any("unsupported action" in error for error in errors))
        self.assertTrue(any("evidence" in error for error in errors))

    def test_invalid_references_geometry_and_fraction_fail(self):
        for fields, message in [
            ({"target": "unknown"}, "target"),
            ({"segment": 999}, "segment"),
            ({"at": 0.9, "until": 0.2}, "fractions"),
            ({"type": "move", "x": 9000, "y": 200}, "bounds"),
            ({"type": "transfer", "to": "missing"}, "destination"),
        ]:
            with self.subTest(fields=fields):
                original = copy.deepcopy(self.scene["object_stage"]["actions"][0])
                self.scene["object_stage"]["actions"][0].update(fields)
                self.assertTrue(any(message in error for error in self.errors()))
                self.scene["object_stage"]["actions"][0] = original

    def test_action_tracks_cannot_overlap(self):
        self.scene["object_stage"]["actions"].append(
            copy.deepcopy(self.scene["object_stage"]["actions"][0])
        )
        self.assertTrue(any("overlapping" in error for error in self.errors()))

    def test_enter_and_exit_share_visibility_track(self):
        actions = self.scene["object_stage"]["actions"]
        actions.append({**actions[0], "type": "exit"})
        self.assertTrue(any("overlapping" in error for error in self.errors()))

    def test_malformed_references_return_errors_and_empty_state_is_rejected(self):
        for field in ("type", "target"):
            with self.subTest(field=field):
                action = self.scene["object_stage"]["actions"][0]
                original = copy.deepcopy(action)
                action[field] = {"invalid": "reference"}
                self.assertTrue(self.errors())
                self.scene["object_stage"]["actions"][0] = original
        self.scene["object_stage"]["actions"][0] = dict(
            type="state", target="phone", segment=0, evidence="synthetic fixture"
        )
        self.assertTrue(any("state needs" in error for error in self.errors()))

    def test_move_checks_glyph_extent_at_destination(self):
        stage = self.scene["object_stage"]
        actor = stage["objects"][0]
        actor.update(kind="queue", scale=1.5)
        stage["actions"][0] = dict(
            type="move",
            target=actor["id"],
            segment=0,
            x=100,
            y=200,
            evidence="synthetic fixture",
        )
        self.assertTrue(any("exceeds stage width" in error for error in self.errors()))

    def test_shot_must_advance_an_executable_state(self):
        self.scene["object_stage"]["actions"] = [
            a for a in self.scene["object_stage"]["actions"] if a["segment"] < 2
        ]
        self.assertTrue(any("each shot" in error for error in self.errors()))

    def test_light_and_dark_text_colors_are_validated(self):
        self.project["scenes"][1]["object_stage"]["ink"] = "#F4F1E9"
        self.assertTrue(any("contrast" in error for error in self.errors()))

    def test_cue_rounding_and_zero_frame_interval(self):
        cues = [{"start": i * 1.03, "end": (i + 1) * 1.03} for i in range(4)]
        staged = measured_stage(self.scene, cues, 0, 24)
        self.assertTrue(
            all(a["end_frame"] > a["start_frame"] for a in staged["actions"])
        )
        self.assertEqual(
            self.scene["object_stage"]["actions"][0].get("start_frame"), None
        )
        with self.assertRaisesRegex(ValueError, "zero frames"):
            measured_stage(self.scene, [{"start": 0, "end": 0.001}] * 4, 0, 24)

    def test_custom_source_survives_restage_and_invalidates_picture_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "authored"
            source.mkdir()
            component = source / "Stage.tsx"
            component.write_text(
                "export default function Stage() {return null;}\n", encoding="utf-8"
            )
            font = base / "font.ttf"
            font.write_bytes(b"copy-only fixture")
            self.project["editorial"] = {"component_dir": "authored"}
            self.project["scenes"] = [self.scene]
            cues = [
                {"scene": 0, "text": "fixture", "start": i * 2, "end": (i + 1) * 2}
                for i in range(4)
            ]
            output = base / "staged"
            payload = remotion_visual.stage(self.project, cues, 8, base, output, font)
            first = remotion_visual.render_key(output, payload)
            generated = output / "src/custom/Stage.tsx"
            generated.write_text("edited generated output", encoding="utf-8")
            remotion_visual.stage(self.project, cues, 8, base, output, font)
            self.assertEqual(component.read_bytes(), generated.read_bytes())
            self.assertEqual(first, remotion_visual.render_key(output, payload))
            component.write_text(
                "export default function Stage() {return 'authored change';}\n",
                encoding="utf-8",
            )
            remotion_visual.stage(self.project, cues, 8, base, output, font)
            self.assertNotEqual(first, remotion_visual.render_key(output, payload))
            self.project.pop("editorial")
            remotion_visual.stage(self.project, cues, 8, base, output, font)
            self.assertFalse(generated.exists())

    def test_v1_cannot_silently_consume_the_new_grammar(self):
        self.project["visual_contract_version"] = 1
        self.assertTrue(
            any(
                "requires visual_contract_version 2" in error for error in self.errors()
            )
        )

    def test_missing_version_cannot_skip_object_stage_validation(self):
        self.project.pop("visual_contract_version")
        self.assertTrue(
            any(
                "requires visual_contract_version 2" in error for error in self.errors()
            )
        )

    def test_missing_custom_source_stops_preflight(self):
        self.project["editorial"] = {"component_dir": "missing"}
        with self.assertRaisesRegex(ValueError, "Stage.tsx"):
            remotion_visual.preflight(self.project, Path.cwd(), {})

    def test_generated_object_image_is_bound_to_the_renderer_consumed_slot(self):
        import generate_images
        from PIL import Image

        self.scene["image_generation"] = dict(
            role="subject",
            object_id="phone",
            prompt="original generic phone object",
        )
        jobs = generate_images.jobs_for(
            self.project, dict(base_url="https://example.test/v1", api_mode="images")
        )
        self.assertEqual(jobs[0]["object_id"], "phone")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            jobs[0]["filename"] = "object.png"
            Image.new("RGB", (16, 16)).save(base / "object.png")
            resolved = generate_images.apply_assets(self.project, base, jobs, base)
            self.assertEqual(assess(resolved, base)["errors"], [])
            actor = resolved["scenes"][0]["object_stage"]["objects"][0]
            self.assertEqual(Path(actor["asset"]), base / "object.png")
            self.assertNotIn("subject_asset", resolved["scenes"][0])

    def test_selection_v2_does_not_force_a_photo_or_picture_tie_break(self):
        spec = self.scene["visual_selection"]
        spec["candidates"][1]["uses_image"] = False
        self.assertEqual(assess_selection(self.project)["errors"], [])


if __name__ == "__main__":
    unittest.main()
