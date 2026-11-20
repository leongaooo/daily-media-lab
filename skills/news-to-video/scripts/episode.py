"""Evidence packages and recoverable programme receipts; no network or media effects.

Production and delivery are separate events. Markdown ledgers retain their existing
headers and history; adoption annotations make a retry safe even if a crash occurs
after the ledger replacement but before the episode receipt is saved.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import uuid

STAGE_DEPENDENCIES = {
    "editorial_locked": ["evidence_ready"],
    "audio_locked": ["editorial_locked"],
    "visual_ready": ["editorial_locked"],
    "animatic_reviewed": ["audio_locked", "visual_ready"],
    "masters_ready": ["animatic_reviewed"],
    "composed": ["masters_ready", "audio_locked"],
    "reviewed": ["composed"],
}
DELIVERY_KINDS = {"text": "文字稿", "script": "剧本", "video": "已制成视频"}


def digest(value):
    """Hash canonical JSON for stable receipt identities."""
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_identity(path):
    """Capture an actual nonempty artifact, never a planned output path."""
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise ValueError(f"Artifact must be a nonempty file: {resolved}")
    hasher = hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return {
        "path": str(resolved),
        "sha256": hasher.hexdigest(),
        "bytes": resolved.stat().st_size,
    }


def verify_identity(identity):
    actual = file_identity(identity["path"])
    if actual != identity:
        raise ValueError(f"Artifact identity changed: {identity['path']}")


def _required_text(item, keys, label):
    if not isinstance(item, dict):
        raise ValueError(f"{label} must be an object")
    for key in keys:
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError(f"{label}.{key} must be nonempty text")


def _url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Expected a source HTTP(S) URL: {value}")


def validate_package(package):
    """Validate referential integrity; source truth still requires editorial review."""
    if package.get("schema_version") != 1 or package.get("domain") not in {
        "idc",
        "web3",
    }:
        raise ValueError("Evidence package needs schema_version=1 and domain=idc|web3")
    _required_text(package, ["package_id"], "package")
    coverage = package.get("coverage", {})
    _required_text(coverage, ["start", "end", "timezone"], "coverage")
    if "limitations" not in coverage:
        raise ValueError(
            "coverage.limitations must explicitly describe coverage limits"
        )
    if not isinstance(package.get("news"), list) or not package["news"]:
        raise ValueError("Evidence package needs at least one verified news item")
    ids = set()
    topics = set()
    urls = set()
    for news in package["news"]:
        _required_text(news, ["news_id", "topic_key", "canonical_url", "delta"], "news")
        _url(news["canonical_url"])
        if news["topic_key"] in topics or news["canonical_url"] in urls:
            raise ValueError("One event must not appear twice in an evidence package")
        topics.add(news["topic_key"])
        urls.add(news["canonical_url"])
        if "limitations" not in news or "material_constraints" not in news:
            raise ValueError("News must declare limitations and material_constraints")
        groups = [
            ("evidence", "evidence_id"),
            ("claims", "claim_id"),
            ("paragraphs", "paragraph_id"),
        ]
        ids_to_add = [news["news_id"]]
        for group, id_key in groups:
            if not isinstance(news.get(group), list) or not news[group]:
                raise ValueError(f"News needs nonempty {group}")
            for record in news[group]:
                _required_text(record, [id_key], group)
                ids_to_add.append(record[id_key])
        if len(set(ids_to_add)) != len(ids_to_add) or ids.intersection(ids_to_add):
            raise ValueError(
                "Evidence, claim, news and paragraph IDs must be package-unique"
            )
        ids.update(ids_to_add)
        evidence_ids = {item["evidence_id"] for item in news["evidence"]}
        claim_ids = {item["claim_id"] for item in news["claims"]}
        for evidence in news["evidence"]:
            _required_text(
                evidence,
                ["url", "publisher", "readable_excerpt", "source_type"],
                "evidence",
            )
            _url(evidence["url"])
            if "published_at" not in evidence or "event_date" not in evidence:
                raise ValueError(
                    "Evidence must distinguish publication and event dates; null means unknown"
                )
        for claim in news["claims"]:
            _required_text(claim, ["text"], "claim")
            if (
                not claim.get("evidence_ids")
                or not set(claim["evidence_ids"]) <= evidence_ids
            ):
                raise ValueError("Claim references missing evidence")
        for paragraph in news["paragraphs"]:
            _required_text(paragraph, ["text"], "paragraph")
            if (
                not paragraph.get("claim_ids")
                or not set(paragraph["claim_ids"]) <= claim_ids
            ):
                raise ValueError("Paragraph references missing claims")
    return package


def _package_receipts(paths):
    receipts = []
    seen_ids = set()
    seen_package_ids = set()
    seen_topics = set()
    seen_urls = set()
    for path in paths:
        package = validate_package(read_json(path))
        if package["package_id"] in seen_package_ids:
            raise ValueError("Package IDs must be unique within an episode")
        seen_package_ids.add(package["package_id"])
        for news in package["news"]:
            local_ids = {news["news_id"]}
            for group, id_key in [
                ("evidence", "evidence_id"),
                ("claims", "claim_id"),
                ("paragraphs", "paragraph_id"),
            ]:
                local_ids.update(item[id_key] for item in news[group])
            if (
                local_ids.intersection(seen_ids)
                or news["topic_key"] in seen_topics
                or news["canonical_url"] in seen_urls
            ):
                raise ValueError(
                    "Cross-package duplicate event; merge its evidence before programme assembly"
                )
            seen_ids.update(local_ids)
            seen_topics.add(news["topic_key"])
            seen_urls.add(news["canonical_url"])
        receipts.append(
            {
                "package_id": package["package_id"],
                "domain": package["domain"],
                **file_identity(path),
            }
        )
    if not receipts:
        raise ValueError("At least one evidence package is required")
    return receipts


def atomic_json(path, value):
    """Replace within the same directory so interrupted writes keep the old receipt."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(
        path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _atomic_bytes(path, data):
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def exclusive(path):
    """Refuse a competing writer. A leftover lock requires owner verification, not timeout deletion."""
    lock_path = Path(str(path) + ".lock")
    owner = {"pid": os.getpid(), "nonce": uuid.uuid4().hex}
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ValueError(
            f"Writer lock exists; inspect its owner before recovery: {lock_path}"
        ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(owner, stream)
        yield
    finally:
        if lock_path.exists() and read_json(lock_path) == owner:
            lock_path.unlink()


def _current(path, revision):
    state = read_json(path)
    if state.get("schema_version") != 1 or state.get("revision") != revision:
        raise ValueError("Episode revision mismatch; reread before writing")
    verify_episode(state)
    return state


def create_episode(path, episode_id, request, packages, confirmed_script=None):
    """Create internal evidence-ready state without claiming user delivery."""
    if not isinstance(episode_id, str) or not episode_id.strip() or not request:
        raise ValueError("Episode needs a stable episode_id and the actual request")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive(path):
        if path.exists():
            raise ValueError(
                "Episode already exists; resume it instead of replacing its identity"
            )
        package_receipts = _package_receipts(packages)
        state = {
            "schema_version": 1,
            "episode_id": episode_id,
            "revision": 1,
            "request": request,
            "packages": package_receipts,
            "stage_receipts": {
                "evidence_ready": {
                    "outputs": package_receipts,
                    "evidence": [
                        "Package references validated; factual review remains editorial responsibility"
                    ],
                }
            },
            "delivery_receipts": [],
            "adoption_receipts": [],
            "failure_receipts": [],
        }
        if confirmed_script:
            state["confirmed_script"] = file_identity(confirmed_script)
        atomic_json(path, state)
    return state


def verify_episode(state):
    """Detect changed dependencies before resuming; never relabel stale output as current."""
    for package in state["packages"]:
        verify_identity({key: package[key] for key in ["path", "sha256", "bytes"]})
        validate_package(read_json(package["path"]))
    if state.get("confirmed_script"):
        verify_identity(state["confirmed_script"])
    for receipt in state["stage_receipts"].values():
        for artifact in receipt.get("inputs", []) + receipt.get("outputs", []):
            verify_identity({key: artifact[key] for key in ["path", "sha256", "bytes"]})
    for receipt in state["delivery_receipts"]:
        verify_identity(receipt["artifact"])
    return state


def draft_episode(path, revision, paragraphs, output):
    """Edit an internal draft only before lock; existing confirmed scripts are immutable inputs."""
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        if (
            state.get("confirmed_script")
            or "editorial_locked" in state["stage_receipts"]
        ):
            raise ValueError(
                "Narration is confirmed or locked; visual work cannot rewrite it"
            )
        claims = set()
        paragraph_ids = set()
        for package in state["packages"]:
            for news in read_json(package["path"])["news"]:
                claims.update(item["claim_id"] for item in news["claims"])
        for paragraph in paragraphs:
            _required_text(paragraph, ["paragraph_id", "text"], "draft paragraph")
            if paragraph["paragraph_id"] in paragraph_ids:
                raise ValueError("Draft paragraph IDs must remain unique")
            paragraph_ids.add(paragraph["paragraph_id"])
            if (
                not paragraph.get("claim_ids")
                or not set(paragraph["claim_ids"]) <= claims
            ):
                raise ValueError("Edited draft must retain traceable claim references")
        if not paragraphs:
            raise ValueError("Draft needs paragraphs")
        destination = Path(output).resolve()
        current_draft = state.get("draft", {}).get("path")
        if destination == path.resolve() or (
            destination.exists() and str(destination) != current_draft
        ):
            raise ValueError(
                "Draft output must be new or this episode's existing unlocked draft"
            )
        atomic_json(
            Path(output), {"episode_id": state["episode_id"], "paragraphs": paragraphs}
        )
        state["draft"] = file_identity(output)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def record_stage(path, revision, stage, outputs, evidence, inputs=()):
    """Record verified artifacts and dependencies after the executor actually completes a stage."""
    if stage not in STAGE_DEPENDENCIES or not evidence:
        raise ValueError("Known stage and concrete completion evidence required")
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        missing = set(STAGE_DEPENDENCIES[stage]) - state["stage_receipts"].keys()
        if missing:
            raise ValueError(f"Stage dependencies not ready: {sorted(missing)}")
        receipt = {
            "inputs": [file_identity(item) for item in inputs],
            "outputs": [file_identity(item) for item in outputs],
            "evidence": evidence,
        }
        if not receipt["outputs"]:
            raise ValueError("Stage receipt must identify actual outputs")
        if stage == "editorial_locked":
            narration = state.get("confirmed_script") or state.get("draft")
            if not narration or narration not in receipt["outputs"]:
                raise ValueError(
                    "Editorial lock must include the current draft or confirmed script identity"
                )
            verify_identity(narration)
        if stage == "reviewed":
            composed_outputs = state["stage_receipts"]["composed"]["outputs"]
            if not any(item in composed_outputs for item in receipt["inputs"]):
                raise ValueError(
                    "Review must identify the actual composed artifact(s) it inspected"
                )
        existing = state["stage_receipts"].get(stage)
        if existing:
            if existing != receipt:
                raise ValueError(
                    "Completed stage identity differs; fork an episode revision instead of overwriting a lock"
                )
            return state
        state["stage_receipts"][stage] = receipt
        state["revision"] += 1
        atomic_json(path, state)
        return state


def record_delivery(
    path, revision, kind, artifact, delivered_to, delivered_at, evidence
):
    """Declare an actual user-facing delivery; an internal render is not delivery evidence."""
    if kind not in DELIVERY_KINDS or not delivered_to or not evidence:
        raise ValueError(
            "Delivery needs kind, destination and actual delivery evidence"
        )
    if datetime.fromisoformat(delivered_at).tzinfo is None:
        raise ValueError("Delivery timestamp must include a timezone")
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        required = "reviewed" if kind == "video" else "editorial_locked"
        if required not in state["stage_receipts"]:
            raise ValueError(f"Delivery requires completed {required}")
        identity = file_identity(artifact)
        output_stage = "composed" if kind == "video" else "editorial_locked"
        eligible = state["stage_receipts"][output_stage]["outputs"]
        if identity not in eligible:
            raise ValueError("Delivered artifact must be an identified stage output")
        if (
            kind == "video"
            and identity not in state["stage_receipts"]["reviewed"]["inputs"]
        ):
            raise ValueError(
                "Delivered video identity was not covered by the recorded review"
            )
        receipt = {
            "kind": kind,
            "artifact": identity,
            "delivered_to": delivered_to,
            "delivered_at": delivered_at,
            "evidence": evidence,
        }
        receipt["delivery_id"] = digest(
            {
                "episode_id": state["episode_id"],
                "kind": kind,
                "sha256": identity["sha256"],
            }
        )
        existing = next(
            (
                item
                for item in state["delivery_receipts"]
                if item["delivery_id"] == receipt["delivery_id"]
            ),
            None,
        )
        if existing:
            return state
        state["delivery_receipts"].append(receipt)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def record_failure(path, revision, stage, reason, resume_from, inputs=()):
    """Keep a recoverable failure without falsely advancing a successful stage."""
    if stage not in {*STAGE_DEPENDENCIES, "adoption"} or not reason or not resume_from:
        raise ValueError(
            "Failure requires a known stage, actual reason and recovery location"
        )
    path = Path(path)
    with exclusive(path):
        state = _current(path, revision)
        receipt = {
            "stage": stage,
            "reason": reason,
            "resume_from": resume_from,
            "inputs": [file_identity(item) for item in inputs],
        }
        # A repeated report should not create new revisions or erase prior evidence.
        failures = state.setdefault("failure_receipts", [])
        if receipt in failures:
            return state
        failures.append(receipt)
        state["revision"] += 1
        atomic_json(path, state)
        return state


def _cell(value):
    return (
        str(value if value is not None else "未知")
        .replace("|", "&#124;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def ledger_update(text, domain, news, delivery, episode_id):
    """Pure, history-preserving ledger patch; retry detects the inline adoption identity."""
    adoption_id = digest(
        {
            "episode_id": episode_id,
            "news_id": news["news_id"],
            "delivery_id": delivery["delivery_id"],
        }
    )
    marker = f"<!-- media-adoption:{adoption_id} -->"
    if marker in text:
        return text, adoption_id
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    columns = 7 if domain == "idc" else 10
    topic_column = 4
    first_separator = None
    existing_index = None
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [item.strip() for item in line.strip().strip("|").split("|")]
        if len(cells) != columns:
            continue
        if all(item and set(item) <= {"-", ":", " "} for item in cells):
            if first_separator is None:
                first_separator = index
        elif cells[topic_column] == _cell(news["topic_key"]):
            existing_index = index
            break
    if first_separator is None:
        raise ValueError(
            "Ledger header not recognized; refusing a destructive format migration"
        )
    annotation = f"{DELIVERY_KINDS[delivery['kind']]}；episode={episode_id}；{delivery['artifact']['path']}；sha256={delivery['artifact']['sha256']}；{marker}"
    if existing_index is not None:
        original = lines[existing_index].rstrip()
        lines[existing_index] = original[:-1].rstrip() + "；" + _cell(annotation) + " |"
    else:
        primary = news["evidence"][0]
        day = delivery["delivered_at"][:10]
        common = [
            day,
            news["canonical_url"],
            news.get("title", news["news_id"]),
            primary["publisher"],
            news["topic_key"],
        ]
        if domain == "idc":
            cells = common + [
                news.get("category", "IDC"),
                news["delta"] + "；" + annotation,
            ]
        else:
            cells = common + [
                news.get("project", "未指定"),
                news.get("version", "未指定"),
                f"发布{primary['published_at']}；事件{primary['event_date']}",
                news["delta"],
                annotation,
            ]
        lines.insert(
            first_separator + 1, "| " + " | ".join(_cell(item) for item in cells) + " |"
        )
    return (
        newline.join(lines) + (newline if text.endswith(("\n", "\r")) else ""),
        adoption_id,
    )


def commit_adoption(
    path, revision, domain, ledger_path, delivery_id, expected_ledger_sha256=None
):
    """Commit one domain after delivery; independent domain receipts support mixed-episode recovery."""
    path = Path(path)
    ledger_path = Path(ledger_path)
    with exclusive(path):
        state = _current(path, revision)
        delivery = next(
            (
                item
                for item in state["delivery_receipts"]
                if item["delivery_id"] == delivery_id
            ),
            None,
        )
        if not delivery:
            raise ValueError("No actual delivery receipt; candidates cannot be adopted")
        packages = [item for item in state["packages"] if item["domain"] == domain]
        if not packages:
            raise ValueError("Episode has no evidence package for this domain")
        with exclusive(ledger_path):
            identity = file_identity(ledger_path)
            if expected_ledger_sha256 and identity["sha256"] != expected_ledger_sha256:
                raise ValueError("Ledger changed; reread before adoption")
            original = ledger_path.read_bytes().decode("utf-8-sig")
            updated = original
            adoption_ids = []
            for package in packages:
                for news in read_json(package["path"])["news"]:
                    updated, adoption_id = ledger_update(
                        updated, domain, news, delivery, state["episode_id"]
                    )
                    adoption_ids.append(adoption_id)
            if updated != original:
                prefix = (
                    b"\xef\xbb\xbf"
                    if ledger_path.read_bytes().startswith(b"\xef\xbb\xbf")
                    else b""
                )
                _atomic_bytes(ledger_path, prefix + updated.encode("utf-8"))
            receipt = {
                "domain": domain,
                "delivery_id": delivery_id,
                "ledger_path": str(ledger_path.resolve()),
                "adoption_ids": adoption_ids,
            }
            if receipt not in state["adoption_receipts"]:
                state["adoption_receipts"].append(receipt)
                state["revision"] += 1
                atomic_json(path, state)
            return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-package")
    validate.add_argument("package")
    create = sub.add_parser("init")
    create.add_argument("episode")
    create.add_argument("--episode-id", required=True)
    create.add_argument("--request", required=True)
    create.add_argument("--package", action="append", required=True)
    create.add_argument("--confirmed-script")
    for name in ["verify", "draft", "stage", "deliver", "adopt", "fail"]:
        command = sub.add_parser(name)
        command.add_argument("episode")
        if name != "verify":
            command.add_argument("--revision", type=int, required=True)
        if name == "draft":
            command.add_argument(
                "--paragraphs",
                required=True,
                help="JSON list or object containing paragraphs",
            )
            command.add_argument("--output", required=True)
        elif name == "stage":
            command.add_argument("--name", choices=STAGE_DEPENDENCIES, required=True)
            command.add_argument("--input", action="append", default=[])
            command.add_argument("--output", action="append", required=True)
            command.add_argument("--evidence", action="append", required=True)
        elif name == "deliver":
            command.add_argument("--kind", choices=DELIVERY_KINDS, required=True)
            command.add_argument("--artifact", required=True)
            command.add_argument("--to", required=True)
            command.add_argument(
                "--at", required=True, help="ISO timestamp with timezone"
            )
            command.add_argument("--evidence", required=True)
        elif name == "adopt":
            command.add_argument("--domain", choices=["idc", "web3"], required=True)
            command.add_argument("--ledger", required=True)
            command.add_argument("--delivery-id", required=True)
            command.add_argument("--ledger-sha256")
        elif name == "fail":
            command.add_argument(
                "--name", choices=[*STAGE_DEPENDENCIES, "adoption"], required=True
            )
            command.add_argument("--reason", required=True)
            command.add_argument("--resume-from", required=True)
            command.add_argument("--input", action="append", default=[])
    args = parser.parse_args()
    if args.command == "validate-package":
        package = validate_package(read_json(args.package))
        result = {
            "package_id": package["package_id"],
            "valid_structure": True,
            "factual_review": "not_proven_by_schema",
        }
    elif args.command == "init":
        result = create_episode(
            args.episode,
            args.episode_id,
            args.request,
            args.package,
            args.confirmed_script,
        )
    elif args.command == "verify":
        result = verify_episode(read_json(args.episode))
    elif args.command == "draft":
        paragraphs = read_json(args.paragraphs)
        if isinstance(paragraphs, dict):
            paragraphs = paragraphs["paragraphs"]
        result = draft_episode(args.episode, args.revision, paragraphs, args.output)
    elif args.command == "stage":
        result = record_stage(
            args.episode,
            args.revision,
            args.name,
            args.output,
            args.evidence,
            args.input,
        )
    elif args.command == "deliver":
        result = record_delivery(
            args.episode,
            args.revision,
            args.kind,
            args.artifact,
            args.to,
            args.at,
            args.evidence,
        )
    elif args.command == "fail":
        result = record_failure(
            args.episode,
            args.revision,
            args.name,
            args.reason,
            args.resume_from,
            args.input,
        )
    else:
        result = commit_adoption(
            args.episode,
            args.revision,
            args.domain,
            args.ledger,
            args.delivery_id,
            args.ledger_sha256,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
