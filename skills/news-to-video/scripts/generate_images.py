"""Prepare/cache per-scene Images API assets. No network without --generate."""

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

MAX_BYTES = 64 * 1024 * 1024


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError(
            "Redirect refused; credentials stay at the configured endpoint"
        )


def decode_image(data):
    rows = data.get("data")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("Expected exactly one image; no automatic retry")
    encoded = rows[0].get("b64_json")
    if not isinstance(encoded, str):
        raise ValueError(
            "Expected b64_json; URL-only response needs a separately verified download adapter"
        )
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > MAX_BYTES:
        raise ValueError("Image exceeds limit")
    with Image.open(io.BytesIO(raw)) as im:
        if (
            im.format not in ("PNG", "JPEG", "WEBP")
            or max(im.size) > 8192
            or im.width * im.height > 32_000_000
        ):
            raise ValueError("Unsupported image or dimensions")
        im.verify()
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        return im.convert("RGBA" if "A" in im.getbands() else "RGB")


def jobs_for(project, connection):
    parsed = urllib.parse.urlsplit(connection["base_url"])
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "base_url must be an explicit HTTPS API base, without credentials/query/fragment"
        )
    if connection.get("api_mode") != "images":
        raise ValueError("This adapter supports Images API only; no protocol fallback")
    model = connection.get("image_model", "gpt-image-2")
    endpoint = connection["base_url"].rstrip("/") + "/images/generations"
    jobs = []
    for index, scene in enumerate(project["scenes"]):
        spec = scene.get("image_generation")
        if not spec or spec.get("enabled", True) is False:
            continue
        role = spec.get("role")
        if role not in ("background", "subject"):
            raise ValueError("Image role must be background or subject")
        asset_id = spec.get("asset_id", f"scene-{index+1:02d}-{role}")
        if not isinstance(asset_id, str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,80}", asset_id
        ):
            raise ValueError("asset_id must be a simple identifier")
        prompt = spec.get("prompt", scene.get("image_prompt", ""))
        if not isinstance(prompt, str) or not prompt.strip() or prompt == "无需生成":
            raise ValueError("Enabled generation needs a deliberate prompt")
        size = spec.get("size", "1536x1024")
        if size not in ("1024x1024", "1024x1536", "1536x1024"):
            raise ValueError("Use a verified size: 1024x1024, 1024x1536, 1536x1024")
        quality = spec.get("quality", "medium")
        if quality not in ("low", "medium", "high", "auto"):
            raise ValueError("Invalid quality")
        payload = dict(model=model, prompt=prompt, size=size, quality=quality, n=1)
        fingerprint = hashlib.sha256(
            json.dumps([endpoint, payload], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        jobs.append(
            dict(
                scene=index,
                role=role,
                asset_id=asset_id,
                payload=payload,
                endpoint=endpoint,
                fingerprint=fingerprint,
            )
        )
    if len({j["asset_id"] for j in jobs}) != len(jobs):
        raise ValueError("asset_id must be unique in a project")
    return jobs


def apply_assets(project, base, jobs, folder):
    # Materialized project remains relocatable with its assets; existing local paths become absolute.
    result = json.loads(json.dumps(project))
    for scene in result["scenes"]:
        for field in ("image", "background_image"):
            if scene.get(field):
                scene[field] = str((base / scene[field]).resolve())
    if result.get("presenter", {}).get("image"):
        result["presenter"]["image"] = str(
            (base / result["presenter"]["image"]).resolve()
        )
    for job in jobs:
        scene = result["scenes"][job["scene"]]
        path = folder / job["filename"]
        if job["role"] == "background":
            scene["background_image"] = str(path.resolve())
        else:
            scene.update(
                mode="product_image",
                image=str(path.resolve()),
                editorial_image_fit="contain",
            )
        scene["image_generation"]["resolved_sha256"] = sha_file(path)
    return result


def run(args):
    project_path = Path(args.project).resolve()
    project = read_json(project_path)
    if "visual_selection_version" in project:
        from score_visuals import assess

        selection_report = assess(project)
        selection_folder = Path(args.output).resolve()
        selection_folder.mkdir(parents=True, exist_ok=True)
        (selection_folder / "visual-selection-report.json").write_text(
            json.dumps(selection_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if selection_report["errors"]:
            raise ValueError(
                "Visual selection preflight failed; see visual-selection-report.json"
            )
    conn = read_json(args.connection)
    jobs = jobs_for(project, conn)
    folder = Path(args.output).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    pending = []
    for job in jobs:
        job["filename"] = f"{job['asset_id']}-{job['fingerprint'][:12]}.png"
        image = folder / job["filename"]
        record = image.with_suffix(".json")
        cached = False
        if image.is_file() and record.is_file():
            info = read_json(record)
            cached = info.get("fingerprint") == job["fingerprint"] and info.get(
                "sha256"
            ) == sha_file(image)
        job["cache_hit"] = cached
        if not cached:
            pending.append(job)
    if args.max_new_images < 0 or len(pending) > args.max_new_images:
        raise ValueError(
            f"{len(pending)} new images exceed --max-new-images={args.max_new_images}"
        )
    report = dict(
        stage="generate" if args.generate else "plan-only",
        api_requests=0,
        automatic_retries=0,
        jobs=jobs,
        completed=False,
    )
    save_json(folder / "generation-report.json", report)
    if not args.generate:
        print(
            json.dumps(
                dict(
                    stage="plan-only",
                    images=len(jobs),
                    cached=len(jobs) - len(pending),
                    pending=len(pending),
                    api_requests=0,
                ),
                ensure_ascii=False,
            )
        )
        return 0
    key = ""
    if pending:
        if not args.credentials:
            raise ValueError("--credentials is required for new generation")
        key = read_json(args.credentials).get("api_key", "")
        if not isinstance(key, str) or not key.strip() or any(c.isspace() for c in key):
            raise ValueError("Invalid api_key")
    try:
        for job in pending:
            # An interrupted or failed submission is not automatically resubmitted on rerun.
            marker = folder / (job["filename"] + ".submitted.json")
            if marker.exists():
                raise ValueError(
                    "Prior unresolved submission exists; inspect provider task/billing before manual reset"
                )
            save_json(
                marker,
                dict(fingerprint=job["fingerprint"], status="submitted-or-unconfirmed"),
            )
            request = urllib.request.Request(
                job["endpoint"],
                data=json.dumps(job["payload"]).encode(),
                headers={
                    "Authorization": "Bearer " + key,
                    "Content-Type": "application/json",
                    "User-Agent": "news-to-video-images/1.0",
                },
                method="POST",
            )
            report["api_requests"] += 1
            save_json(folder / "generation-report.json", report)
            print(f"Generating {job['asset_id']} (one request, no retry)", flush=True)
            with urllib.request.build_opener(NoRedirect).open(
                request, timeout=240
            ) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError("Response exceeds limit")
                im = decode_image(json.loads(raw))
            image = folder / job["filename"]
            temp = image.with_suffix(".partial.png")
            im.save(temp, format="PNG")
            temp.replace(image)
            save_json(
                image.with_suffix(".json"),
                dict(
                    kind="generated_image",
                    fingerprint=job["fingerprint"],
                    sha256=sha_file(image),
                    endpoint=job["endpoint"],
                    model=job["payload"]["model"],
                    prompt=job["payload"]["prompt"],
                    requested_size=job["payload"]["size"],
                    dimensions=list(im.size),
                    size_matches_request=(
                        list(im.size)
                        == [int(n) for n in job["payload"]["size"].split("x")]
                    ),
                    role=job["role"],
                    scene=job["scene"],
                    reviewed=False,
                    disclosure="原创生成示意，非现场照片",
                ),
            )
            marker.unlink()
        resolved = apply_assets(project, project_path.parent, jobs, folder)
        save_json(folder / "resolved-project.json", resolved)
        report.update(
            completed=True, resolved_project=str(folder / "resolved-project.json")
        )
        save_json(folder / "generation-report.json", report)
        print(
            json.dumps(
                dict(
                    completed=True,
                    api_requests=report["api_requests"],
                    resolved_project=report["resolved_project"],
                ),
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        message = f"{type(exc).__name__}: request failed or unconfirmed"
        if isinstance(exc, urllib.error.HTTPError):
            message = f"HTTP {exc.code}"
            try:
                details = json.loads(exc.read(16000)).get("error", {})
                if isinstance(details, dict) and isinstance(
                    details.get("message"), str
                ):
                    message += ": " + details["message"][:800]
            except Exception:
                pass
        elif isinstance(exc, ValueError):
            message = str(exc)
        report["error"] = message.replace(key, "[REDACTED]") if key else message
        save_json(folder / "generation-report.json", report)
        print(report["error"], flush=True)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--connection", required=True)
    parser.add_argument("--credentials")
    parser.add_argument("--output", required=True)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--max-new-images", type=int, default=3)
    try:
        raise SystemExit(run(parser.parse_args()))
    except (ValueError, KeyError, OSError) as exc:
        # Configuration errors never need a traceback or credential value.
        print("Configuration error: " + type(exc).__name__)
        raise SystemExit(2)
