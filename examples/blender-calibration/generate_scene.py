"""生成原创静态校色卡源场景；默认不配音、不启动序列渲染。

色片为场景线性输入，经AgX显示变换成为PNG参考；这些数值不能当成
PNG应有的sRGB码值。往返核验应比较真实母版与最终编码抽帧。
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
FRAMES = 24


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def emission(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeEmission")
    shader.inputs[0].default_value = (*color, 1)
    shader.inputs[1].default_value = 1
    tree.links.new(shader.outputs[0], output.inputs["Surface"])
    return material


def pixel_to_world(camera, x, y):
    """使用正交相机实际view_frame推导像素坐标，不假设ortho_scale横纵含义。"""
    corners = camera.data.view_frame(scene=bpy.context.scene)
    minimum_x = min(corner.x for corner in corners)
    maximum_x = max(corner.x for corner in corners)
    minimum_y = min(corner.y for corner in corners)
    maximum_y = max(corner.y for corner in corners)
    return (
        minimum_x + x / WIDTH * (maximum_x - minimum_x),
        maximum_y - y / HEIGHT * (maximum_y - minimum_y),
        0,
    )


def patch(camera, patch_id, box, color):
    x0, y0, x1, y1 = box
    vertices = [
        pixel_to_world(camera, x, y)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    ]
    mesh = bpy.data.meshes.new(patch_id)
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(patch_id, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(emission(patch_id, color))
    for vertex in vertices:
        projected = world_to_camera_view(bpy.context.scene, camera, Vector(vertex))
        if projected.z <= 0 or (1 - projected.y) * HEIGHT >= 904:
            raise ValueError("Color patch extends into the caption protection rail")
    return {
        "patch_id": patch_id,
        "scene_linear_rgb": color,
        "pixel_box": box,
        "sample_box": [x0 + 24, y0 + 24, x1 - 24, y1 - 24],
        "sample_center": [(x0 + x1) // 2, (y0 + y1) // 2],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="生成产物目录；建议放仓库outputs或仓库外"
    )
    parser.add_argument("--preview", action="store_true")
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(arguments)
    output = Path(args.output).resolve()
    # 示例接受调用者指定的任意输出位置，但不覆盖已有源工程或回执。
    protected = ["calibration.blend", "shots.json", "patches.json", "preview.png"]
    existing = [name for name in protected if (output / name).exists()]
    if existing:
        raise ValueError(
            f"Output already contains generated artifacts; use a new directory: {existing}"
        )
    output.mkdir(parents=True, exist_ok=True)
    if bpy.app.version_string != "4.4.3":
        raise ValueError("This technical fixture is pinned to Blender 4.4.3")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
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
    world = bpy.data.worlds.new("Black calibration surround")
    world.use_nodes = True
    background = next(
        node for node in world.node_tree.nodes if node.type == "BACKGROUND"
    )
    background.inputs["Color"].default_value = (0, 0, 0, 1)
    background.inputs["Strength"].default_value = 0
    scene.world = world
    camera_data = bpy.data.cameras.new("Orthographic calibration camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 19.2
    camera_data.clip_start = 0.1
    camera_data.clip_end = 100
    camera = bpy.data.objects.new("Orthographic calibration camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0, 0, 20)
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera
    bpy.context.view_layer.update()
    patches = []
    gray_values = (0, 0.001, 0.003, 0.01, 0.03, 0.09, 0.18, 0.4, 0.7, 1)
    for index, level in enumerate(gray_values):
        x0 = 127 + index * 168
        patches.append(
            patch(camera, f"gray-{index:02}", [x0, 180, x0 + 154, 390], [level] * 3)
        )
    colors = {
        "red": [1, 0, 0],
        "green": [0, 1, 0],
        "blue": [0, 0, 1],
        "cyan": [0, 1, 1],
        "amber": [1, 0.35, 0],
        "white": [1, 1, 1],
    }
    for index, (name, color) in enumerate(colors.items()):
        x0 = 149 + index * 274
        patches.append(patch(camera, name, [x0, 500, x0 + 252, 740], color))
    scene["fixture_identity"] = "original-static-color-calibration-v1"
    scene["facts_boundary"] = "原创技术校色卡，无新闻/人声/性能主张；非显示器物理校准。"
    scene["subtitle_protected_y"] = 904
    scene.frame_set(1)
    source = output / "calibration.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    shot = {
        "shot_id": "calibration-card",
        "story_world": "technical-color-fixture",
        "start_frame": 0,
        "end_frame": FRAMES,
        "source": {"path": source.name, "sha256": sha(source)},
        "dependencies": [],
        "render": {
            "blender_version": bpy.app.version_string,
            "engine": "BLENDER_EEVEE_NEXT",
            "seed": 0,
            "samples": 32,
            "denoise": False,
            "width": WIDTH,
            "height": HEIGHT,
            "fps": 24,
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
            "label": "原创技术校色卡 · 非新闻场景",
            "evidence_ids": ["calibration-original-fixture-v1"],
            "prohibited_implications": [
                "不代表显示器物理校准",
                "不表示AgX变换后码值等于场景线性RGB",
            ],
        },
        "receipt": "receipts/calibration-card.json",
    }
    write_json(output / "shots.json", {"schema_version": 1, "fps": 24, "shots": [shot]})
    write_json(
        output / "patches.json",
        {
            "fixture_id": "calibration-original-fixture-v1",
            "license": "MIT",
            "author": "Original procedural geometry distributed by Daily Media Lab",
            "width": WIDTH,
            "height": HEIGHT,
            "frames": FRAMES,
            "inputs": "scene-linear emission colors; AgX is applied once by Blender",
            "comparison": "Compare decoded final-video patches against the actual PNG master, not against these scene-linear inputs",
            "patches": patches,
        },
    )
    if args.preview:
        scene.render.filepath = str(output / "preview.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
