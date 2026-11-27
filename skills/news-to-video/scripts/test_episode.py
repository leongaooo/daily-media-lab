"""Isolated behaviour checks for evidence and adoption recovery; no TTS or rendering."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys

import episode


def package(domain="idc"):
    return {
        "schema_version": 1,
        "package_id": f"{domain}-fixture",
        "domain": domain,
        "coverage": {
            "start": "2026-11-19",
            "end": "2026-11-20",
            "timezone": "Asia/Shanghai",
            "limitations": ["Closed synthetic test; no current-news claim"],
        },
        "news": [
            {
                "news_id": f"{domain}-n1",
                "title": "Synthetic release",
                "topic_key": f"{domain}-release-1",
                "canonical_url": f"https://example.test/{domain}/release",
                "delta": "Synthetic first release; not deployed",
                "evidence": [
                    {
                        "evidence_id": f"{domain}-e1",
                        "url": f"https://example.test/{domain}/release",
                        "publisher": "Fixture maintainer",
                        "published_at": "2026-11-20",
                        "event_date": None,
                        "readable_excerpt": "A proposed release, not deployment.",
                        "source_type": "maintainer_statement",
                    }
                ],
                "claims": [
                    {
                        "claim_id": f"{domain}-c1",
                        "text": "Proposed release, not deployment",
                        "evidence_ids": [f"{domain}-e1"],
                    }
                ],
                "paragraphs": [
                    {
                        "paragraph_id": f"{domain}-p1",
                        "text": "This fixture is a proposal.",
                        "claim_ids": [f"{domain}-c1"],
                    }
                ],
                "limitations": ["No deployment evidence"],
                "material_constraints": ["No project photograph"],
            }
        ],
    }


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "episode.json"
        self.package_path = self.root / "idc.json"
        episode.atomic_json(self.package_path, package())
        self.state = episode.create_episode(
            self.path,
            "fixture-episode",
            "synthetic test",
            [self.package_path],
            acceptance_contract="legacy",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_daily_editorial_plan_is_bound_and_verified(self):
        plan_path = self.root / "editorial-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "plan_id": "daily-fixture-plan",
                    "episode_id": "fixture-episode",
                    "publish_date": "2026-11-28",
                    "timezone": "Asia/Shanghai",
                    "question": "这条消息改变了什么？",
                    "audience_outcome": "能说出已披露范围和待核边界。",
                    "lane": "engineering_progress",
                    "format": "fact",
                    "headline": "这条消息改变了什么？",
                    "evidence_ids": ["idc-e1"],
                    "editorial_package_ids": ["idc-fixture"],
                    "value_intent": {
                        "directions": {
                            name: {
                                "level": "supporting",
                                "reason": "fixture",
                            }
                            for name in (
                                "content_depth",
                                "content_value",
                                "knowledge_value",
                                "audio_visual_value",
                                "emotion_value",
                            )
                        },
                        "column_identity": {
                            "mode": "carry",
                            "signals": ["subtitle rail"],
                            "fit_reason": "fixture",
                        },
                    },
                    "expression": {
                        "text": "fixture",
                        "visual": "fixture",
                        "sound": "fixture",
                        "structure": "fixture",
                    },
                    "interaction": {"type": "none"},
                    "review_policy": "user_requested_only",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        plan_episode_path = self.root / "editorial-plan-episode.json"
        state = episode.create_episode(
            plan_episode_path,
            "fixture-episode",
            "synthetic test",
            [self.package_path],
            acceptance_contract="legacy",
            editorial_plan=plan_path,
        )
        self.assertEqual(state["editorial_plan"]["path"], str(plan_path.resolve()))
        episode.verify_episode(state)
        plan_path.write_text(
            plan_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "Artifact identity changed"):
            episode.verify_episode(episode.read_json(plan_episode_path))

    def draft(self):
        self.draft_path = self.root / "draft.json"
        self.state = episode.draft_episode(
            self.path,
            self.state["revision"],
            package()["news"][0]["paragraphs"],
            self.draft_path,
        )

    def lock(self):
        self.draft()
        self.state = episode.record_stage(
            self.path,
            self.state["revision"],
            "editorial_locked",
            [self.draft_path],
            ["Synthetic editorial review"],
        )

    def deliver(self):
        self.lock()
        self.state = episode.record_delivery(
            self.path,
            self.state["revision"],
            "script",
            self.draft_path,
            "isolated-fixture-reviewer",
            "2026-11-20T12:00:00+08:00",
            "Synthetic delivery receipt; no real delivery",
        )
        return self.state["delivery_receipts"][0]

    def ledger(self, domain="idc"):
        path = self.root / f"{domain}-ledger.md"
        header = (
            "| Date | URL | Title | Source | Topic | Domain | Why |"
            if domain == "idc"
            else (
                "| Date | URL | Title | Source | Topic | Project | Version | "
                "Dates | Delta | Delivery |"
            )
        )
        columns = 7 if domain == "idc" else 10
        path.write_text(
            "# Keep history\n\n"
            + header
            + "\n|"
            + "---|" * columns
            + "\n\n## Archive\nKeep this exact history.\n",
            encoding="utf-8",
        )
        return path

    def test_missing_evidence_and_duplicated_ids_rejected(self):
        invalid = deepcopy(package())
        invalid["news"][0]["claims"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "missing evidence"):
            episode.validate_package(invalid)
        invalid = deepcopy(package())
        invalid["news"][0]["paragraphs"][0]["paragraph_id"] = "idc-e1"
        with self.assertRaisesRegex(ValueError, "package-unique"):
            episode.validate_package(invalid)

    def test_draft_editable_until_editorial_lock(self):
        self.lock()
        with self.assertRaisesRegex(ValueError, "confirmed or locked"):
            episode.draft_episode(
                self.path,
                self.state["revision"],
                package()["news"][0]["paragraphs"],
                self.draft_path,
            )

    def test_confirmed_script_protected_before_new_lock(self):
        confirmed = self.root / "confirmed.md"
        confirmed.write_text("Previously confirmed script", encoding="utf-8")
        protected = self.root / "protected-episode.json"
        state = episode.create_episode(
            protected, "protected", "existing script", [self.package_path], confirmed
        )
        with self.assertRaisesRegex(ValueError, "confirmed or locked"):
            episode.draft_episode(
                protected,
                state["revision"],
                package()["news"][0]["paragraphs"],
                self.root / "replacement.json",
            )
        self.assertEqual(
            confirmed.read_text(encoding="utf-8"), "Previously confirmed script"
        )

    def test_draft_cannot_overwrite_package_or_episode(self):
        for output in [self.package_path, self.path]:
            with self.assertRaisesRegex(ValueError, "must be new"):
                episode.draft_episode(
                    self.path,
                    self.state["revision"],
                    package()["news"][0]["paragraphs"],
                    output,
                )

    def test_revision_and_writer_lock_refuse_competing_change(self):
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            episode.draft_episode(
                self.path,
                0,
                package()["news"][0]["paragraphs"],
                self.root / "draft.json",
            )
        with episode.exclusive(self.path):
            with self.assertRaisesRegex(ValueError, "Writer lock exists"):
                episode.draft_episode(
                    self.path,
                    1,
                    package()["news"][0]["paragraphs"],
                    self.root / "draft.json",
                )
        self.assertFalse(Path(str(self.path) + ".lock").exists())

    def test_stale_frozen_artifact_blocks_resume(self):
        self.lock()
        self.draft_path.write_text("changed after lock", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identity changed"):
            episode.verify_episode(episode.read_json(self.path))

    def test_video_requires_reviewed_production_and_cannot_adopt_candidate(self):
        video = self.root / "video.mp4"
        video.write_bytes(b"not real media; stage refusal only")
        with self.assertRaisesRegex(ValueError, "completed reviewed"):
            episode.record_delivery(
                self.path,
                1,
                "video",
                video,
                "fixture",
                "2026-11-20T12:00:00+08:00",
                "fixture",
            )
        with self.assertRaisesRegex(ValueError, "No actual delivery"):
            episode.commit_adoption(self.path, 1, "idc", self.ledger(), "not-delivered")

    def test_stage_dependency_and_changed_locked_stage_refused(self):
        self.lock()
        with self.assertRaisesRegex(ValueError, "dependencies not ready"):
            episode.record_stage(
                self.path,
                self.state["revision"],
                "composed",
                [self.draft_path],
                ["fixture"],
            )
        with self.assertRaisesRegex(ValueError, "identity differs"):
            episode.record_stage(
                self.path,
                self.state["revision"],
                "editorial_locked",
                [self.draft_path],
                ["different review"],
            )

    def test_adoption_preserves_history_and_retries_without_duplicate(self):
        delivery = self.deliver()
        ledger = self.ledger()
        self.state = episode.commit_adoption(
            self.path, self.state["revision"], "idc", ledger, delivery["delivery_id"]
        )
        original = ledger.read_bytes()
        self.state = episode.commit_adoption(
            self.path, self.state["revision"], "idc", ledger, delivery["delivery_id"]
        )
        self.assertEqual(original, ledger.read_bytes())
        self.assertIn(b"Keep this exact history.", original)
        self.assertEqual(original.count(b"media-adoption:"), 1)
        self.assertEqual(len(self.state["adoption_receipts"]), 1)

    def test_crash_after_ledger_before_receipt_recovers(self):
        delivery = self.deliver()
        ledger = self.ledger()
        old_revision = self.state["revision"]
        with patch.object(
            episode,
            "atomic_json",
            side_effect=OSError("simulated receipt save failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated"):
                episode.commit_adoption(
                    self.path, old_revision, "idc", ledger, delivery["delivery_id"]
                )
        self.assertEqual(ledger.read_text(encoding="utf-8").count("media-adoption:"), 1)
        state = episode.commit_adoption(
            self.path, old_revision, "idc", ledger, delivery["delivery_id"]
        )
        self.assertEqual(len(state["adoption_receipts"]), 1)
        self.assertEqual(ledger.read_text(encoding="utf-8").count("media-adoption:"), 1)

    def test_existing_event_script_to_video_updates_same_row(self):
        delivery = self.deliver()
        news = package()["news"][0]
        ledger = self.ledger().read_text(encoding="utf-8")
        updated, _ = episode.ledger_update(
            ledger, "idc", news, delivery, "fixture-episode"
        )
        video_delivery = {**delivery, "kind": "video", "delivery_id": "video-delivery"}
        combined, _ = episode.ledger_update(
            updated, "idc", news, video_delivery, "fixture-episode"
        )
        self.assertEqual(combined.count(news["topic_key"]), 1)
        self.assertIn("剧本", combined)
        self.assertIn("已制成视频", combined)

    def test_mixed_packages_one_programme_and_independent_receipts(self):
        web3_path = self.root / "web3.json"
        episode.atomic_json(web3_path, package("web3"))
        mixed_path = self.root / "mixed.json"
        state = episode.create_episode(
            mixed_path, "mixed", "one programme", [self.package_path, web3_path]
        )
        self.assertEqual(
            {item["domain"] for item in state["packages"]}, {"idc", "web3"}
        )
        self.assertEqual(state["delivery_receipts"], [])
        self.assertEqual(state["adoption_receipts"], [])

    def test_mixed_partial_adoption_recovers_only_missing_domain(self):
        web3_path = self.root / "web3.json"
        episode.atomic_json(web3_path, package("web3"))
        mixed_path = self.root / "mixed.json"
        state = episode.create_episode(
            mixed_path, "mixed", "one programme", [self.package_path, web3_path]
        )
        draft_path = self.root / "mixed-draft.json"
        paragraphs = (
            package()["news"][0]["paragraphs"]
            + package("web3")["news"][0]["paragraphs"]
        )
        state = episode.draft_episode(
            mixed_path, state["revision"], paragraphs, draft_path
        )
        state = episode.record_stage(
            mixed_path,
            state["revision"],
            "editorial_locked",
            [draft_path],
            ["Synthetic review"],
        )
        state = episode.record_delivery(
            mixed_path,
            state["revision"],
            "script",
            draft_path,
            "fixture",
            "2026-11-20T12:00:00+08:00",
            "Synthetic delivery",
        )
        delivery_id = state["delivery_receipts"][0]["delivery_id"]
        idc_ledger = self.ledger("idc")
        web3_ledger = self.ledger("web3")
        web3_ledger.write_text("Malformed fixture ledger", encoding="utf-8")
        state = episode.commit_adoption(
            mixed_path, state["revision"], "idc", idc_ledger, delivery_id
        )
        saved_idc = idc_ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, "header not recognized"):
            episode.commit_adoption(
                mixed_path, state["revision"], "web3", web3_ledger, delivery_id
            )
        state = episode.read_json(mixed_path)
        self.assertEqual(
            [item["domain"] for item in state["adoption_receipts"]], ["idc"]
        )
        web3_ledger = self.ledger("web3")
        state = episode.commit_adoption(
            mixed_path, state["revision"], "web3", web3_ledger, delivery_id
        )
        self.assertEqual(
            {item["domain"] for item in state["adoption_receipts"]}, {"idc", "web3"}
        )
        self.assertEqual(saved_idc, idc_ledger.read_bytes())
        self.assertEqual(
            web3_ledger.read_text(encoding="utf-8").count("media-adoption:"), 1
        )

    def test_writer_lock_refuses_a_real_second_process(self):
        code = (
            "import sys; from pathlib import Path; import episode\n"
            "try:\n"
            "    with episode.exclusive(Path(sys.argv[1])): pass\n"
            "except ValueError:\n"
            "    print('competing writer refused')\n"
            "else:\n"
            "    raise SystemExit(99)\n"
        )
        with episode.exclusive(self.path):
            result = subprocess.run(
                [sys.executable, "-c", code, str(self.path)],
                cwd=Path(episode.__file__).parent,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("competing writer refused", result.stdout)

    def test_changed_ledger_precondition_preserves_all_data(self):
        delivery = self.deliver()
        ledger = self.ledger()
        before = ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, "Ledger changed"):
            episode.commit_adoption(
                self.path,
                self.state["revision"],
                "idc",
                ledger,
                delivery["delivery_id"],
                "not-current-hash",
            )
        self.assertEqual(before, ledger.read_bytes())

    def test_failure_receipt_does_not_advance_completed_stages(self):
        state = episode.record_failure(
            self.path,
            1,
            "audio_locked",
            "Synthetic TTS interruption",
            "rerun missing clips",
            [self.package_path],
        )
        revision = state["revision"]
        self.assertNotIn("audio_locked", state["stage_receipts"])
        repeated = episode.record_failure(
            self.path,
            revision,
            "audio_locked",
            "Synthetic TTS interruption",
            "rerun missing clips",
            [self.package_path],
        )
        self.assertEqual(repeated["revision"], revision)
        self.assertEqual(len(repeated["failure_receipts"]), 1)

    def test_unprefixed_cross_package_reference_ids_rejected(self):
        unprefixed = package()
        unprefixed["news"][0]["evidence"][0]["evidence_id"] = "E1"
        unprefixed["news"][0]["claims"][0].update(claim_id="C1", evidence_ids=["E1"])
        unprefixed["news"][0]["paragraphs"][0].update(
            paragraph_id="P1", claim_ids=["C1"]
        )
        unprefixed_path = self.root / "unprefixed-idc.json"
        episode.atomic_json(unprefixed_path, unprefixed)
        for group, id_key in [
            ("claims", "claim_id"),
            ("evidence", "evidence_id"),
            ("paragraphs", "paragraph_id"),
        ]:
            other = deepcopy(package("web3"))
            conflict = unprefixed["news"][0][group][0][id_key]
            other["news"][0][group][0][id_key] = conflict
            if group == "claims":
                other["news"][0]["paragraphs"][0]["claim_ids"] = [conflict]
            elif group == "evidence":
                other["news"][0]["claims"][0]["evidence_ids"] = [conflict]
            other_path = self.root / f"duplicate-{group}.json"
            episode.atomic_json(other_path, other)
            with self.assertRaisesRegex(ValueError, "Cross-package duplicate"):
                episode.create_episode(
                    self.root / f"bad-{group}.json",
                    "mixed-ambiguous",
                    "synthetic",
                    [unprefixed_path, other_path],
                )

    def test_review_binds_exact_composed_artifact_before_delivery(self):
        self.lock()
        for stage in [
            "audio_locked",
            "visual_ready",
            "animatic_reviewed",
            "masters_ready",
        ]:
            artifact = self.root / f"{stage}.txt"
            artifact.write_text(f"Synthetic artifact for {stage}", encoding="utf-8")
            self.state = episode.record_stage(
                self.path,
                self.state["revision"],
                stage,
                [artifact],
                ["Synthetic completion"],
            )
        video_a = self.root / "a.mp4"
        video_b = self.root / "b.mp4"
        video_a.write_bytes(b"synthetic video A identity only")
        video_b.write_bytes(b"synthetic video B identity only")
        self.state = episode.record_stage(
            self.path,
            self.state["revision"],
            "composed",
            [video_a, video_b],
            ["Synthetic composition"],
        )
        review = self.root / "review.md"
        review.write_text("Reviewed synthetic A only", encoding="utf-8")
        for inputs in [[], [self.draft_path]]:
            with self.assertRaisesRegex(ValueError, "actual composed artifact"):
                episode.record_stage(
                    self.path,
                    self.state["revision"],
                    "reviewed",
                    [review],
                    ["Synthetic review"],
                    inputs,
                )
        self.state = episode.record_stage(
            self.path,
            self.state["revision"],
            "reviewed",
            [review],
            ["Synthetic A review"],
            [video_a],
        )
        with self.assertRaisesRegex(ValueError, "not covered"):
            episode.record_delivery(
                self.path,
                self.state["revision"],
                "video",
                video_b,
                "fixture",
                "2026-11-20T12:00:00+08:00",
                "Synthetic delivery",
            )
        self.state = episode.record_delivery(
            self.path,
            self.state["revision"],
            "video",
            video_a,
            "fixture",
            "2026-11-20T12:00:00+08:00",
            "Synthetic delivery",
        )
        self.assertEqual(
            self.state["delivery_receipts"][0]["artifact"],
            episode.file_identity(video_a),
        )


if __name__ == "__main__":
    unittest.main()
