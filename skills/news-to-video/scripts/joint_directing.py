"""项目级联合导演：同一整帧事件驱动侧板、对象状态和引用锚点。

这里只实现本次洞室机制及 IDC 状态板两种消费者。摄影仍由 Blender 作者
读取事件并保存到源 blend；本模块不把计划存在冒称摄影已经执行。
"""

from copy import deepcopy
import math
from pathlib import Path
import re
import shutil

from frozen_audio import file_hash
from narrative_media import digest, read_json

FRAME_FORMAT = {"fps": 24, "width": 1920, "height": 1080}
KINDS = {"cavern-flex-v3", "idc-status-v3"}
STATUSES = {"future", "reported", "pending", "reference"}


def _integer(value):
    return type(value) is int


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value)


def _text(value, description):
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(f"Joint directing requires {description}")


def event_progress(event, frame):
    """区间末帧到达终态；后续帧保持，保证跳帧/随机访问仍可确定复现。"""
    first = event["start_frame"]
    last = event["end_frame"] - 1
    if frame < first:
        return 0.0
    if frame >= last:
        return 1.0
    return (frame - first) / (last - first)


def _smooth(progress):
    return progress * progress * (3 - 2 * progress)


def validate_plan(plan, total_frames):
    """只在项目输入边界收口，不静默补时间或猜测口播词级锚点。"""
    if plan.get("schema_version") != 1 or any(
        plan.get(key) != value for key, value in FRAME_FORMAT.items()
    ):
        raise ValueError("Joint directing requires schema 1, 1920x1080 at 24 fps")
    events = plan.get("events")
    _text(plan.get("projection"), "projection path")
    if not isinstance(events, dict) or not events:
        raise ValueError("Joint directing requires named events")
    for name, event in events.items():
        if not isinstance(event, dict) or not all(
            _integer(event.get(key)) for key in ("start_frame", "end_frame")
        ):
            raise ValueError(f"Event {name} requires integer global boundaries")
        if not 0 <= event["start_frame"] < event["end_frame"] <= total_frames:
            raise ValueError(f"Event {name} is outside the complete timeline")
    camera_events = plan.get("camera_events")
    if (
        not isinstance(camera_events, list)
        or not camera_events
        or any(
            not isinstance(name, str) or name not in events for name in camera_events
        )
        or len(set(camera_events)) != len(camera_events)
    ):
        raise ValueError(
            "Joint directing must name the events actually consumed by camera"
        )
    overlays = plan.get("overlays")
    if not isinstance(overlays, list) or not overlays:
        raise ValueError("Joint directing requires actual overlays")
    seen = set()
    for overlay in overlays:
        identifier = overlay.get("overlay_id")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identifier)
            or identifier in seen
        ):
            raise ValueError("Joint overlay_id must be unique and stable")
        seen.add(identifier)
        if overlay.get("kind") not in KINDS:
            raise ValueError("Unsupported project joint overlay kind")
        if (
            not all(_integer(overlay.get(key)) for key in ("start_frame", "end_frame"))
            or not 0 <= overlay["start_frame"] < overlay["end_frame"] <= total_frames
        ):
            raise ValueError("Joint overlay requires an in-range integer interval")
        panel = overlay.get("panel")
        if (
            not isinstance(panel, list)
            or len(panel) != 4
            or not all(_finite(value) for value in panel)
        ):
            raise ValueError("Joint panel requires [x,y,width,height]")
        x, y, width, height = panel
        if not (0 <= x and 100 <= y and width >= 800 and height >= 580):
            raise ValueError("Joint panel is too small or outside its readable area")
        if x + width > 1856 or y + height > 880:
            raise ValueError("Joint panel must stay above y904 caption protection")
        for key in ("title", "identity"):
            _text(overlay.get(key), f"overlay {key}")
        names = overlay.get("event_names", {})
        required = (
            ("panel", "prediction", "reschedule", "result")
            if overlay["kind"] == "cavern-flex-v3"
            else ("panel",)
        )
        if not isinstance(names, dict) or any(
            names.get(key) not in events for key in required
        ):
            raise ValueError(f"Joint overlay is missing event bindings: {required}")
        if overlay["kind"] == "cavern-flex-v3":
            if not all(word in overlay["identity"] for word in ("示意", "非实测")):
                raise ValueError(
                    "Hypothetical mechanism must remain visibly identified"
                )
            starts = [events[names[key]]["start_frame"] for key in required]
            if starts != sorted(starts):
                raise ValueError("Mechanism must establish, move, hold, then conclude")
            if (
                events[names["result"]]["start_frame"]
                < events[names["reschedule"]]["end_frame"]
            ):
                raise ValueError("Result hold cannot start before the task move ends")
            if "policy" in names and names["policy"] not in events:
                raise ValueError("Policy closure must reference an actual event")
            task = overlay.get("task", {})
            _text(task.get("id"), "one persistent task id")
            _text(task.get("label"), "task label")
            if not all(_finite(task.get(key)) for key in ("from", "to", "width")):
                raise ValueError("Task positions require finite normalized values")
            if not 0.15 <= task["width"] <= 0.35 or not all(
                0 <= task[key] <= 1 - task["width"] for key in ("from", "to")
            ):
                raise ValueError("Same task must retain width inside the schedule")
            caveats = overlay.get("caveats", [])
            if "policy" in names and len(caveats) != 2:
                raise ValueError("Policy closure requires two authored caveats")
            if "policy" not in names and caveats:
                raise ValueError("Excerpt caveats require a policy event")
            for caveat in caveats:
                _text(caveat.get("text"), "policy caveat")
                if caveat.get("event") not in events:
                    raise ValueError("Policy caveat must bind an actual event")
        else:
            cards = overlay.get("cards", [])
            if not isinstance(cards, list) or not 1 <= len(cards) <= 3:
                raise ValueError("IDC status board requires one to three cards")
            if overlay.get("reference") and len(cards) > 2:
                raise ValueError("IDC reference board has room for at most two cards")
            if overlay.get("reference") and len(cards) == 2 and height < 610:
                raise ValueError("IDC reference and two cards need a 610px high panel")
            for card in cards:
                for key in ("title", "detail"):
                    _text(card.get(key), f"IDC card {key}")
                if (
                    card.get("status") not in STATUSES
                    or card.get("event") not in events
                ):
                    raise ValueError("IDC card must bind an evidence status and event")
            if overlay.get("reference"):
                reference = overlay["reference"]
                _text(reference.get("path"), "product reference path")
                _text(reference.get("label"), "product reference label")
                if not _sha(reference.get("sha256")):
                    raise ValueError("Product reference requires a SHA256")
    for left, right in zip(
        sorted(overlays, key=lambda item: item["start_frame"]),
        sorted(overlays, key=lambda item: item["start_frame"])[1:],
    ):
        if left["end_frame"] > right["start_frame"]:
            raise ValueError("Project sideboards must not compete in the same frame")
    return plan


def validate_projection(projection, manifest, manifest_base, total_frames, plan):
    """源文件哈希拒绝旧机位投影；camera 哈希额外绑定作者的摄影采样身份。

    visible 仅是作者提供的几何可见标记，不是遮挡/专业细节验收证明。
    """
    if projection.get("schema_version") != 1 or any(
        projection.get(key) != value for key, value in FRAME_FORMAT.items()
    ):
        raise ValueError("Projection frame format does not match the narrative")
    projected = projection.get("shots")
    if not isinstance(projected, list) or len(projected) != len(manifest["shots"]):
        raise ValueError("Projection must cover every narrative shot")
    anchors = [None] * total_frames
    for shot, item in zip(manifest["shots"], projected):
        if item.get("shot_id") != shot["shot_id"]:
            raise ValueError("Projection shot order or identity mismatch")
        if (
            any(item.get(key) != shot[key] for key in ("start_frame", "end_frame"))
            or item.get("source_first_frame") != shot["media"]["source_first_frame"]
        ):
            raise ValueError("Projection global/local frame mapping mismatch")
        dependencies = shot.get("dependencies", [])
        if item.get("dependencies_sha256") != digest(dependencies) or any(
            file_hash(manifest_base / dependency["path"]) != dependency["sha256"]
            for dependency in dependencies
        ):
            raise ValueError("Projection scene dependencies are stale")
        if item.get("source_sha256") != shot["source"]["sha256"] or file_hash(
            manifest_base / shot["source"]["path"]
        ) != item.get("source_sha256"):
            raise ValueError(
                "Projection source checksum is stale after scene/camera change"
            )
        if (
            not _sha(shot.get("camera_sha256"))
            or item.get("camera_sha256") != shot["camera_sha256"]
        ):
            raise ValueError("Projection camera fingerprint mismatch")
        camera_names = shot.get("camera_event_names", plan["camera_events"])
        if (
            not isinstance(camera_names, list)
            or not camera_names
            or any(
                not isinstance(name, str) or name not in plan["events"]
                for name in camera_names
            )
        ):
            raise ValueError("Camera event bindings are missing or invalid")
        current_events = digest({name: plan["events"][name] for name in camera_names})
        if (
            item.get("camera_events_sha256") != current_events
            or shot.get("camera_events_sha256") != current_events
        ):
            raise ValueError(
                "Projection camera events are stale after approach timing change"
            )
        frames = item.get("frames")
        first, end = shot["start_frame"], shot["end_frame"]
        if not isinstance(frames, list) or len(frames) != end - first:
            raise ValueError("Projection is missing narrative frames")
        for expected, anchor in zip(range(first, end), frames):
            if (
                anchor.get("frame") != expected
                or not all(_finite(anchor.get(key)) for key in ("x", "y"))
                or type(anchor.get("visible")) is not bool
            ):
                raise ValueError(
                    "Projection requires continuous finite global frame anchors"
                )
            anchors[expected] = {
                "x": anchor["x"],
                "y": anchor["y"],
                "visible": anchor["visible"],
            }
    if any(anchor is None for anchor in anchors):
        raise ValueError("Projection does not cover the complete timeline")
    return anchors


def load_directing(project, base, manifest=None, total_frames=None):
    """加载并校验联合计划；保留 events 给摄影作者及独立声音解析器共用。"""
    if not project.get("narrative_directing"):
        return None
    base = Path(base)
    manifest_path = base / project["narrative_manifest"]
    manifest = manifest if manifest is not None else read_json(manifest_path)
    count = manifest["shots"][-1]["end_frame"]
    if total_frames is not None and count != total_frames:
        raise ValueError("Joint directing does not match the complete audio timeline")
    plan_path = base / project["narrative_directing"]
    plan = validate_plan(read_json(plan_path), count)
    projection_path = plan_path.parent / plan["projection"]
    projection = read_json(projection_path)
    validate_projection(projection, manifest, manifest_path.parent, count, plan)
    for overlay in plan["overlays"]:
        reference = overlay.get("reference")
        if (
            reference
            and file_hash(plan_path.parent / reference["path"]) != reference["sha256"]
        ):
            raise ValueError("Product reference checksum mismatch")
    return plan


def frame_state(plan, frame):
    """编译实际图形消费者所用状态；不另写各部门自己的秒数/延迟。"""
    result = []
    for overlay in plan["overlays"]:
        if not overlay["start_frame"] <= frame < overlay["end_frame"]:
            continue
        names = overlay["event_names"]
        progress = {
            key: event_progress(plan["events"][name], frame)
            for key, name in names.items()
        }
        state = {
            "overlay_id": overlay["overlay_id"],
            "panel_progress": _smooth(progress["panel"]),
        }
        if overlay["kind"] == "cavern-flex-v3":
            task = overlay["task"]
            task_progress = _smooth(progress["reschedule"])
            state.update(
                prediction_progress=progress["prediction"],
                task_id=task["id"],
                task_x=task["from"] + (task["to"] - task["from"]) * task_progress,
                task_progress=task_progress,
                result_visible=frame >= plan["events"][names["result"]]["start_frame"],
                policy_progress=_smooth(progress.get("policy", 0)),
                caveat_progress=[
                    _smooth(event_progress(plan["events"][item["event"]], frame))
                    for item in overlay.get("caveats", [])
                ],
            )
        else:
            state["card_progress"] = [
                _smooth(event_progress(plan["events"][item["event"]], frame))
                for item in overlay["cards"]
            ]
        result.append(state)
    return result


def compile_directing(plan, projection, total_frames):
    """独立图形缓存载荷；不改变 Blender 母版或源依赖清单。"""
    result = deepcopy(plan)
    result["projection_identity"] = digest(projection)
    result["plan_identity"] = digest(plan)
    anchors = [anchor for shot in projection["shots"] for anchor in shot["frames"]]
    result["frames"] = [
        {"anchor": anchors[frame], "overlays": frame_state(plan, frame)}
        for frame in range(total_frames)
    ]
    return result


def stage_directing(project, base, public, total_frames):
    """把已校验计划和精确参考字节交给 Remotion，身份加入合成缓存键。"""
    plan = load_directing(project, base, total_frames=total_frames)
    if plan is None:
        return None
    plan_path = Path(base) / project["narrative_directing"]
    projection = read_json(plan_path.parent / plan["projection"])
    payload = compile_directing(plan, projection, total_frames)
    for overlay in payload["overlays"]:
        reference = overlay.get("reference")
        if not reference:
            continue
        path = plan_path.parent / reference["path"]
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Joint product reference must be a supported raster image")
        # 完整内容哈希已经唯一标识素材；不再叠加长 overlay_id，避免 Windows
        # 深层项目路径超过传统路径长度限制。图板身份仍保留在编译载荷中。
        filename = f"joint-{reference['sha256']}{path.suffix.lower()}"
        target = Path(public) / "assets" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        reference["asset"] = "assets/" + filename
    return payload
