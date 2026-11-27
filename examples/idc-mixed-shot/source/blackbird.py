"""Create the editable Blackbird route illustration from the frozen cue window."""

import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def block(name, location, size, color, bevel=0.06, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.color = (*color, 1)
    if bevel:
        modifier = obj.modifiers.new("Machined edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    obj.parent = parent
    return obj


def arrow(name, x, y, heading, color):
    points = [(0.38, 0), (-0.30, 0.25), (-0.13, 0), (-0.30, -0.25)]
    cosine, sine = math.cos(heading), math.sin(heading)
    vertices = [
        (x + a * cosine - b * sine, y + a * sine + b * cosine, 0.065) for a, b in points
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.color = (*color, 1)


def screen_point(scene, x, y, z):
    point = world_to_camera_view(scene, scene.camera, Vector((x, y, z)))
    return [round(point.x * 1920), round((1 - point.y) * 1080)]


def main():
    job = Path(sys.argv[sys.argv.index("--") + 1])
    timing = json.loads((job / "timing.json").read_text(encoding="utf-8"))
    cues = timing["boundaries"]
    bpy.ops.wm.read_factory_settings(use_empty=True)

    ground = (0.20, 0.26, 0.30)
    dark = (0.09, 0.14, 0.19)
    metal = (0.44, 0.52, 0.55)
    ivory = (0.78, 0.81, 0.75)
    route = (0.18, 0.96, 0.79)
    amber = (0.99, 0.62, 0.24)

    block("Site", (0, 0, -0.37), (18, 12, 0.72), ground, 0.25)
    block("Entrance pad", (-6.1, -2.4, 0), (3.7, 2.9, 0.08), dark)
    block("Receiving platform", (3, 4.12, 0.09), (3.4, 2.65, 0.22), metal)
    block("Receiving position", (3, 4.0, 0.21), (2.66, 1.73, 0.045), dark)

    for x in (1.54, 4.46):
        for y in (3.1, 5.18):
            block("Receiving marker", (x, y, 0.23), (0.23, 0.28, 0.08), route)
    for x in (-3.8, -2.5, -1.2, 0.1, 1.4, 2.5):
        arrow("Approach direction", x, -2.4, 0, route)
    for y in (-1.3, -0.25, 0.85, 1.95, 2.88):
        arrow("Turn toward platform", 3, y, math.pi / 2, route)
    for x, y in ((-7, -4), (-5, -4), (-3, -4), (5, -2), (5, 0), (5, 2)):
        block("Route boundary", (x, y, 0.20), (0.17, 0.17, 0.40), amber)

    # The module and its carrier share a route controller to preserve object identity
    # as the module turns and arrives. The route marks remain fixed to the floor.
    module = bpy.data.objects.new("Compute module rig", None)
    bpy.context.collection.objects.link(module)
    block("Carrier", (0, 0, 0.34), (2.8, 1.68, 0.26), dark, parent=module)
    block("Module body", (0, 0, 0.93), (2.54, 1.48, 1.03), ivory, parent=module)
    block("Module roof", (0, 0, 1.51), (2.58, 1.51, 0.10), metal, parent=module)
    for x in (-1.02, -0.52, -0.02, 0.48, 0.98):
        block("Vent", (x, -0.752, 1.01), (0.26, 0.04, 0.51), dark, 0.025, module)
        block("Side rib", (x, 0.75, 1.0), (0.08, 0.055, 0.89), metal, 0.02, module)
    for x in (-0.9, 0.9):
        for y in (-0.76, 0.76):
            block("Carrier wheel", (x, y, 0.19), (0.43, 0.25, 0.36), dark, 0.1, module)
    block("Identity stripe", (1.277, 0, 1.20), (0.05, 1.12, 0.15), amber, 0.012, module)

    travel = cues[7] - cues[6]
    total = cues[8] - cues[6]
    trajectory = [
        (1, (-6.20, -2.40, 0), 0),
        (round(travel * 0.52), (2.38, -2.40, 0), 0),
        (round(travel * 0.66), (3.00, -1.78, 0), math.pi / 2),
        (travel + 1, (3.00, 4.00, 0.19), math.pi / 2),
        (total, (3.00, 4.00, 0.19), math.pi / 2),
    ]
    for frame, location, heading in trajectory:
        module.location = location
        module.rotation_euler.z = heading
        module.keyframe_insert(data_path="location", frame=frame)
        module.keyframe_insert(data_path="rotation_euler", frame=frame)
    for curve in module.animation_data.action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"

    scene = bpy.context.scene
    bpy.ops.object.camera_add(location=(9.6, -15.2, 16.4))
    camera = bpy.context.object
    camera.rotation_euler = (
        (Vector((0.0, 0.0, 0.1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 27.0
    camera.data.shift_y = -0.041
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 12
    scene.display.render_aa = "8"
    scene.view_settings.view_transform = "Standard"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.studio_light = "paint.sl"
    shading.color_type = "OBJECT"
    shading.background_type = "WORLD"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_specular_highlight = True
    scene.world = bpy.data.worlds.new("Slate studio")
    scene.world.color = (0.015, 0.027, 0.04)
    scene.frame_end = total
    scene.frame_set(1)

    positions = {
        "entrance": screen_point(scene, -6.1, -2.4, 0),
        "turn": screen_point(scene, 3, -2.4, 0),
        "receiving": screen_point(scene, 3, 4.12, 0.22),
        "turn_frame": round(travel * 0.66) - 1,
        "arrival_frame": travel,
    }
    (job / "projection.json").write_text(
        json.dumps(positions, indent=2), encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(job / "source" / "blackbird.blend"))
    (job / "raw3d").mkdir(exist_ok=True)
    if "--still" in sys.argv:
        scene.render.filepath = str(job / "review" / "3d-look.png")
        bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath = (job / "raw3d").as_posix() + "/"
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
