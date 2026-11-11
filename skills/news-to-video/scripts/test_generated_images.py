"""Offline regression: secrets, duplicate billing protection, layout and image decoding."""

import argparse
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import generate_images as g


def png():
    stream = io.BytesIO()
    Image.new("RGB", (120, 80), "#227766").save(stream, "PNG")
    return stream.getvalue()


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return json.dumps(
            {"data": [{"b64_json": base64.b64encode(png()).decode()}]}
        ).encode()


class GeneratedImageTests(unittest.TestCase):
    def fixture(self, path):
        p = dict(
            title="测试",
            scenes=[
                dict(
                    chapter="章节",
                    headline="测试",
                    mode="theme_text",
                    center_text="测试",
                    segments=[dict(text="这是一条字幕")],
                    image_generation=dict(
                        role="subject", asset_id="object", prompt="generic object"
                    ),
                )
            ],
        )
        g.save_json(path / "project.json", p)
        g.save_json(
            path / "connection.json",
            dict(
                base_url="https://relay.example/v1",
                api_mode="images",
                image_model="gpt-image-2",
            ),
        )
        g.save_json(path / "key.json", dict(api_key="local-secret-not-for-output"))
        return argparse.Namespace(
            project=str(path / "project.json"),
            connection=str(path / "connection.json"),
            credentials=str(path / "key.json"),
            output=str(path / "assets"),
            max_new_images=3,
            generate=False,
        )

    def test_plan_never_reads_key_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            Path(args.credentials).unlink()
            with patch.object(
                g.urllib.request, "build_opener", side_effect=AssertionError("network")
            ):
                self.assertEqual(g.run(args), 0)

    def test_generation_then_verified_cache_no_key_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            args.generate = True
            with patch.object(g.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value = Response()
                self.assertEqual(g.run(args), 0)
                self.assertEqual(opener.return_value.open.call_count, 1)
            Path(args.credentials).unlink()
            with patch.object(
                g.urllib.request,
                "build_opener",
                side_effect=AssertionError("repeat request"),
            ):
                self.assertEqual(g.run(args), 0)
            for file in Path(args.output).glob("*.json"):
                self.assertNotIn(
                    "local-secret-not-for-output", file.read_text(encoding="utf-8")
                )
            resolved = g.read_json(Path(args.output) / "resolved-project.json")
            self.assertTrue(Path(resolved["scenes"][0]["image"]).is_file())
            self.assertEqual(resolved["scenes"][0]["editorial_image_fit"], "contain")
            self.assertNotIn("image_layout", resolved["scenes"][0])

    def test_unresolved_submission_blocks_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            args.generate = True
            with patch.object(
                g.urllib.request, "build_opener", side_effect=TimeoutError
            ):
                self.assertEqual(g.run(args), 1)
            with patch.object(
                g.urllib.request,
                "build_opener",
                side_effect=AssertionError("repeat request"),
            ):
                self.assertEqual(g.run(args), 1)

    def test_provider_error_redacts_key_and_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            args.generate = True
            failure = g.urllib.error.HTTPError(
                "https://relay.example/v1/images/generations",
                403,
                "blocked",
                {},
                io.BytesIO(
                    json.dumps(
                        {"error": {"message": "denied local-secret-not-for-output"}}
                    ).encode()
                ),
            )
            captured = io.StringIO()
            with patch.object(
                g.urllib.request, "build_opener"
            ) as opener, contextlib.redirect_stdout(captured):
                opener.return_value.open.side_effect = failure
                self.assertEqual(g.run(args), 1)
                self.assertEqual(opener.return_value.open.call_count, 1)
            self.assertNotIn("local-secret-not-for-output", captured.getvalue())
            self.assertNotIn(
                "local-secret-not-for-output",
                (Path(args.output) / "generation-report.json").read_text(),
            )

    def test_corrupt_cache_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            args.generate = True
            with patch.object(g.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value = Response()
                self.assertEqual(g.run(args), 0)
            next(Path(args.output).glob("*.png")).write_bytes(b"bad")
            args.generate = False
            g.run(args)
            self.assertFalse(
                g.read_json(Path(args.output) / "generation-report.json")["jobs"][0][
                    "cache_hit"
                ]
            )

    def test_budget_protocol_and_url_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            args.max_new_images = 0
            with self.assertRaises(ValueError):
                g.run(args)
            for url in (
                "http://relay.example/v1",
                "https://user:key@relay.example/v1",
                "https://relay.example/v1?secret=x",
            ):
                with self.assertRaises(ValueError):
                    g.jobs_for(
                        g.read_json(args.project), dict(base_url=url, api_mode="images")
                    )

    def test_decode_rejects_text_multiple_and_broken_image(self):
        for data in (
            {"output_text": "image"},
            {"data": [{}, {}]},
            {"data": [{"b64_json": "bad"}]},
        ):
            with self.assertRaises(ValueError):
                g.decode_image(data)

    def test_redirect_refused(self):
        with self.assertRaises(ValueError):
            g.NoRedirect().redirect_request(None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
