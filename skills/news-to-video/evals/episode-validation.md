# Editorial programme behaviour validation · 2026-11-20

Scope: evidence-package references, internal draft versus confirmed narration, programme artifact receipts, single-writer/revision behaviour and delivery/adoption recovery. No network, TTS, Blender, GPU or media decoding is performed by these tests.

Executed from the canonical root:

```powershell
python -X utf8 -m unittest discover -s skills/news-to-video/scripts -p test_episode.py -v
python -X utf8 skills/news-to-video/scripts/episode.py validate-package skills/news-to-video/assets/editorial-package-example.json
```

Result:18 tests passed (1.705 seconds in the recorded run); the synthetic package validates its reference structure. Black formatting was applied to episode.py/test_episode.py using temporary tooling outside the skill. The original system Python did not have Black; no production/runtime dependency was added.

The checks exercise missing evidence and duplicate IDs; editable new drafts and immutable editorial locks; previously confirmed scripts; prevention of draft overwrites on protected existing files; stale revisions; exclusive file locks, including a real second Python process; changed frozen artifacts; production-stage prerequisites; candidates refused as adopted; idempotent repeated adoption; ledger-save/episode-save interruption; script-to-video association on the same existing event; a mixed programme with partial domain failure and recovery; a changed-ledger hash precondition; recoverable failure receipts without false stage advancement; cross-package unprefixed claim/evidence/paragraph ID ambiguity; and exact composed-input identities in review/delivery, including wrong-artifact rejection. Tests use isolated synthetic data and do not alter user ledgers or tracker.

Two independently researched current IDC/Web3 packages were also run through validate-package by the coordinating task's editorial worker; both structural checks passed. This establishes field/reference compatibility only. The source researcher and coordinating task retain responsibility for original-page reads, dates, delta, factual boundaries and actual production evidence.

These results do not prove automatic skill routing, primary-source truth, source availability, video aesthetics, actual user receipt, listening quality, public-machine installation, remote publishing or end-to-end media delivery. CLI delivery receipts record the executor's actual delivery evidence; they cannot observe user receipt by themselves. Programme locking does not make two Markdown ledgers an atomic transaction. Source/mother-frame integrity and external_final media validation belong to the separate media execution contract.
