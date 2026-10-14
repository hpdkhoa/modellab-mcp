"""Model Lab's real-gun check, the render half: the build's side outline drawn exactly as a
reference photo shows the real gun. The camera looks at the gun's right side with the muzzle to the right, at the
photo's own scale (cm a pixel), the bore on the photo's bore row and the muzzle on its muzzle column. Black on white,
flat: an outline mask for ttools to measure against the photo's.

    blender -b <build>.blend -P modellab_compare.py -- <job.json>
job: {"facts": <facts.json>, "width": px, "height": px, "cm_per_px": s, "bore_row": px, "muzzle_col": px, "out": png}"""
import json
import sys

import bpy
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
facts = json.load(open(job["facts"], encoding="utf-8"))
W, H, S = int(job["width"]), int(job["height"]), float(job["cm_per_px"])
muzzle_y = facts["marks"]["muzzle"]["at"][1]
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == 'ARMATURE' and o.animation_data:
        o.animation_data.action = None
    if o.name.startswith("SM_"):
        o.hide_render = True
bpy.context.view_layer.update()
# the camera at the picture's middle: column W/2 is muzzle_y + (W/2 - muzzle_col) cm-pixels along the bore
yc = muzzle_y + (W / 2.0 - job["muzzle_col"]) * S
zc = (job["bore_row"] - H / 2.0) * S
cam = bpy.data.objects.get("cam") or bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = W * S / 100.0
cam.data.clip_start, cam.data.clip_end = 0.01, 10.0
# from the gun's right (Blender -X), looking toward +X; the picture's right is the gun's forward (Blender -Y)
r, u, f = Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
M = Matrix((r, u, -f)).transposed().to_4x4()
M.translation = Vector((-1.0, -yc / 100.0, zc / 100.0))
cam.matrix_world = M
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'FLAT'
sh.color_type = 'SINGLE'
sh.single_color = (0.0, 0.0, 0.0)
sh.show_cavity = False
sh.show_shadows = False
sh.show_specular_highlight = False
sh.show_object_outline = False
sh.background_type = 'WORLD'
sc.world = sc.world or bpy.data.worlds.new("w")
sc.world.color = (1.0, 1.0, 1.0)
sc.view_settings.view_transform = 'Standard'
sc.render.film_transparent = False
sc.display.render_aa = '8'
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.filepath = job["out"]
bpy.ops.render.render(write_still=True)
print("MODEL LAB COMPARE RENDER", job["out"])
