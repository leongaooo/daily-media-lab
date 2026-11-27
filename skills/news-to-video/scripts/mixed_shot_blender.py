"""Build beveled Blender blocks and project a route into the current camera."""

import math

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


def route_keys(obj, keyframes):
    """Set linear movement between cue-aligned frames and repeat the final pose to hold."""
    for frame, location in keyframes:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
