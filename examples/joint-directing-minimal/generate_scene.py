"""生成24帧联合消费测试源与投影；不渲染、不配音、不读取图片或凭据。

左侧原创几何只是可追踪占位物，不是服务器、产品或观赏质量样板。
相机读取同一directing.json的approach事件；二维板面由正式消费者绘制。
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

WIDTH = 1920
HEIGHT = 1080
FPS = 24
FRAMES = 24
SHOT_ID = "joint-technical-object"


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def digest(value):
    """与narrative_media.digest采用相同JSON内容摘要，不依赖作者机器路径。"""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def material(name, color, metallic=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.45
    shader.inputs["Metallic"].default_value = metallic
    return result


def add_placeholder():
    """保留明显的几何原语身份，不用抽象箱体假装专业设备。"""
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=1.25, location=(-3.2, 0.5, 0)
    )
    subject = bpy.context.object
    subject.name = "Original technical icosahedron - not a server"
    subject.data.materials.append(material("Muted teal geometry", (0.07, 0.32, 0.35)))
    subject.rotation_euler = (0.2, 0.35, 0.15)
    # 小球提供稳定锚点；它不是电源灯、运行状态或真实设备连接口。
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24, ring_count=12, radius=0.16, location=(-1.95, 0.48, 0.65)
    )
    marker = bpy.context.object
    marker.name = "Editorial reference marker - no operating status"
    marker.data.materials.append(material("Reference amber", (0.65, 0.3, 0.07)))
    return subject, marker


def configure_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.fps_base = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.frame_start = 1
    scene.frame_end = FRAMES
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    world = bpy.data.worlds.new("Original technical surround")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.075, 0.09, 1)
    background.inputs["Strength"].default_value = 0.4
    scene.world = world

    light_data = bpy.data.lights.new("Fixed soft area light", "AREA")
    light_data.energy = 900
    light_data.shape = "DISK"
    light_data.size = 6
    light = bpy.data.objects.new("Fixed soft area light", light_data)
    scene.collection.objects.link(light)
    light.location = (-3, 4, 9)
    light.rotation_euler = (
        (Vector((-3.2, 0.5, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()
    )

    camera_data = bpy.data.cameras.new("Shared event camera")
    camera_data.lens = 50
    camera_data.sensor_width = 36
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100
    camera = bpy.data.objects.new("Shared event camera", camera_data)
    scene.collection.objects.link(camera)
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera
    return scene, camera


def animate_camera(camera, plan):
    """把全局零起点事件转换一次到Blender局部1起点；不另猜摄影秒数。"""
    if plan.get("camera_events") != ["approach"]:
        raise ValueError("This fixture only authors the approach camera event")
    event = plan["events"]["approach"]
    start, end = event["start_frame"], event["end_frame"]
    if not 0 <= start < end <= FRAMES:
        raise ValueError("Approach event must fit the 24-frame technical fixture")
    # 每个整数帧都取同一事件的线性位置，结束后停留；无需依赖Action内部曲线API。
    # 这些密集关键帧只是短技术测试的确定性采样，不是正式影片的摄影风格建议。
    for frame in range(FRAMES):
        progress = min(1.0, max(0.0, (frame - start) / max(1, end - start - 1)))
        camera.location = (0, 0, 20.0 - 2.0 * progress)
        camera.keyframe_insert(data_path="location", frame=frame + 1)


def projection_samples(scene, camera, subject, marker):
    """导出实际摄影采样与标记投影；可见标记只作几何判断，不作遮挡保证。"""
    anchors = []
    samples = []
    for frame in range(FRAMES):
        scene.frame_set(frame + 1)
        bpy.context.view_layer.update()
        point = world_to_camera_view(scene, camera, marker.matrix_world.translation)
        x, y = point.x * WIDTH, (1 - point.y) * HEIGHT
        visible = point.z > 0 and 64 <= x < 880 and 100 <= y < 880
        if not visible:
            raise ValueError(f"Reference marker leaves its reserved area at {frame}")
        # 主体全程留左，板面／字幕完整保留；不缩放完整镜头来补布局。
        for corner in subject.bound_box:
            projected = world_to_camera_view(
                scene, camera, subject.matrix_world @ Vector(corner)
            )
            pixel_x = projected.x * WIDTH
            pixel_y = (1 - projected.y) * HEIGHT
            if projected.z <= 0 or not (64 <= pixel_x < 850 and 100 <= pixel_y < 880):
                raise ValueError(
                    f"Placeholder geometry leaves its reserved area at {frame}"
                )
        anchors.append({"frame": frame, "x": x, "y": y, "visible": visible})
        samples.append(
            {
                "frame": frame,
                "matrix_world": [
                    [round(float(value), 9) for value in row]
                    for row in camera.matrix_world
                ],
                "lens": camera.data.lens,
                "sensor_width": camera.data.sensor_width,
                "sensor_fit": camera.data.sensor_fit,
                "shift_x": camera.data.shift_x,
                "shift_y": camera.data.shift_y,
            }
        )
    return anchors, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="新的空产物目录；不写入样例源目录"
    )
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(arguments)
    example = Path(__file__).resolve().parent
    output = Path(args.output).resolve()
    if output == example or example in output.parents:
        raise ValueError("Keep generated media outside the example source directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Use a new empty output directory; existing artifacts are protected"
        )
    if bpy.app.version_string != "4.4.3":
        raise ValueError("This technical fixture is pinned to Blender 4.4.3")
    plan = json.loads((example / "directing.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)

    scene, camera = configure_scene()
    subject, marker = add_placeholder()
    animate_camera(camera, plan)
    anchors, camera_samples = projection_samples(scene, camera, subject, marker)
    camera_hash = digest(
        {"width": WIDTH, "height": HEIGHT, "fps": FPS, "samples": camera_samples}
    )
    event_hash = digest({name: plan["events"][name] for name in plan["camera_events"]})
    scene["fixture_identity"] = "original-joint-consumer-technical-v1"
    scene["facts_boundary"] = (
        "原创占位几何与假设排程；非服务器、非新闻、非运行或性能证据。"
    )
    scene["camera_events_sha256"] = event_hash
    scene["subtitle_protected_y"] = 904
    scene.frame_set(1)
    source = output / "joint-technical.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    source_hash = file_hash(source)
    shot = {
        "shot_id": SHOT_ID,
        "story_world": "original-joint-consumer-fixture",
        "start_frame": 0,
        "end_frame": FRAMES,
        "source": {"path": source.name, "sha256": source_hash},
        "dependencies": [],
        "camera_sha256": camera_hash,
        "camera_event_names": plan["camera_events"],
        "camera_events_sha256": event_hash,
        "render": {
            "blender_version": bpy.app.version_string,
            "engine": "BLENDER_EEVEE_NEXT",
            "seed": 0,
            "samples": 16,
            "denoise": False,
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "display_transform": "AgX",
            "look": "AgX - Medium High Contrast",
            "exposure": 0,
            "gamma": 1,
        },
        "media": {
            "role": "master",
            "pattern": "frames/%06d.png",
            "source_first_frame": 1,
            "bit_depth": 8,
            "color_space": "display-srgb",
            "alpha": "opaque",
        },
        "handles": {"head": 0, "tail": 0},
        "facts": {
            "kind": "explanation",
            "label": "技术测试 · 占位几何 · 非服务器",
            "evidence_ids": ["original-joint-consumer-fixture-v1"],
            "prohibited_implications": [
                "不是服务器、产品复原或新闻现场",
                "不证明实际调度、供电或性能",
                "一秒静音不能证明观看节奏、口播或听感",
            ],
        },
        "receipt": "receipts/joint-technical-object.json",
    }
    projected_shot = {
        "shot_id": SHOT_ID,
        "source_sha256": source_hash,
        "camera_sha256": camera_hash,
        "camera_events_sha256": event_hash,
        "start_frame": 0,
        "end_frame": FRAMES,
        "source_first_frame": 1,
        "dependencies_sha256": digest(shot["dependencies"]),
        "frames": anchors,
    }
    write_json(output / "directing.json", plan)
    write_json(
        output / "shots.json", {"schema_version": 1, "fps": FPS, "shots": [shot]}
    )
    write_json(
        output / "projection.json",
        {
            "schema_version": 1,
            "fps": FPS,
            "width": WIDTH,
            "height": HEIGHT,
            "shots": [projected_shot],
        },
    )
    write_json(
        output / "camera-samples.json",
        {"camera_sha256": camera_hash, "samples": camera_samples},
    )
    print(
        "Saved original technical scene and actual camera projections; rendering not started."
    )


if __name__ == "__main__":
    main()
