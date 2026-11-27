"""Regression tests for explicit stable-daily quality layers."""

import unittest

from stability_gate import STABILITY_LAYER_KEYS, validate_stability_gate


def gate_with(status="passed"):
    layers = {}
    for key in STABILITY_LAYER_KEYS:
        layer = {"status": status, "evidence": [f"evidence:{key}"]}
        if status != "passed":
            layer = {
                "status": status,
                "evidence": [],
                "reason": f"No {key} evidence was collected",
            }
        layers[key] = layer
    blocking = [] if status == "passed" else list(STABILITY_LAYER_KEYS)
    return {
        "version": 1,
        "layers": layers,
        "stable_daily": status == "passed",
        "status": "passed" if status == "passed" else "deferred",
        "blocking_layers": blocking,
    }


class StabilityGateTests(unittest.TestCase):
    def test_all_layers_pass(self):
        summary = validate_stability_gate(gate_with())
        self.assertTrue(summary["stable_daily"])
        self.assertEqual(summary["blocking_layers"], [])

    def test_missing_sensory_evidence_stays_deferred(self):
        gate = gate_with()
        gate["layers"]["headphone_listening"] = {
            "status": "not_run",
            "evidence": [],
            "reason": "No headphone session was performed",
        }
        gate["stable_daily"] = False
        gate["status"] = "deferred"
        gate["blocking_layers"] = ["headphone_listening"]
        summary = validate_stability_gate(gate)
        self.assertFalse(summary["stable_daily"])
        self.assertEqual(summary["blocking_layers"], ["headphone_listening"])

    def test_single_approval_does_not_replace_other_layers(self):
        gate = gate_with("not_run")
        gate["layers"]["user_approval"] = {
            "status": "passed",
            "evidence": ["reviewer:directional-approval"],
        }
        gate["blocking_layers"].remove("user_approval")
        summary = validate_stability_gate(gate)
        self.assertFalse(summary["stable_daily"])
        self.assertIn("cross_machine", summary["blocking_layers"])

    def test_passed_layer_requires_evidence(self):
        gate = gate_with()
        gate["layers"]["technical_decode"] = {"status": "passed", "evidence": []}
        with self.assertRaisesRegex(ValueError, "technical_decode"):
            validate_stability_gate(gate)


if __name__ == "__main__":
    unittest.main()
