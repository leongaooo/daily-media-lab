"""Build a small editable Blender scene for the three data halls."""

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mixed_shot_blender import arrow, block, route_keys, screen_point

GROUND = (0.19, 0.29, 0.33)
DARK = (0.08, 0.14, 0.18)
ROUTE = (0.20, 0.90, 0.67)
WALL = (0.65, 0.77, 0.75)
METAL = (0.34, 0.55, 0.57)


def data_hall(x, number):
    block(f"Hall {number} slab", (x, 1.8, 0.14), (4.9, 4.6, 0.28), METAL)
    block(f"Hall {number} side wall", (x - 2.33, 2.0, 0.81), (0.20, 4.3, 1.2), WALL)
    block(f"Hall {number} back wall", (x, 4.05, 0.81), (4.9, 0.22, 1.2), WALL)
    for dx in (-1.44, 0, 1.44):
        for y in (1.38, 2.73):
            block(
                "Generic equipment enclosure",
                (x + dx, y, 0.90),
                (0.79, 0.91, 1.26),
                DARK,
            )
            block(
                "Enclosure highlight",
                (x + dx, y - 0.466, 1.22),
                (0.59, 0.05, 0.10),
                METAL,
            )
    block("Data hall entrance", (x, -0.55, 0.13), (2.1, 0.43, 0.16), ROUTE)


def main():
    job = Path(sys.argv[sys.argv.index("--") + 1])
    cues = json.loads((job / "timing.json").read_text(encoding="utf-8"))["boundaries"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    block("Shared facility base", (0, 0, -0.27), (19.8, 10.5, 0.50), GROUND, 0.20)
    hall_positions = (-5.6, 0.0, 5.6)
    for number, x in enumerate(hall_positions, 1):
        data_hall(x, number)

    # Wayfinding marks describe the viewer's walkthrough in this conceptual layout.
    for x in (-7, -5.9, -4.8, -3.4, -2.25, -1.10, 0, 1.10, 2.25, 3.40, 4.50, 5.60):
        arrow("Walkthrough direction", x, -2.45, 0, ROUTE)
    for x in hall_positions:
        arrow("Hall access", x, -1.30, 1.5707963, ROUTE)
    marker = block(
        "Animated viewpoint marker", (-7.9, -2.45, 0.18), (0.47, 0.47, 0.30), ROUTE
    )
    travel = cues[7] - cues[6]
    total = cues[8] - cues[6]
    route_keys(
        marker,
        [
            (1, (-7.9, -2.45, 0.18)),
            (round(travel * 0.25), (-5.6, -2.45, 0.18)),
            (round(travel * 0.53), (0, -2.45, 0.18)),
            (round(travel * 0.85), (5.6, -2.45, 0.18)),
            (travel + 1, (5.6, -0.90, 0.18)),
            (total, (5.6, -0.90, 0.18)),
        ],
    )

    scene = bpy.context.scene
    bpy.ops.object.camera_add(location=(3.8, -13.2, 15.8))
    camera = bpy.context.object
    aim = Vector((0, 0, 0.35)) - camera.location
    camera.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 28.7
    camera.data.shift_y = -0.025
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
    scene.world.color = (0.018, 0.035, 0.046)
    scene.frame_end = total
    scene.frame_set(1)
    projection = {
        "halls": [screen_point(scene, x, 3.5, 1.55) for x in hall_positions],
        "turn_frame": round(travel * 0.85),
        "arrival_frame": travel,
    }
    (job / "projection.json").write_text(
        json.dumps(projection, indent=2), encoding="utf-8"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(job / "source/kajaani.blend"))
    (job / "raw3d").mkdir(exist_ok=True)
    scene.render.filepath = (job / "raw3d").as_posix() + "/"
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
