import json
from pathlib import Path
import tempfile
import unittest

import daily_editorial


def plan():
    directions = {
        name: {"level": "supporting", "reason": f"fixture reason for {name}"}
        for name in (
            "content_depth",
            "content_value",
            "knowledge_value",
            "audio_visual_value",
            "emotion_value",
        )
    }
    return {
        "schema_version": 1,
        "plan_id": "daily-20261128-fixture",
        "episode_id": "idc-20261128-fixture",
        "publish_date": "2026-11-28",
        "timezone": "Asia/Shanghai",
        "question": "这条进展到底改变了什么？",
        "audience_outcome": "观众能区分公开容量、项目阶段和仍需核对的实际负载。",
        "lane": "engineering_progress",
        "format": "fact",
        "headline": "公开容量和实际负载，应该怎么区分？",
        "evidence_ids": ["fixture-e1"],
        "editorial_package_ids": ["fixture-package"],
        "value_intent": {
            "directions": directions,
            "column_identity": {
                "mode": "carry",
                "signals": ["公开声音", "短句字幕", "来源边界"],
                "fit_reason": "沿用已验收栏目线索，同时让主题承担容量口径解释。",
            },
        },
        "expression": {
            "text": "口播解释容量口径和阶段",
            "visual": "SVG对照公开容量与实际负载",
            "sound": "公开声音保持稳定语气",
            "structure": "先事实，再边界，最后给核对问题",
        },
        "interaction": {
            "type": "choose_follow_up",
            "prompt": "你更想继续查哪一项？",
            "options": ["实际启用时间", "公开IT负载"],
        },
        "follow_up_questions": ["下一次应补哪份运营披露？"],
        "review_policy": "user_requested_only",
        "topic_decision": {
            "source": "daily_scan",
            "reason": "当天证据明确，且能回答一个圈外人也会问的问题。",
        },
    }


class DailyEditorialTests(unittest.TestCase):
    def test_valid_plan(self):
        self.assertEqual(
            daily_editorial.validate_plan(plan())["headline"],
            "公开容量和实际负载，应该怎么区分？",
        )

    def test_interaction_without_prompt_is_rejected(self):
        invalid = plan()
        invalid["interaction"] = {"type": "collect_experience"}
        with self.assertRaisesRegex(ValueError, "interaction.prompt"):
            daily_editorial.validate_plan(invalid)

    def test_review_requires_explicit_user_request(self):
        review = {
            "schema_version": 1,
            "review_id": "review-fixture",
            "episode_id": "idc-20261128-fixture",
            "source_scope": "同题材、相近时长的作品",
            "trigger": "scheduled",
            "requested_at": "2026-11-28T09:00:00+08:00",
            "source": {
                "path": "private-export.xlsx",
                "sha256": "a" * 64,
                "exported_at": "2026-11-28T08:00:00+08:00",
            },
            "matched_works": [],
            "observations": [],
            "unknowns": [],
            "revisit_conditions": [],
        }
        with self.assertRaisesRegex(ValueError, "explicit user request"):
            daily_editorial.validate_review(review)

    def test_cli_validates_a_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(json.dumps(plan(), ensure_ascii=False), encoding="utf-8")
            result = __import__("subprocess").run(
                [
                    "python",
                    str(Path(__file__).with_name("daily_editorial.py")),
                    "validate-plan",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn('"valid": true', result.stdout)


if __name__ == "__main__":
    unittest.main()
