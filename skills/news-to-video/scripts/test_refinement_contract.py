"""Regression coverage for lost editorial content and bounded render execution."""

import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import remotion_visual as editorial
import render


class RefinementContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.font = self.base / "font.ttf"
        self.font.write_bytes(b"font fixture; no font renderer invoked")

    def stage(self, scene, render_options=None):
        project = {"scenes": [scene]}
        if render_options is not None:
            project["editorial"] = {"render": render_options}
        return editorial.stage(
            project,
            [{"scene": 0, "text": "原口播", "start": 0, "end": 1}],
            1,
            self.base,
            self.base / "stage",
            self.font,
        )

    def test_alias_source_is_resolved_before_top_level_chart_validation(self):
        project = {
            "title": "同口径统计",
            "scenes": [
                {
                    "composition": "chart",
                    "source": "公开报告，全国口径",
                    "data": [{"label": "能力", "value": 1}],
                    "segments": [{"text": "报告披露一个数字"}],
                }
            ],
        }
        original = copy.deepcopy(project)
        render.validate(project)
        self.assertEqual(project, original)

    def test_legacy_aliases_reach_the_actual_staged_payload_without_mutating_input(
        self,
    ):
        scene = {
            "composition": "comparison",
            "nodes": [{"title": "总体技术要求"}, {"title": "测试方法"}],
            "source": "公告附件",
            "summary": "两项互补标准",
            "comparison_labels": ["规划依据", "测试依据"],
        }
        original = copy.deepcopy(scene)
        payload = self.stage(scene)["scenes"][0]
        self.assertEqual(payload["nodes"], scene["nodes"])
        self.assertEqual(payload["source"], "公告附件")
        self.assertEqual(payload["summary"], "两项互补标准")
        self.assertEqual(payload["comparison_labels"], ["规划依据", "测试依据"])
        self.assertEqual(scene, original)
        persisted = json.loads(
            (self.base / "stage/src/data.json").read_text(encoding="utf-8")
        )
        self.assertEqual(persisted["scenes"][0], payload)

    def test_explicit_source_and_summary_win_with_an_auditable_note(self):
        payload = self.stage(
            {
                "source": "简略归属",
                "data_source": "完整来源与口径",
                "summary": "旧摘要",
                "editorial_summary": "已确认摘要",
            }
        )["scenes"][0]
        self.assertEqual(payload["source"], "完整来源与口径")
        self.assertEqual(payload["summary"], "已确认摘要")
        self.assertEqual(len(payload["field_mapping_notes"]), 2)

    def test_conflicting_nodes_stop_instead_of_picking_different_facts(self):
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.stage(
                {"nodes": [{"title": "甲"}], "editorial_nodes": [{"title": "乙"}]}
            )

    def test_empty_or_truncated_visual_content_is_rejected_before_runtime(self):
        for kind, nodes in [
            ("comparison", []),
            ("comparison", [{"title": "只有一项"}]),
            ("comparison", [{"title": str(index)} for index in range(3)]),
            ("evidence_board", []),
        ]:
            with self.subTest(kind=kind, count=len(nodes)):
                with self.assertRaisesRegex(ValueError, "requires"):
                    editorial.preflight(
                        {"scenes": [{"composition": kind, "nodes": nodes}]},
                        self.base,
                        {},
                    )

    def test_empty_shot_override_cannot_hide_nonempty_scene_content(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            self.stage(
                {
                    "composition": "comparison",
                    "editorial_nodes": [{"title": "甲"}, {"title": "乙"}],
                    "shots": [
                        {"title": "错误空覆盖", "nodes": [], "start": 0, "end": 1}
                    ],
                }
            )

    def test_authored_shot_nodes_are_supported(self):
        nodes = [{"title": "电力侧"}, {"title": "网络侧"}]
        payload = self.stage(
            {
                "composition": "evidence_board",
                "shots": [{"title": "两项核对", "nodes": nodes, "start": 0, "end": 1}],
            }
        )["scenes"][0]
        self.assertEqual(payload["shots"][0]["nodes"], nodes)

    def test_comparison_defaults_are_neutral_and_authored_labels_must_be_complete(self):
        nodes = [{"title": "甲"}, {"title": "乙"}]
        payload = self.stage({"composition": "comparison", "nodes": nodes})["scenes"][0]
        self.assertEqual(payload["comparison_labels"], ["对照 A", "对照 B"])
        for labels in (["只有一项"], ["甲", ""], "错误类型"):
            with self.subTest(labels=labels):
                with self.assertRaisesRegex(ValueError, "comparison_labels"):
                    self.stage(
                        {
                            "composition": "comparison",
                            "nodes": nodes,
                            "comparison_labels": labels,
                        }
                    )

    def test_resource_options_are_strict_and_reach_the_render_command(self):
        options = {
            "concurrency": 1,
            "parallel_encoding": False,
            "ffmpeg_threads": 2,
            "node_heap_mb": 384,
        }
        folder = self.base / "stage"
        payload = self.stage({}, options)
        result = SimpleNamespace(returncode=0)
        original_options = os.environ.get("NODE_OPTIONS")
        with patch.object(editorial.subprocess, "run", return_value=result) as process:
            editorial.render(
                self.base,
                self.base / "cli.js",
                folder,
                self.base / "silent.mp4",
                payload,
                self.base / "render.log",
            )
        arguments = process.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--concurrency") + 1], "1")
        self.assertIn("--disallow-parallel-encoding", arguments)
        self.assertIn(
            "--max-old-space-size=384", process.call_args.kwargs["env"]["NODE_OPTIONS"]
        )
        self.assertIn(
            '"-threads", "2"',
            (folder / "remotion.config.ts").read_text(encoding="utf-8"),
        )
        self.assertEqual(os.environ.get("NODE_OPTIONS"), original_options)

    def test_invalid_resource_settings_stop_before_staging(self):
        for options in (
            {"concurrency": True},
            {"concurrency": 0},
            {"parallel_encoding": "false"},
            {"ffmpeg_threads": 0},
            {"node_heap_mb": 64},
            {"unimplemented": 1},
        ):
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, "editorial.render"):
                    self.stage({}, options)

    def test_narrative_shots_do_not_inherit_legacy_node_requirements(self):
        project = {"narrative_version": 1, "scenes": [{"composition": "comparison"}]}
        self.assertIs(editorial.normalize_editorial(project), project)


if __name__ == "__main__":
    unittest.main()
