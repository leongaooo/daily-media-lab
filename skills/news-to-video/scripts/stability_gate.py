"""Structured quality layers for the optional stable daily-production gate.

The gate keeps technical, visual, sensory, audience, reproducibility and
approval evidence separate. A missing layer is represented explicitly instead
of being inferred from a successful player run or a single review comment.
"""

from __future__ import annotations


STABILITY_GATE_VERSION = 1
STABILITY_LAYER_KEYS = (
    "technical_decode",
    "actual_visual",
    "continuous_av",
    "manual_viewing",
    "manual_listening",
    "phone_viewing",
    "headphone_listening",
    "speaker_listening",
    "audience_recall",
    "cross_machine",
    "user_approval",
)
STABILITY_STATUSES = {"passed", "not_run", "blocked"}


def validate_stability_gate(gate):
    """Validate a layer-by-layer gate and return its computed summary.

    ``passed`` requires at least one evidence reference. ``not_run`` and
    ``blocked`` require a reason so a receipt cannot silently omit a quality
    layer. The stable result is derived from all layers and is checked against
    the recorded value to prevent a hand-edited optimistic summary.
    """

    if not isinstance(gate, dict) or gate.get("version") != STABILITY_GATE_VERSION:
        raise ValueError("Stability gate requires version=1")
    layers = gate.get("layers")
    if not isinstance(layers, dict) or set(layers) != set(STABILITY_LAYER_KEYS):
        raise ValueError("Stability gate must declare every quality layer")

    blocking_layers = []
    for key in STABILITY_LAYER_KEYS:
        layer = layers[key]
        if not isinstance(layer, dict):
            raise ValueError(f"Stability layer {key} must be an object")
        status = layer.get("status")
        if status not in STABILITY_STATUSES:
            raise ValueError(f"Stability layer {key} has an unsupported status")
        evidence = layer.get("evidence", [])
        if not isinstance(evidence, list) or any(
            not isinstance(item, str) or not item.strip() for item in evidence
        ):
            raise ValueError(f"Stability layer {key} evidence must be text references")
        reason = layer.get("reason")
        if status == "passed" and not evidence:
            raise ValueError(f"Passed stability layer {key} needs evidence")
        if status != "passed":
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"Unpassed stability layer {key} needs a reason")
            blocking_layers.append(key)

    stable_daily = not blocking_layers
    if gate.get("stable_daily") is not stable_daily:
        raise ValueError("Stability gate stable_daily does not match its layers")
    expected_status = "passed" if stable_daily else "deferred"
    if gate.get("status") != expected_status:
        raise ValueError("Stability gate status does not match its layers")
    recorded_blockers = gate.get("blocking_layers")
    if recorded_blockers != blocking_layers:
        raise ValueError("Stability gate blocking_layers does not match its layers")
    return {
        "version": STABILITY_GATE_VERSION,
        "stable_daily": stable_daily,
        "status": expected_status,
        "blocking_layers": blocking_layers,
    }
