"""Orbit: a chrome sphere inside three spinning neon rings, with an orbiting camera.

This script only BUILDS the scene. local-render's driver sets resolution, fps,
frame range and the render engine from render.json, then renders.
Motion uses driver expressions of `frame`, so it works in every Blender 4.2+ / 5.x
without touching the keyframe API.
"""
import math

import bpy

FRAMES = globals().get("LR_FRAMES", 96)
TAU = math.tau

# ---- clean slate
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene


def material(name, color, metallic=0.0, roughness=0.4, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        bsdf.inputs[key].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


def drive(obj, path, index, expr):
    fc = obj.driver_add(path, index)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr  # simple expressions run without Python auto-exec


def srgb(hexstr):
    c = [int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


LIME, CORAL, ICE, INK = srgb("c6ff3d"), srgb("ff5c39"), srgb("9fb6ff"), srgb("0b0d17")

# ---- world
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (*srgb("1a2150"), 1)
bg.inputs["Strength"].default_value = 1.2

# ---- floor
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -2.9))
bpy.context.object.data.materials.append(material("Floor", INK, metallic=0.2, roughness=0.18))

# ---- chrome sphere, gently bobbing
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=96, ring_count=48, location=(0, 0, 0))
sphere = bpy.context.object
bpy.ops.object.shade_smooth()
sphere.data.materials.append(material("Chrome", (0.9, 0.9, 0.95), metallic=1.0, roughness=0.08))
drive(sphere, "location", 2, "0.12*sin(frame*%.6f)" % (TAU / FRAMES * 2))

# ---- neon rings
rings = [(1.55, 0.03, LIME, 1.0, 0), (1.95, 0.04, CORAL, -1.0, 1), (2.4, 0.028, ICE, 0.5, 2)]
for i, (radius, thick, color, turns, axis) in enumerate(rings):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thick, major_segments=192, minor_segments=24)
    ring = bpy.context.object
    bpy.ops.object.shade_smooth()
    ring.data.materials.append(material("Ring%d" % i, color, emission=color, strength=3.5))
    ring.rotation_euler = (math.radians(60 + i * 25), math.radians(i * 35), 0)
    # each ring spins a whole number of turns over the clip, so the video loops seamlessly
    drive(ring, "rotation_euler", axis, "%.4f + frame*%.6f" % (ring.rotation_euler[axis], TAU * turns / FRAMES))

# ---- lights
bpy.ops.object.light_add(type="AREA", location=(4, -3, 5))
key = bpy.context.object
key.data.energy, key.data.size = 600, 6
key.rotation_euler = (math.radians(45), 0, math.radians(50))
bpy.ops.object.light_add(type="AREA", location=(-5, 4, 2))
rim = bpy.context.object
rim.data.energy, rim.data.size, rim.data.color = 500, 3, ICE
rim.rotation_euler = (math.radians(70), 0, math.radians(-130))

# ---- camera on an orbiting rig (a quarter turn over the clip)
bpy.ops.object.empty_add(location=(0, 0, 0))
rig = bpy.context.object
drive(rig, "rotation_euler", 2, "frame*%.6f" % (TAU * 0.25 / FRAMES))
bpy.ops.object.camera_add(location=(0, -10.5, 2.4))
cam = bpy.context.object
cam.data.lens = 45
cam.parent = rig
track = cam.constraints.new("TRACK_TO")
track.target = sphere
track.track_axis, track.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
cam.data.dof.use_dof = True
cam.data.dof.focus_object = sphere
cam.data.dof.aperture_fstop = 2.8
scene.camera = cam

# ---- look
for attr, value in (("view_transform", "AgX"), ("look", "AgX - Punchy")):
    try:
        setattr(scene.view_settings, attr, value)
    except TypeError:
        pass
try:
    scene.eevee.use_raytracing = True  # screen-space reflections on the floor (Eevee 4.2+)
except AttributeError:
    pass
