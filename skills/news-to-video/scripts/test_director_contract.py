"""Offline tests for boundaries that must hold before paid generation or TTS."""

import copy
import unittest

from director_contract import assess, narration_identity
from remotion_visual import _story_shots


def project():
    return {
        "director_contract_version": 1,
        "scenes": [
            {
                "visual_goal": "理解食品追溯链路",
                "story_world": {
                    "id": "food",
                    "setting": "同一批产品从生产到门店",
                    "continuity_notes": "相同产品外观与流向",
                    "facts_boundary": "原创示意，不证明真实产线",
                },
                "segments": [{"text": "字幕", "spoken": "原配音"}],
            }
        ],
    }


class DirectorTests(unittest.TestCase):
    def test_generic_topic_and_legacy_boundary(self):
        self.assertEqual(assess(project())["errors"], [])
        self.assertEqual(assess({})["status"], "legacy-not-assessed")

    def test_missing_world_is_rejected(self):
        value = project()
        value["scenes"][0].pop("story_world")
        self.assertTrue(assess(value)["errors"])

    def test_same_world_cannot_change_identity(self):
        value = project()
        value["scenes"].append(copy.deepcopy(value["scenes"][0]))
        value["scenes"][1]["story_world"]["setting"] = "无关场景"
        self.assertTrue(assess(value)["errors"])

    def test_visual_edits_preserve_narration_identity(self):
        value = project()
        changed = copy.deepcopy(value)
        changed["scenes"][0]["image"] = "new.png"
        self.assertEqual(narration_identity(value), narration_identity(changed))
        changed["scenes"][0]["segments"][0]["spoken"] = "改过的配音"
        self.assertNotEqual(narration_identity(value), narration_identity(changed))

    def test_extra_modes_and_voice_tempo_are_rejected(self):
        value = project()
        value["production_mode"] = "premium"
        self.assertTrue(assess(value)["errors"])
        value.pop("production_mode")
        value["voice"] = {"speed": 1.3}
        self.assertTrue(assess(value)["errors"])

    def test_shot_times_follow_measured_caption_boundaries(self):
        scene = {
            "shots": [
                {
                    "title": "结果",
                    "segment_start": 1,
                    "segment_end": 1,
                }
            ]
        }
        cues = [{"start": 5, "end": 7}, {"start": 7, "end": 12.5}]
        shots = _story_shots(scene, None, None, 0, cues, 120, 24)
        self.assertEqual((shots[0]["start"], shots[0]["end"]), (2, 7.5))
        scene["shots"][0]["segment_end"] = 2
        with self.assertRaises(ValueError):
            _story_shots(scene, None, None, 0, cues, 120, 24)


if __name__ == "__main__":
    unittest.main()
