"""Model Lab's build, in Blender: a gun from a platform and its parameters. It builds the
parts, checks them against the facts (lengths, the port and its cover, the magazine in its well, the bolt's travel,
the sight line), rigs one bone a moving part, renders the rest and open poses, and writes SK_<name>_Rig.fbx,
SM_<name>_Magazine.fbx (its origin on the feed lips, for the hand), <name>.blend and facts.json. Writes only under
the job's out folder.

    blender -b --factory-startup -P modellab_blender.py -- <job.json>

job: {"platform": "ar15", "name": "M4A1", "params": {...}, "targets": {"oal_cm": {"0": 75.57, "4": 83.82}},
      "scale": 1.0, "out": folder, "tools": <a folder with finish_util, optional>}"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
if job.get("tools"):
    sys.path.insert(0, job["tools"])
import modellab_parts as K  # noqa: E402

PLATFORMS = {"ar15": "modellab_ar15"}
plat = __import__(PLATFORMS[job["platform"]])
OUT = job["out"]
NAME = job["name"]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.scale_length = 1.0
kit = K.Kit(plat.materials(job.get("params", {})))   # the material slots, coloured from the finish parameters
bones, marks, moving, m, params = plat.build(kit, job.get("params", {}))
tri = sum(len(o.data.polygons) for obs in kit.parts.values() for o in obs)


# --- the checks: the facts against the model as built ---------------------------------------------------------------
checks = []


def check(cid, ok, value, want, note=""):
    checks.append({"id": cid, "pass": bool(ok), "value": value, "want": want, "note": note})


targets = job.get("targets", {})
oal_now = m["muzzle_y"] - m["butt_y"]
if "oal_cm" in targets:
    want = targets["oal_cm"]
    if isinstance(want, dict):   # a sliding stock: one length a position
        for pos, cm in want.items():
            got = oal_now + (int(pos) - m["stock_pos"]) * plat.STOCK_STEP   # each step out adds a step of length
            check("length_stock_%s" % pos, abs(got - cm) <= cm * 0.015, round(got, 2), cm, "within 1.5 percent; source: " + targets.get("source", "-"))
    else:
        check("length", abs(oal_now - want) <= want * 0.015, round(oal_now, 2), want, "within 1.5 percent; source: " + targets.get("source", "-"))

lo, hi = kit.bounds("Bolt_Head")
check("chamber_on_bore", abs(hi.y) < 0.05 and abs((lo.z + hi.z) / 2) < 0.05, [round(hi.y, 3), round((lo.z + hi.z) / 2, 3)], [0, 0],
      "the bolt face at rest on the bore, at the origin")

OPEN_DEG = plat.COVER_OPEN_DEG
cover_stop = None
if "DustCover" in kit.parts:
    # the cover's spring swings it open until it meets the lower (beside the magazine well): swing it a degree at a
    # time and stop it one degree short of the first touch. The upper it rides against at its hinge does not count.
    import bmesh as _bm
    from mathutils.bvhtree import BVHTree as _BVH
    skip = {"Upper", "DustCover_Rod"}
    bm = _bm.new()
    owner = []
    for bone, obs in kit.parts.items():
        if bone == "DustCover":
            continue
        for ob in obs:
            if ob.name.split(".")[0] in skip:
                continue
            n0 = len(bm.faces)
            tmp = ob.data.copy()
            tmp.transform(ob.matrix_world)
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
            owner += [ob.name.split(".")[0]] * (len(bm.faces) - n0)
    gun_tree = _BVH.FromBMesh(bm)
    bm.free()
    hinge_b = K.g(*plat.HINGE)
    cover_obs = kit.parts["DustCover"]
    base = []
    for ob in cover_obs:
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        base.append(me)
    deg = 0.0
    while deg > plat.COVER_OPEN_DEG:
        nxt = deg - 1.0
        R = Matrix.Translation(hinge_b) @ Matrix.Rotation(math.radians(nxt), 4, Vector((0, 1, 0))) @ Matrix.Translation(-hinge_b)
        hit = None
        for me in base:
            bm = _bm.new()
            bm.from_mesh(me)
            bm.transform(R)
            pairs = _BVH.FromBMesh(bm).overlap(gun_tree)
            bm.free()
            if pairs:
                hit = owner[pairs[0][1]]
                break
        if hit:
            cover_stop = {"deg": deg, "touches": hit}
            break
        deg = nxt
    for me in base:
        bpy.data.meshes.remove(me)
    OPEN_DEG = deg
    check("cover_swing_clear", True if cover_stop is None else deg <= -120.0, round(OPEN_DEG, 1), "open past -120 degrees",
          "the cover swings open clear of the gun%s" % (" until it rests on %s" % cover_stop["touches"] if cover_stop else ""))
    moving["DustCover"]["open_deg"] = OPEN_DEG
    if cover_stop:
        moving["DustCover"]["rests_on"] = cover_stop["touches"]

if "DustCover_Plate" in kit.named:
    lo, hi = kit.bounds("DustCover_Plate")
    py, pz = plat.PORT["y"], plat.PORT["z"]
    over = max(lo.y - py[0], py[1] - hi.y, lo.z - pz[0] - 0.01, pz[1] - hi.z, 0.0)
    check("cover_closes_port", over <= 0.0, round(over, 3), 0.0, "the closed cover reaches past every edge of the port (cm short)")
    hz = plat.HINGE[2]
    check("cover_hinge_at_port_bottom", abs(hz - pz[0]) < 0.05, round(hz, 3), pz[0], "the hinge on the port's bottom edge")
    # the open cover, turned about the hinge: every point stays outside the receiver's right face
    ob = kit.named["DustCover_Plate"]
    hinge = Vector(plat.HINGE)
    turn = Matrix.Rotation(math.radians(OPEN_DEG), 3, Vector((0, 1, 0)))   # about the gun's Y
    xs = []
    for v in ob.data.vertices:
        pg = K.ug(ob.matrix_world @ v.co) - hinge
        # gun space is left-handed against Blender's: turn in Blender's frame, where the open angle is defined
        pb = Vector((pg.x, -pg.y, pg.z))
        qb = turn @ pb
        xs.append(qb.x + hinge.x)
    check("cover_opens_outside", max(xs) <= -plat.UP_HW + 0.02, round(max(xs), 3), "<= %.2f" % (-plat.UP_HW + 0.02),
          "open, the plate hangs outside the receiver's right face, not through it")

ob = kit.named["Magazine_Body"]
wy, hw = m["well_in"], m["hw_in"]
over = 0.0
for v in ob.data.vertices:
    p = K.ug(ob.matrix_world @ v.co)
    if p.z >= plat.WELL_BOT:
        over = max(over, abs(p.x) - hw, wy[0] - p.y, p.y - wy[1])
check("magazine_in_well", over <= 0.0, round(over, 3), 0.0, "inside the well the magazine stays clear of every wall (cm into a wall)")
check("magazine_seated", plat.UP_BOT - plat.WELL_BOT >= 4.0, round(plat.UP_BOT - plat.WELL_BOT, 2), ">= 4.0",
      "how deep the well holds the magazine (cm)")
check("bolt_clears_round", -plat.BOLT_TRAVEL < m["round_rear_y"] - 0.1, [-plat.BOLT_TRAVEL, round(m["round_rear_y"], 2)], "travel past the top round",
      "drawn back, the bolt face is behind the top round so it can strip it")


# --- the parts table: every visible part of the real gun with its features drawn (modellab_<platform>.PARTS) -------
parts_report = plat.parts_check(params, set(kit.named)) if hasattr(plat, "parts_check") else []
missing = ["%s: %s" % (r["part"], ", ".join(r["missing"])) for r in parts_report if r["missing"]]
if parts_report:
    n_feat = sum(len(r["features"]) for r in parts_report)
    check("parts_complete", not missing, missing or "all %d features of %d parts" % (n_feat, len(parts_report)), "every feature drawn",
          "each visible part of the real gun with its real features (the platform's parts table)")


# where every shape is (gun cm), so a difference against a real gun can be named by the parts there
shape_bounds = {}
for n in sorted(kit.named):
    if n.startswith("_"):
        continue
    try:
        lo_, hi_ = kit.bounds(n)
        shape_bounds[n] = [[round(c, 2) for c in lo_], [round(c, 2) for c in hi_]]
    except Exception:
        pass


# --- the magazine alone, for the hand: its origin on the feed lips ------------------------------------------------
copies = []
for ob in kit.parts["Magazine"] + kit.parts.get("MagRound", []):
    c = ob.copy()
    c.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(c)
    copies.append(c)
lips = K.g(*marks["mag_lips"]["at"])
for c in copies:
    c.data.transform(c.matrix_world)
    c.matrix_world = Matrix.Identity(4)
    c.data.transform(Matrix.Translation(-lips))
for o in bpy.context.scene.objects:
    o.select_set(False)
for c in copies:
    c.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
mag_ob = bpy.context.object
mag_ob.name = "SM_%s_Magazine" % NAME
mag_ob.hide_render = True

# --- the rig ---------------------------------------------------------------------------------------------------------
try:
    import finish_util
    colors = finish_util.edge_colors
except ImportError:
    colors = None
slots = kit.refine_slots(getattr(plat, "slot_of", None))   # the coating slots: upper, lower, barrel apart
arm, mesh = kit.rig("SK_%s_Rig" % NAME, bones, colors)
slot_tris = {}
for poly in mesh.data.polygons:
    mname = mesh.data.materials[poly.material_index].name if mesh.data.materials else "-"
    slot_tris[mname] = slot_tris.get(mname, 0) + 1
if colors:
    colors(mag_ob)
scale = float(job.get("scale", 1.0))
if scale != 1.0:
    arm.scale = (scale, scale, scale)

# --- the attachments: each drawn in its own frame, rigged apart, mounted on its socket ------------------------------
import bmesh  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
import modellab_attach as A  # noqa: E402

SIGHT_Z = m["sight_z"]
mounts, att_problems = A.resolve(A.entries(params.get("attachments"), params), m["rails"])
for prob in att_problems:
    check("attachment_%s_mounts" % prob["item"], False, prob["why"], "a free slot on a rail it fits")
atts = []


def to_gun(mt, p):
    """A point of an attachment's own frame (cm) into gun space, as its socket puts it."""
    (sx, sy, sz), _ = A.socket(mt)
    x, y, z = p
    face = mt["face"]
    if face == "top":
        return Vector((x + sx, y + sy, z + sz))
    if face == "bottom":
        return Vector((-x + sx, y + sy, -z + sz))
    if face == "left":
        return Vector((z + sx, y + sy, -x + sz))
    return Vector((-z + sx, y + sy, x + sz))


for mt in mounts:
    it = A.ITEMS[mt["item"]]
    akit = K.Kit.like(kit)
    ax = SIGHT_Z - mt["surface"] - 0.01
    abones, amoves, info = A.build(akit, mt, ax)
    # the points the checks need, in its own frame, before the parts are joined
    local = {}
    for key in ("Rear_Aperture", "Front_Post", "Lens_Rear", "Window_Rear", "Lens_Front", "Window_Front"):
        if key in akit.named:
            lo_, hi_ = akit.bounds(key)
            local[key] = ((lo_ + hi_) / 2, lo_, hi_)
    a_tri = sum(len(o.data.polygons) for obs in akit.parts.values() for o in obs)
    a_arm, a_mesh = akit.rig("%s_%s" % (NAME, mt["name"]), abones, colors)
    col = a_mesh.data.color_attributes.get("Col")
    if col and getattr(akit, "bores", None):   # inside a bore: no wear (the cut's edges are sharp, but nothing rubs them)
        for i, v in enumerate(a_mesh.data.vertices):
            q = K.ug(v.co)
            if any(math.hypot(q.x - bx, q.z - bz) < br + 0.05 for bx, bz, br in akit.bores):
                col.data[i].color = (1.0, 1.0, 1.0, 1.0)
    at, turn = A.socket(mt)
    M_ = Matrix.Translation(K.g(*at)) @ Matrix.Rotation(math.radians(turn), 4, 'Y')
    if scale != 1.0:
        M_ = Matrix.Scale(scale, 4) @ M_
    a_arm.matrix_world = M_
    states = it["states"]
    rest_v = states.index(mt["state"]) if mt["state"] in states else 0   # 0 the rest state as drawn, 1 the moved one
    atts.append({"mount": mt, "item": it, "arm": a_arm, "mesh": a_mesh, "moves": amoves, "local": local, "value": float(rest_v),
                 "tri": a_tri, "info": info})


def att_pose(a, v):
    """An attachment's moving bones at v of their move (0 as drawn, 1 moved)."""
    arm_ = a["arm"]
    for pb in arm_.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    for bone, (kind, axis, amount) in a["moves"].items():
        b = arm_.data.bones[bone]
        h = b.head_local
        R = Quaternion(Vector(axis), math.radians(amount * v)).to_matrix().to_4x4()
        arm_.pose.bones[bone].matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ b.matrix_local
        bpy.context.view_layer.update()


def world_bvh(ob):
    """A BVH of a shape as it stands (posed, in world space)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ob.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    ev.to_mesh_clear()
    return tree


for a in atts:
    att_pose(a, a["value"])
gun_tree = world_bvh(mesh)
for a in atts:
    name = a["mount"]["name"]
    others = [(b["mount"]["name"], world_bvh(b["mesh"])) for b in atts if b is not a]
    hits, blocked = [], []
    values = [0.0, 1.0] if a["moves"] else [a["value"]]
    for v in values:
        att_pose(a, v)
        tree = world_bvh(a["mesh"])
        state = a["item"]["states"][int(v)] if a["moves"] else "fixed"
        if tree.overlap(gun_tree):
            hits.append("the gun (%s)" % state)
        for oname, otree in others:
            if tree.overlap(otree):
                # in the state it shows, a clash is a fault; in its other state it is real use: move the other first
                (hits if v == a["value"] else blocked).append("%s (%s)" % (oname, state))
    att_pose(a, a["value"])
    a["blocked_by"] = blocked
    check("attachment_%s_clear" % name, not hits, hits or "clear", "clear",
          "on rail %s slot %d: clear of the gun in every state and of the other attachments as shown%s" % (
              a["mount"]["rail"], a["mount"]["slot"], "; to change state, first move: " + ", ".join(blocked) if blocked else ""))

# the sights: the iron sight line from the fixed sights and the flip sights, the optics on it
rear = marks.get("rear_sight", {}).get("at")
front = list(m["front_sight"]) if m["front_sight"] else None
for a in atts:
    mt, loc = a["mount"], a["local"]
    if "Rear_Aperture" in loc:
        rear = list(to_gun(mt, loc["Rear_Aperture"][0]))
        marks["rear_sight"] = {"at": [round(c, 3) for c in rear], "by": mt["name"]}
    if "Front_Post" in loc:
        c, lo_, hi_ = loc["Front_Post"]
        tip = to_gun(mt, (c.x, c.y, hi_.z))
        front = list(tip)
        marks["front_sight"] = {"at": [round(c_, 3) for c_ in front], "by": mt["name"]}
if front and rear:
    d = abs(rear[2] - front[2])
    check("sight_line", d < 0.1, round(d, 3), "< 0.1", "the rear aperture and the front post tip at one height")
optics = []
for a in atts:
    mt, loc, kind = a["mount"], a["local"], a["item"]["kind"]
    if kind not in ("optic", "magnifier", "optic_low"):
        continue
    key = next(k for k in ("Lens_Rear", "Window_Rear") if k in loc)
    axis = to_gun(mt, loc[key][0])
    key_f = next(k for k in ("Lens_Front", "Window_Front") if k in loc)
    axis_f = to_gun(mt, loc[key_f][0])
    a["axis"] = [round(c, 3) for c in axis]
    optics.append((a, axis, axis_f))
    if a["item"]["axis"] == "co_witness":
        d = axis.z - SIGHT_Z
        check("%s_co_witness" % mt["name"], abs(d) < 0.15 and abs(axis_f.z - axis.z) < 0.05, round(d, 3), "|d| < 0.15",
              "its axis on the iron sight line, level: the irons show through it (absolute co-witness)")
    else:
        check("%s_under_irons" % mt["name"], axis.z < SIGHT_Z - 0.5, round(axis.z - SIGHT_Z, 3), "< -0.5",
              "its axis sits under the iron sight line, as real (no co-witness: folded backup sights stay down)")
for a, axis, _ in optics:
    if a["item"]["kind"] != "magnifier":
        continue
    ahead = [(b, ax_) for b, ax_, _ in optics if b["item"]["kind"] == "optic" and ax_.y > axis.y]
    ok = any(abs(ax_.z - axis.z) < 0.15 and abs(ax_.x - axis.x) < 0.1 for b, ax_ in ahead)
    check("%s_behind_optic" % a["mount"]["name"], ok, [b["mount"]["name"] for b, _ in ahead] or "no optic ahead", "a red dot or holo ahead on its axis",
          "a magnifier magnifies the dot of a sight ahead of it; it needs one on the same axis")

# --- pictures ---------------------------------------------------------------------------------------------------
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.film_transparent = False
world = bpy.data.worlds.new("bg")
sc.world = world
world.color = (0.62, 0.64, 0.68)
renderer = "workbench"
if job.get("render", "eevee") == "eevee":
    # a studio: real materials (colour, metal, roughness, worn edges) under a key, a fill and a rim light
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            renderer = "eevee"
            break
        except TypeError:
            continue
if renderer == "eevee":
    sc.eevee.taa_render_samples = 32
    world.use_nodes = True
    bgn = world.node_tree.nodes.get("Background")
    bgn.inputs["Color"].default_value = (0.42, 0.44, 0.47, 1.0)
    bgn.inputs["Strength"].default_value = 0.7
    for lname, energy, rot in (("Key", 3.2, (math.radians(50), 0, math.radians(-35))), ("Fill", 1.1, (math.radians(65), 0, math.radians(140))),
                               ("Rim", 2.2, (math.radians(115), 0, math.radians(-160)))):
        ld = bpy.data.lights.new(lname, 'SUN')
        ld.energy = energy
        ld.angle = math.radians(8)
        lo_ = bpy.data.objects.new(lname, ld)
        lo_.rotation_euler = rot
        sc.collection.objects.link(lo_)
    sc.view_settings.view_transform = 'AgX'
else:
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_shadows = False
    sh.show_specular_highlight = True
    sc.display.render_aa = '16'
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
bpy.context.view_layer.update()
pts = [ (mesh.matrix_world @ v.co) for v in mesh.data.vertices]
blo = Vector([min(p[i] for p in pts) for i in range(3)])
bhi = Vector([max(p[i] for p in pts) for i in range(3)])
mid = (blo + bhi) / 2
span = (bhi - blo).length
shots = []


def shoot(name, d, size, target=None, persp=False, render=True):
    t = target if target is not None else mid
    d = d.normalized()
    cam.data.type = 'PERSP' if persp else 'ORTHO'
    if persp:
        cam.data.lens = 50
        cam.location = t + d * size * 2.6
    else:
        cam.data.ortho_scale = size
        cam.location = t + d * span * 2
    f = -d                                         # where the camera looks
    r = f.cross(Vector((0, 0, 1)))                 # the picture's right: the gun's forward in a side view
    if r.length < 1e-6:
        r = Vector((0, -1, 0))                     # straight down from above: the muzzle to the right
    r.normalize()
    u = (-f).cross(r).normalized()
    loc = t + d * (size * 2.6 if persp else span * 2)
    M = Matrix((r, u, -f)).transposed().to_4x4()
    M.translation = loc
    cam.matrix_world = M
    if not render:
        return None
    path = os.path.join(OUT, "view_%s.png" % name)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    shots.append({"view": name, "path": path})


def set_pose(bolt=0.0, handle=0.0, cover=0.0, mag=0.0):
    """The moving parts at a point of their travel: bolt and handle 0 forward to 1 at the stop, cover 0 shut to 1
    open, mag the magazine's drop along the well in cm."""
    AW = arm.matrix_world
    AWI = AW.inverted()
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()

    def put(bone, move=Vector(), turn=Quaternion()):
        if bone not in arm.pose.bones:
            return
        P = AW @ arm.data.bones[bone].head_local
        W = Matrix.Translation(move) @ Matrix.Translation(P) @ turn.to_matrix().to_4x4() @ Matrix.Translation(-P)
        arm.pose.bones[bone].matrix = (AWI @ W @ AW) @ rest[bone]
        bpy.context.view_layer.update()
    travel = plat.BOLT_TRAVEL / 100.0 * scale
    if bolt:
        put("Bolt", Vector((0, travel * bolt, 0)))
    if handle:
        put("ChargingHandle", Vector((0, travel * handle, 0)))
    if cover:
        put("DustCover", turn=Quaternion(Vector((0, 1, 0)), math.radians(OPEN_DEG * cover)))
    if mag:
        put("Magazine", Vector((0, 0, -mag / 100.0)) * scale)


def pose(open_):
    """The open pose: the carrier and handle to the stop, the cover open, the magazine out along the well."""
    if open_:
        set_pose(1.0, 1.0, 1.0, 9.0)
    else:
        set_pose()


pose(False)
shoot("right", Vector((-1, 0, 0)), span * 1.05)
shoot("left", Vector((1, 0, 0)), span * 1.05)
shoot("top", Vector((0, 0, 1)), span * 1.05)
shoot("front", Vector((0, -1, 0)), span * 0.32)
shoot("three_quarter", Vector((-0.8, -0.9, 0.45)), span * 0.42, persp=True)
receiver = K.g(0, -4.0, -1.0) * scale
shoot("receiver_right", Vector((-1, 0, 0.12)), span * 0.42, target=receiver)
butt = K.g(0, marks["butt"]["at"][1] + 9.0, -3.5) * scale
shoot("stock_three_quarter", Vector((-0.9, 0.35, 0.3)), span * 0.17, target=butt, persp=True)
handle_at = K.g(0.0, -15.9, 1.9) * scale
shoot("charging_handle", Vector((-0.75, 0.75, 0.55)), span * 0.06, target=handle_at, persp=True)
grip = K.g(*marks["grip_r"]["at"]) * scale
shoot("grip_lower_left", Vector((0.85, 0.45, -0.25)), span * 0.13, target=grip, persp=True)
# the shooter's eye on the sight line, a little behind the rearmost sight, looking down the bore
eye_y = rear[1] if rear else m["butt_y"] + 25.0
for _, ax_, _ in optics:
    eye_y = min(eye_y, ax_.y)
ahead = K.g(0, front[1] if front else m["muzzle_y"], SIGHT_Z) * scale
eye = K.g(0, eye_y - 8.0, SIGHT_Z) * scale
shoot("sight_picture", Vector((0, 1, 0)), (ahead - eye).length / 2.6, target=ahead, persp=True)
if atts:
    rail_mid = K.g(0, (min(a["mount"]["y"] for a in atts) + max(a["mount"]["y"] for a in atts)) / 2, 1.0) * scale
    shoot("attachments", Vector((-0.6, 0.45, 0.65)), span * 0.3, target=rail_mid, persp=True)
pose(True)
shoot("open_right", Vector((-1, 0, 0.12)), span * 0.42, target=receiver)
shoot("open_three_quarter", Vector((-0.9, -0.5, 0.5)), span * 0.2, target=receiver, persp=True)
port = K.g(*marks["eject_port"]["at"]) * scale
shoot("open_port", Vector((-1, 0.25, 0.35)), span * 0.11, target=port)
pose(False)

# --- the motion: one cycle of the moving parts, kept as an action in the .blend ---------------------------------
# frames at 30 a second: pull the handle (the cover springs open as the carrier moves), let it fly forward, drop the
# magazine, seat it again, shut the cover by hand
FPS = 30
TRACKS = {   # (frame, value, the ease into it)
    "bolt": [(1, 0), (10, 0), (22, 1, "in"), (30, 1), (33, 0, "in")],
    "cover": [(1, 0), (10.5, 0), (13, 1, "out"), (95, 1), (101, 0, "inout")],
    "mag": [(1, 0), (45, 0), (56, 18.0, "in"), (70, 18.0), (84, 0, "inout")],
}
PHASES = [(1, "at rest"), (10, "pull the charging handle"), (22, "the bolt at the rear"), (30, "let go: the bolt flies home"),
          (45, "press the magazine release"), (56, "the magazine out"), (70, "seat the magazine"), (95, "shut the dust cover"),
          (102, "at rest")]
LAST = 110
if any(a["moves"] for a in atts):
    # then each moving attachment goes to its other state and back; one another blocks moves second, after the
    # blocker has moved out of its way (a backup sight goes up after the magnifier swings aside), and back first
    def _went(a):
        return "%s to %s" % (a["mount"]["name"], a["item"]["states"][1 - int(a["value"])])
    first = [a for a in atts if a["moves"] and not a.get("blocked_by")]
    second = [a for a in atts if a["moves"] and a.get("blocked_by")]
    for a in first:
        a["track"] = "att1"
    for a in second:
        a["track"] = "att2"
    TRACKS["att1"] = [(1, 0), (110, 0), (122, 1, "inout"), (145, 1), (157, 0, "inout")]
    TRACKS["att2"] = [(1, 0), (123, 0), (133, 1, "inout"), (134, 1), (144, 0, "inout")]
    PHASES += [(110, "attachments: " + ", ".join(_went(a) for a in first))]
    if second:
        PHASES += [(123, "then " + ", ".join(_went(a) for a in second)), (134, "and back")]
    PHASES += [(145, "attachments back"), (158, "at rest")]
    LAST = 164


def _ease(t, kind):
    if kind == "in":
        return t * t
    if kind == "out":
        return 1 - (1 - t) ** 2
    if kind == "inout":
        return t * t * (3 - 2 * t)
    return t


def track(name, f):
    keys = TRACKS[name]
    for k0, k1 in zip(keys, keys[1:]):
        if k0[0] <= f <= k1[0]:
            t = (f - k0[0]) / (k1[0] - k0[0])
            return k0[1] + (k1[1] - k0[1]) * _ease(t, k1[2] if len(k1) > 2 else "")
    return keys[-1][1]


def phase(f):
    return [name for start, name in PHASES if start <= f][-1]


arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new("%s_Cycle" % NAME)
sc.frame_start, sc.frame_end = 1, LAST
sc.render.fps = FPS
for start, name in PHASES:
    sc.timeline_markers.new(name, frame=start)
for a in atts:
    if a["moves"]:
        a["arm"].animation_data_create()
        a["arm"].animation_data.action = bpy.data.actions.new("%s_%s_Cycle" % (NAME, a["mount"]["name"]))
for f in range(1, LAST + 1):
    b_ = track("bolt", f)
    set_pose(b_, b_, track("cover", f), track("mag", f))
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
    for a in atts:
        if a["moves"]:
            d_ = a["value"]
            att_pose(a, d_ + (1 - 2 * d_) * track(a.get("track", "att1"), f))
            for pb in a["arm"].pose.bones:
                pb.keyframe_insert("location", frame=f)
                pb.keyframe_insert("rotation_quaternion", frame=f)
motion = None
if job.get("motion"):
    # every frame from two views; ttools joins them into labelled GIFs
    frames = os.path.join(OUT, "motion")
    os.makedirs(frames, exist_ok=True)
    keep = (sc.render.resolution_x, sc.render.resolution_y)
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    if renderer == "eevee":
        sc.eevee.taa_render_samples = 12
    motion = {"fps": FPS, "frames": LAST, "phases": [{"frame": f_, "name": n_} for f_, n_ in PHASES], "views": {}}
    for view, args in (("receiver_right", (Vector((-1, 0, 0.12)), span * 0.42, receiver, False)),
                       ("three_quarter", (Vector((-0.9, -0.55, 0.45)), span * 0.24, K.g(0, -5.0, -3.0) * scale, True))):
        shoot(view, *args, render=False)
        paths = []
        for f in range(1, LAST + 1):
            sc.frame_set(f)
            path_ = os.path.join(frames, "%s_%03d.png" % (view, f))
            sc.render.filepath = path_
            bpy.ops.render.render(write_still=True)
            paths.append(path_)
        motion["views"][view] = paths
    sc.render.resolution_x, sc.render.resolution_y = keep
sc.frame_set(1)
pose(False)
for a in atts:
    att_pose(a, a["value"])

# --- the files -------------------------------------------------------------------------------------------------
for o in bpy.context.scene.objects:
    o.select_set(False)
arm.select_set(True)
mesh.select_set(True)
fbx = os.path.join(OUT, "SK_%s_Rig.fbx" % NAME)
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                         bake_anim=False, mesh_smooth_type='FACE', colors_type='LINEAR')
for o in bpy.context.scene.objects:
    o.select_set(False)
mag_ob.hide_render = False
mag_ob.select_set(True)
mag_fbx = os.path.join(OUT, "SM_%s_Magazine.fbx" % NAME)
bpy.ops.export_scene.fbx(filepath=mag_fbx, use_selection=True, object_types={'MESH'}, mesh_smooth_type='FACE',
                         add_leaf_bones=False, bake_anim=False, colors_type='LINEAR')
att_facts = []
for a in atts:
    mt, it = a["mount"], a["item"]
    keep_m = a["arm"].matrix_world.copy()
    a["arm"].matrix_world = Matrix.Identity(4)
    if a["arm"].animation_data:
        act = a["arm"].animation_data.action
        a["arm"].animation_data.action = None
    att_pose(a, 0.0)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    a["mesh"].select_set(True)
    moving_ = bool(a["moves"])
    if moving_:
        a["arm"].select_set(True)
    path_ = os.path.join(OUT, "%s_%s_%s.fbx" % ("SK" if moving_ else "SM", NAME, mt["name"]))
    bpy.ops.export_scene.fbx(filepath=path_, use_selection=True, object_types={'ARMATURE', 'MESH'} if moving_ else {'MESH'},
                             add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', colors_type='LINEAR')
    a["arm"].matrix_world = keep_m
    if a["arm"].animation_data:
        a["arm"].animation_data.action = act
    att_pose(a, a["value"])
    at, turn = A.socket(mt)
    att_facts.append({
        "name": mt["name"], "item": mt["item"], "about": it["about"], "rail": mt["rail"], "rail_type": mt["type"], "slot": mt["slot"],
        "socket": {"at": [round(c, 3) for c in at], "turn_y_deg": turn,
                   "note": "the attachment's origin (its recoil lug, on the rail's top surface) in gun space; turned about the bore"},
        "state": mt["state"], "states": it["states"], "options": mt["options"],
        "moving": {b: {"kind": k, "axis": list(ax_), "deg": amt, "what": it["moving"].get(b, "")} for b, (k, ax_, amt) in a["moves"].items()},
        "axis": a.get("axis"), "axis_over_rail_cm": round(a["info"]["axis_over_rail"], 3) if a["info"]["axis_over_rail"] else None,
        "blocked_by": a.get("blocked_by", []), "triangles": a["tri"], "file": path_,
    })
mag_ob.hide_render = True      # in the .blend the hand's magazine stays out of renders (it sits at the origin)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "%s.blend" % NAME))

size = (bhi - blo) * 100.0
facts = {
    "name": NAME, "platform": job["platform"], "params": params, "scale": scale,
    "frame": "gun space, cm: +X the gun's left, +Y forward, +Z up; the origin is the bolt face at rest on the bore",
    "size_cm": {"length": round(size.y, 2), "height": round(size.z, 2), "width": round(size.x, 2)},
    "triangles": tri, "vertices": len(mesh.data.vertices), "renderer": renderer,
    "bones": [b[0] for b in bones], "marks": marks, "moving": moving,
    "checks": checks, "all_pass": all(c["pass"] for c in checks), "motion": motion,
    "action": "%s_Cycle" % NAME,
    "rails": m["rails"], "attachments": att_facts, "attachment_problems": att_problems, "parts": parts_report,
    "shape_bounds": shape_bounds,
    "slots": {s: {"shapes": shapes, "triangles": slot_tris.get(s, 0)} for s, shapes in slots.items()},
    "files": {"rig": fbx, "magazine": mag_fbx, "blend": os.path.join(OUT, "%s.blend" % NAME)}, "views": shots,
}
json.dump(facts, open(os.path.join(OUT, "facts.json"), "w", encoding="utf-8"), indent=1)
print("MODEL LAB: %s %s, %d checks, all pass %s" % (NAME, job["platform"], len(checks), facts["all_pass"]))
