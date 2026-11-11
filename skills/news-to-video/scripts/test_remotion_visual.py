"""Regression checks for scene-owned flow content and continuous frame allocation."""

import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr
import io
from types import SimpleNamespace
from unittest.mock import patch

import remotion_visual as editorial
import render


class EditorialContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.runtime = {}

    def test_missing_flow_nodes_stops_instead_of_rendering_demo(self):
        project = {"scenes": [{"editorial_kind": "flow"}]}
        with self.assertRaisesRegex(ValueError, "editorial_nodes"):
            editorial.preflight(project, self.base, self.runtime)

    def test_valid_and_malformed_scene_owned_nodes(self):
        nodes = [{"title": "核对依赖"}, {"title": "隔离签名回归"}]
        project = {"scenes": [{"editorial_kind": "flow", "editorial_nodes": nodes}]}
        editorial.preflight(project, self.base, self.runtime)
        project["scenes"][0]["editorial_nodes"][1]["title"] = " "
        with self.assertRaisesRegex(ValueError, "title"):
            editorial.preflight(project, self.base, self.runtime)

    def test_global_boundaries_keep_short_scenes_and_captions_continuous(self):
        # Independent rounding yields 3 frames here, while the actual program is 4.
        boundaries = [0, 0.06, 0.12, 0.18]
        project = {"scenes": [{"editorial_kind": "hero"} for _ in range(3)]}
        cues = [
            {
                "scene": index,
                "text": str(index),
                "start": boundaries[index],
                "end": boundaries[index + 1],
            }
            for index in range(3)
        ]
        audio = self.base / "audio.wav"
        font = self.base / "font.ttf"
        audio.write_bytes(b"test audio copied without decoding")
        font.write_bytes(b"test font copied without decoding")
        payload = editorial.stage(
            project, cues, 0.18, self.base, self.base / "stage", font
        )
        self.assertEqual(
            sum(scene["duration"] for scene in payload["scenes"]), round(0.18 * 24)
        )
        for scene in payload["scenes"]:
            self.assertEqual(scene["captions"][0]["start"], 0)
            self.assertEqual(scene["captions"][-1]["end"], scene["duration"])

    def test_flow_data_and_diagram_fit_survive_staging(self):
        nodes = [{"title": "SDK"}, {"title": "签名"}, {"title": "激活后核验"}]
        project = {"scenes": [{"editorial_kind": "flow", "editorial_nodes": nodes}]}
        cues = [{"scene": 0, "text": "待执行检查", "start": 0, "end": 1}]
        audio = self.base / "voice.wav"
        font = self.base / "font.ttf"
        audio.write_bytes(b"audio")
        font.write_bytes(b"font")
        folder = self.base / "stage"
        editorial.stage(project, cues, 1, self.base, folder, font)
        scene = json.loads((folder / "src/data.json").read_text(encoding="utf-8"))[
            "scenes"
        ][0]
        self.assertEqual(scene["nodes"], nodes)
        self.assertEqual(scene["image_fit"], "contain")

    def test_default_cli_has_only_editorial_and_rejects_retired_choices(self):
        parser = render.argument_parser()
        args = parser.parse_args(["project.json", "--output", "delivery"])
        self.assertEqual(args.visual_engine, "remotion_editorial")
        for engine in ("pillow", "hyperframes"):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(
                    ["project.json", "--output", "delivery", "--visual-engine", engine]
                )

    def test_old_layout_stops_before_voice_or_renderer_runtime(self):
        path = self.base / "project.json"
        path.write_text(
            json.dumps(
                {
                    "title": "旧布局",
                    "layout": "standard",
                    "scenes": [{"segments": [{"text": "检查"}]}],
                }
            ),
            encoding="utf-8",
        )
        args = SimpleNamespace(
            project=str(path),
            output=str(self.base / "out"),
            runtime=None,
            visual_engine=render.ENGINE,
        )
        with patch.object(render, "make_voice") as voice, patch.object(
            editorial, "preflight"
        ) as runtime:
            with self.assertRaisesRegex(ValueError, "unsupported layout"):
                render.run(args)
            voice.assert_not_called()
            runtime.assert_not_called()

    def test_default_dimensions_and_caption_policy_are_validated(self):
        project = {"title": "测试", "scenes": [{"segments": [{"text": "检查"}]}]}
        render.validate(project)
        project["width"] = 1080
        with self.assertRaisesRegex(ValueError, "dimensions"):
            render.validate(project)
        project.pop("width")
        project["editorial"] = {"captions": "unknown"}
        with self.assertRaisesRegex(ValueError, "captions"):
            render.validate(project)

    def test_picture_cache_ignores_music_but_tracks_assets(self):
        folder = self.base / "staged"
        folder.mkdir()
        image = folder / "image.png"
        audio = folder / "mix.wav"
        image.write_bytes(b"picture-one")
        audio.write_bytes(b"music-one")
        payload = {"scenes": [{"kind": "hero", "duration": 24}]}
        first = editorial.render_key(folder, payload)
        audio.write_bytes(b"music-two")
        self.assertEqual(first, editorial.render_key(folder, payload))
        image.write_bytes(b"picture-two")
        self.assertNotEqual(first, editorial.render_key(folder, payload))


if __name__ == "__main__":
    unittest.main()
