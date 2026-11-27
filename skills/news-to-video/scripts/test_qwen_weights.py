"""Check that the Windows reader override is limited to model loading."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import qwen_weights


class QwenWeightReaderTests(unittest.TestCase):
    def test_windows_uses_pread_and_restores_reader_after_load_error(self):
        original = Mock(return_value="tensor bytes")
        module = SimpleNamespace(safe_open=original)

        def failing_load(model_dir, **options):
            self.assertEqual(model_dir, "model")
            self.assertEqual(options, {"device_map": "cpu"})
            self.assertEqual(
                module.safe_open("weights", framework="pt", device="cpu"),
                "tensor bytes",
            )
            raise RuntimeError("load failed")

        with (
            patch.object(qwen_weights, "os", SimpleNamespace(name="nt")),
            patch.dict(
                sys.modules, {"transformers": SimpleNamespace(modeling_utils=module)}
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "load failed"):
                qwen_weights.load_qwen_weights(failing_load, "model", device_map="cpu")
        original.assert_called_once_with(
            "weights", framework="pt", device="cpu", backend="pread"
        )
        self.assertIs(module.safe_open, original)

    def test_other_platform_delegates_to_the_normal_loader(self):
        normal_loader = Mock(return_value="model")
        with patch.object(qwen_weights, "os", SimpleNamespace(name="posix")):
            result = qwen_weights.load_qwen_weights(
                normal_loader, "model-directory", device_map="cpu"
            )
        self.assertEqual(result, "model")
        normal_loader.assert_called_once_with("model-directory", device_map="cpu")
