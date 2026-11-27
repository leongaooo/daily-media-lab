"""Validate the small editorial record used by the daily news-to-video entry.

The record keeps editorial choices close to the episode without pretending to
automate fact checking, audience analysis, committee decisions, or post-
publication review.  It is deliberately JSON-only so a plan can be inspected
and carried into a normal ``episode.py init`` run.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path


SCHEMA_VERSION = 1
LANES = {"engineering_progress", "technology_operations", "procurement_supply_chain"}
FORMATS = {"fact", "why", "how_to", "comparison", "choice", "follow_up"}
LEVELS = {"focus", "supporting", "not_claimed"}
IDENTITY_MODES = {"carry", "adjust", "create"}
INTERACTION_TYPES = {
    "none",
    "like",
    "choose_follow_up",
    "collect_experience",
    "collect_leads",
}
SUGGESTION_STATUSES = {"proposed", "accepted", "revise_after_evidence", "parked"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _require_string_list(value, label, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{label} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")


def _require_iso_date(value, label):
    _require_text(value, label)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must use YYYY-MM-DD") from error


def _require_iso_datetime(value, label):
    _require_text(value, label)
    try:
        datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO timestamp") from error


def _validate_directions(value):
    if not isinstance(value, dict):
        raise ValueError("value_intent.directions must be an object")
    expected = {
        "content_depth",
        "content_value",
        "knowledge_value",
        "audio_visual_value",
        "emotion_value",
    }
    if set(value) != expected:
        raise ValueError("value_intent.directions must cover the five value directions")
    for name, entry in value.items():
        if not isinstance(entry, dict):
            raise ValueError(f"value_intent.directions.{name} must be an object")
        if entry.get("level") not in LEVELS:
            raise ValueError(f"value_intent.directions.{name}.level is unsupported")
        _require_text(entry.get("reason"), f"value_intent.directions.{name}.reason")


def _validate_column_identity(value):
    if not isinstance(value, dict) or value.get("mode") not in IDENTITY_MODES:
        raise ValueError("value_intent.column_identity.mode is unsupported")
    _require_string_list(value.get("signals"), "value_intent.column_identity.signals")
    _require_text(value.get("fit_reason"), "value_intent.column_identity.fit_reason")


def _validate_interaction(value):
    if not isinstance(value, dict) or value.get("type") not in INTERACTION_TYPES:
        raise ValueError("interaction.type is unsupported")
    interaction_type = value["type"]
    if interaction_type == "none":
        if value.get("prompt") or value.get("options"):
            raise ValueError("interaction.none cannot carry a prompt or options")
        return
    _require_text(value.get("prompt"), "interaction.prompt")
    if interaction_type == "choose_follow_up":
        _require_string_list(value.get("options"), "interaction.options")
        if len(value["options"]) < 2:
            raise ValueError("interaction.options needs at least two choices")


def validate_plan(plan):
    """Validate a daily plan and return the same object for CLI composition."""
    if not isinstance(plan, dict) or plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Daily editorial plan requires schema_version=1")
    for key in ("plan_id", "episode_id", "question", "audience_outcome", "headline"):
        _require_text(plan.get(key), f"plan.{key}")
    _require_iso_date(plan.get("publish_date"), "plan.publish_date")
    if plan.get("timezone") != "Asia/Shanghai":
        raise ValueError("plan.timezone must be Asia/Shanghai")
    if plan.get("lane") not in LANES:
        raise ValueError("plan.lane is unsupported")
    if plan.get("format") not in FORMATS:
        raise ValueError("plan.format is unsupported")
    _require_string_list(plan.get("evidence_ids"), "plan.evidence_ids")
    _require_string_list(
        plan.get("editorial_package_ids"),
        "plan.editorial_package_ids",
        allow_empty=True,
    )
    value_intent = plan.get("value_intent")
    if not isinstance(value_intent, dict):
        raise ValueError("plan.value_intent must be an object")
    _validate_directions(value_intent.get("directions"))
    _validate_column_identity(value_intent.get("column_identity"))
    expression = plan.get("expression")
    if not isinstance(expression, dict):
        raise ValueError("plan.expression must be an object")
    for key in ("text", "visual", "sound", "structure"):
        _require_text(expression.get(key), f"plan.expression.{key}")
    _validate_interaction(plan.get("interaction"))
    if plan.get("review_policy") != "user_requested_only":
        raise ValueError("plan.review_policy must be user_requested_only")
    if "follow_up_questions" in plan:
        _require_string_list(plan["follow_up_questions"], "plan.follow_up_questions", True)
    if "topic_decision" in plan:
        decision = plan["topic_decision"]
        if not isinstance(decision, dict):
            raise ValueError("plan.topic_decision must be an object")
        _require_text(decision.get("reason"), "plan.topic_decision.reason")
        if decision.get("source") not in {"daily_scan", "committee", "user_requested"}:
            raise ValueError("plan.topic_decision.source is unsupported")
    return plan


def validate_suggestion(suggestion):
    """Validate a public suggestion before a human direction decision."""
    if not isinstance(suggestion, dict) or suggestion.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Suggestion requires schema_version=1")
    for key in ("suggestion_id", "original_text", "work_context"):
        _require_text(suggestion.get(key), f"suggestion.{key}")
    _require_iso_datetime(suggestion.get("captured_at"), "suggestion.captured_at")
    if suggestion.get("status") not in SUGGESTION_STATUSES:
        raise ValueError("suggestion.status is unsupported")
    _require_text(suggestion.get("decision_reason"), "suggestion.decision_reason")
    _require_string_list(
        suggestion.get("evidence_opportunities"),
        "suggestion.evidence_opportunities",
        True,
    )
    return suggestion


def validate_review(review):
    """Validate a manually requested review record without reading private exports."""
    if not isinstance(review, dict) or review.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Review requires schema_version=1")
    for key in ("review_id", "episode_id", "source_scope"):
        _require_text(review.get(key), f"review.{key}")
    if review.get("trigger") != "user_requested":
        raise ValueError("Review can only be recorded after an explicit user request")
    _require_iso_datetime(review.get("requested_at"), "review.requested_at")
    source = review.get("source")
    if not isinstance(source, dict):
        raise ValueError("review.source must be an object")
    for key in ("path", "sha256", "exported_at"):
        _require_text(source.get(key), f"review.source.{key}")
    _require_string_list(review.get("matched_works"), "review.matched_works", True)
    _require_string_list(review.get("observations"), "review.observations", True)
    _require_string_list(review.get("unknowns"), "review.unknowns", True)
    _require_string_list(
        review.get("revisit_conditions"), "review.revisit_conditions", True
    )
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-plan", "validate-suggestion", "validate-review"):
        command = sub.add_parser(name)
        command.add_argument("path")
    args = parser.parse_args()
    validators = {
        "validate-plan": validate_plan,
        "validate-suggestion": validate_suggestion,
        "validate-review": validate_review,
    }
    result = validators[args.command](read_json(args.path))
    result_id = result.get(
        "plan_id", result.get("suggestion_id", result.get("review_id"))
    )
    print(
        json.dumps(
            {"valid": True, "kind": args.command, "id": result_id},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
