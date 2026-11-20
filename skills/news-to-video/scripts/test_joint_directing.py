"""无 GPU 回归：共享事件的真实合成载荷、摄影依赖与同一任务前后态。"""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from frozen_audio import file_hash
from joint_directing import (
    compile_directing,
    frame_state,
    load_directing,
    stage_directing,
    validate_plan,
)
from narrative_media import digest, seal, source_identity
import remotion_visual


class JointDirectingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "scene.blend").write_bytes(b"synthetic scene and camera")
        self.plan = {
            "schema_version": 1,
            "fps": 24,
            "width": 1920,
            "height": 1080,
            "projection": "projection.json",
            "camera_events": ["approach"],
            "events": {
                key: {"start_frame": start, "end_frame": end}
                for key, start, end in (
                    ("approach", 0, 2),
                    ("panel", 0, 2),
                    ("prediction", 2, 4),
                    ("reschedule", 4, 7),
                    ("result", 7, 9),
                    ("policy", 9, 10),
                    ("project", 10, 11),
                    ("green", 11, 12),
                )
            },
            "overlays": [
                {
                    "overlay_id": "flex",
                    "kind": "cavern-flex-v3",
                    "start_frame": 0,
                    "end_frame": 12,
                    "panel": [900, 180, 910, 640],
                    "title": "柔性算力",
                    "identity": "机制示意 · 非实测",
                    "event_names": {
                        key: key
                        for key in (
                            "panel",
                            "prediction",
                            "reschedule",
                            "result",
                            "policy",
                        )
                    },
                    "task": {
                        "id": "task-A",
                        "label": "可延后任务 A",
                        "from": 0.1,
                        "to": 0.6,
                        "width": 0.22,
                    },
                    "caveats": [
                        {"text": "不证明项目已通电", "event": "project"},
                        {"text": "不承诺全天候100%绿电", "event": "green"},
                    ],
                }
            ],
        }
        camera_events = digest({"approach": self.plan["events"]["approach"]})
        self.shot = {
            "shot_id": "s01",
            "story_world": "synthetic",
            "start_frame": 0,
            "end_frame": 12,
            "source": {
                "path": "scene.blend",
                "sha256": file_hash(self.base / "scene.blend"),
            },
            "camera_sha256": "c" * 64,
            "camera_events_sha256": camera_events,
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
                "label": "测试示意",
                "evidence_ids": ["test"],
                "prohibited_implications": [],
            },
            "receipt": "receipt.json",
        }
        self.manifest = {"schema_version": 1, "fps": 24, "shots": [self.shot]}
        self.projection = {
            "schema_version": 1,
            "fps": 24,
            "width": 1920,
            "height": 1080,
            "shots": [
                {
                    "shot_id": "s01",
                    "source_sha256": self.shot["source"]["sha256"],
                    "camera_sha256": self.shot["camera_sha256"],
                    "camera_events_sha256": camera_events,
                    "source_first_frame": 1,
                    "start_frame": 0,
                    "end_frame": 12,
                    "dependencies_sha256": digest([]),
                    "frames": [
                        {"frame": frame, "x": 720 + frame, "y": 440, "visible": True}
                        for frame in range(12)
                    ],
                }
            ],
        }
        self.project = {
            "narrative_version": 1,
            "narrative_manifest": "shots.json",
            "narrative_directing": "directing.json",
            "scenes": [{"segments": [{"text": "测试"}]}],
        }
        self.save()

    def save(self):
        for name, value in (
            ("directing", self.plan),
            ("projection", self.projection),
            ("shots", self.manifest),
        ):
            (self.base / f"{name}.json").write_text(
                json.dumps(value, ensure_ascii=False), encoding="utf-8"
            )

    def test_event_changes_the_consumed_frame_state_and_task_retains_identity(self):
        before = compile_directing(self.plan, self.projection, 12)
        self.plan["events"]["reschedule"]["start_frame"] = 5
        after = compile_directing(self.plan, self.projection, 12)
        old = before["frames"][5]["overlays"][0]
        new = after["frames"][5]["overlays"][0]
        self.assertNotEqual(old["task_x"], new["task_x"])
        self.assertEqual(old["task_id"], new["task_id"])
        self.assertEqual(
            frame_state(self.plan, 7)[0]["task_x"],
            frame_state(self.plan, 8)[0]["task_x"],
        )
        self.assertTrue(frame_state(self.plan, 7)[0]["result_visible"])
        self.assertEqual(self.plan["overlays"][0]["task"]["width"], 0.22)

    def test_policy_caveats_follow_their_own_events(self):
        self.assertEqual(frame_state(self.plan, 9)[0]["caveat_progress"], [0, 0])
        self.assertEqual(frame_state(self.plan, 10)[0]["caveat_progress"], [1, 0])
        self.assertEqual(frame_state(self.plan, 11)[0]["caveat_progress"], [1, 1])

    def test_camera_fingerprint_and_actual_source_change_reject_stale_projection(self):
        load_directing(self.project, self.base)
        self.projection["shots"][0]["camera_sha256"] = "a" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "camera fingerprint"):
            load_directing(self.project, self.base)
        self.projection["shots"][0]["camera_sha256"] = self.shot["camera_sha256"]
        self.save()
        (self.base / "scene.blend").write_bytes(b"changed camera")
        with self.assertRaisesRegex(ValueError, "source checksum"):
            load_directing(self.project, self.base)

    def test_approach_timing_invalidates_old_camera_but_board_timing_does_not(self):
        self.plan["events"]["panel"]["start_frame"] = 1
        self.save()
        load_directing(self.project, self.base)
        self.plan["events"]["approach"]["end_frame"] = 3
        self.save()
        with self.assertRaisesRegex(ValueError, "camera events are stale"):
            load_directing(self.project, self.base)

    def test_missing_or_nonfinite_projection_and_caption_overlap_fail(self):
        self.projection["shots"][0]["frames"].pop()
        self.save()
        with self.assertRaisesRegex(ValueError, "missing narrative frames"):
            load_directing(self.project, self.base)
        self.plan["overlays"][0]["panel"][1] = 300
        with self.assertRaisesRegex(ValueError, "caption protection"):
            validate_plan(self.plan, 12)

    def test_source_frame_offset_and_dependency_change_reject_old_anchors(self):
        self.projection["shots"][0]["source_first_frame"] = 2
        self.save()
        with self.assertRaisesRegex(ValueError, "frame mapping"):
            load_directing(self.project, self.base)
        self.projection["shots"][0]["source_first_frame"] = 1
        dependency = self.base / "camera-path.json"
        dependency.write_text("camera path revision 2")
        self.shot["dependencies"] = [
            {"path": dependency.name, "sha256": file_hash(dependency)}
        ]
        self.save()
        with self.assertRaisesRegex(ValueError, "dependencies are stale"):
            load_directing(self.project, self.base)

    def test_multiline_idc_copy_cannot_overrun_fixed_card_rows(self):
        self.plan["overlays"] = [
            {
                "overlay_id": "idc",
                "kind": "idc-status-v3",
                "start_frame": 0,
                "end_frame": 12,
                "panel": [900, 180, 910, 640],
                "title": "供应状态",
                "identity": "来源披露 · 非现场",
                "event_names": {"panel": "panel"},
                "cards": [
                    {
                        "title": "供应",
                        "detail": "第一行\n第二行",
                        "status": "future",
                        "event": "prediction",
                    }
                ],
            }
        ]
        with self.assertRaisesRegex(ValueError, "IDC card detail"):
            validate_plan(self.plan, 12)

    def test_mechanism_excerpt_omits_policy_without_inventing_a_closure(self):
        overlay = self.plan["overlays"][0]
        del overlay["event_names"]["policy"]
        del overlay["caveats"]
        validate_plan(self.plan, 12)
        state = frame_state(self.plan, 11)[0]
        self.assertEqual(state["policy_progress"], 0)
        self.assertEqual(state["caveat_progress"], [])

    def test_idc_board_preserves_pending_and_future_statuses(self):
        self.plan["overlays"] = [
            {
                "overlay_id": "idc",
                "kind": "idc-status-v3",
                "start_frame": 0,
                "end_frame": 12,
                "panel": [900, 180, 910, 640],
                "title": "供应状态",
                "identity": "来源披露 · 非现场",
                "event_names": {"panel": "panel"},
                "cards": [
                    {
                        "title": "2027年下半年以后",
                        "detail": "未来供应安排",
                        "status": "future",
                        "event": "prediction",
                    },
                    {
                        "title": "负载、网络与存储",
                        "detail": "待核验",
                        "status": "pending",
                        "event": "reschedule",
                    },
                ],
            }
        ]
        validate_plan(self.plan, 12)
        self.assertEqual(frame_state(self.plan, 4)[0]["card_progress"], [1, 0])
        self.plan["overlays"][0]["cards"][0]["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "evidence status"):
            validate_plan(self.plan, 12)

    def test_reference_stages_in_deep_project_path_with_its_complete_identity(self):
        reference_path = self.base / "reference.png"
        Image.new("RGB", (80, 40), "#293541").save(reference_path)
        reference_hash = file_hash(reference_path)
        self.plan["overlays"] = [
            {
                "overlay_id": "cluster-product-levels",
                "kind": "idc-status-v3",
                "start_frame": 0,
                "end_frame": 12,
                "panel": [900, 180, 910, 640],
                "title": "产品层级",
                "identity": "产品参考 · 非现场",
                "event_names": {"panel": "panel"},
                "cards": [
                    {
                        "title": "通用机柜",
                        "detail": "实际产品型号待核",
                        "status": "reference",
                        "event": "prediction",
                    }
                ],
                "reference": {
                    "path": reference_path.name,
                    "sha256": reference_hash,
                    "label": "原创层级示意",
                },
            }
        ]
        self.save()
        # 复现实际深层工作区；旧的 overlay 名称加完整哈希会越过 260 字符。
        padding = 170 - len(str(self.base / "project-" / "public"))
        public = self.base / ("project-" + "x" * padding) / "public"
        payload = stage_directing(self.project, self.base, public, 12)
        reference = payload["overlays"][0]["reference"]
        staged = public / reference["asset"]
        self.assertEqual(reference["sha256"], reference_hash)
        self.assertEqual(file_hash(staged), reference_hash)
        self.assertEqual(reference_path.read_bytes(), staged.read_bytes())

    def test_staging_consumes_directing_and_board_edit_changes_only_composition_key(
        self,
    ):
        frames = self.base / "frames"
        frames.mkdir()
        for frame in range(1, 13):
            Image.new("RGB", (1920, 1080), "#293541").save(frames / f"{frame:06d}.png")
        seal(self.base / "shots.json")
        font = self.base / "font.ttf"
        font.write_bytes(b"staging only fixture")
        folder = self.base / "stage"
        cues = [
            {
                "scene": 0,
                "text": "测试",
                "start": 0,
                "end": 0.5,
                "start_frame": 0,
                "end_frame": 12,
            }
        ]
        payload = remotion_visual.stage(
            self.project, cues, 0.5, self.base, folder, font
        )
        source_before = source_identity(self.shot, self.base)
        key_before = remotion_visual.render_key(folder, payload)
        self.assertEqual(
            payload["narrative_directing"]["frames"][5]["anchor"]["x"], 725
        )
        self.plan["overlays"][0]["title"] = "同一任务改排"
        self.save()
        changed = remotion_visual.stage(
            self.project, cues, 0.5, self.base, folder, font
        )
        self.assertNotEqual(key_before, remotion_visual.render_key(folder, changed))
        self.assertEqual(source_before, source_identity(self.shot, self.base))
        self.assertEqual(payload["narrative_shots"], changed["narrative_shots"])


if __name__ == "__main__":
    unittest.main()
