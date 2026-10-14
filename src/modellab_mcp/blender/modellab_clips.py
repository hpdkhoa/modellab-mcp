"""Model Lab's gun clips: the gun's own moving parts
through real actions, from beats and timings, on a Model Lab rig. It opens a build's .blend, keys each clip at 60
frames a second, measures it (every part on its own axis; each beat happens: the bolt's full stroke, the cover open
before the carrier passes, the magazine out of the well and seated, the bolt held on its catch), exports each clip
alone as FBX and renders a labelled GIF a clip. Writes only under the build's clips folder.

    blender -b <build>/<name>.blend -P modellab_clips.py -- <clips_job.json>

job: {"facts": <facts.json>, "out": <build>/clips, "clips": [names] or null for all, "render": true}

Timings are estimates at real speeds: a hand pulls the charging handle in about a third of a second; the buffer
spring returns the carrier in about 40 ms; a cycle at about 800 rounds a minute takes 75 ms (the M4's rate is
700 to 970 a minute, Wikipedia, M4 carbine); a dropped magazine falls freely (18 cm in about 0.19 s at 9.8 m/s2)."""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
facts = json.load(open(job["facts"], encoding="utf-8"))
OUT = job["out"]
os.makedirs(OUT, exist_ok=True)
NAME = facts["name"]
MOV = facts["moving"]
FPS = 60
sc = bpy.context.scene
sc.render.fps = FPS
arm = bpy.data.objects["SK_%s_Rig" % NAME]
mesh = bpy.data.objects["SK_%s_Rig_Mesh" % NAME]
TRAVEL = MOV["Bolt"]["travel_cm"]
CATCH = MOV["Bolt"]["catch_cm"]
WELL_DROP = facts["marks"]["mag_lips"]["at"][2] - facts["marks"]["magwell"]["bottom_z"]   # the lips to the well's mouth
for o in bpy.data.objects:            # the hand's magazine (SM_<name>_Magazine, at the origin) is not on the gun
    if o.name.startswith("SM_"):
        o.hide_render = True
for a in bpy.data.objects:            # the attachments keep the pose the build left them in
    if a.type == 'ARMATURE' and a is not arm and a.animation_data:
        a.animation_data.action = None


def g(v):
    """Gun space (cm) to Blender (m)."""
    return Vector((v[0], -v[1], v[2])) / 100.0


# --- the channels: what each moves, in gun space -------------------------------------------------------------------
def _move(bone, cm_axis):
    return {"bone": bone, "kind": "move", "axis": Vector(cm_axis)}


CHANNELS = {
    "bolt": _move("Bolt", (0, -1, 0)),               # cm back along the bore
    "handle": _move("ChargingHandle", (0, -1, 0)),   # cm back
    "mag": _move("Magazine", (0, 0, -1)),            # cm down along the well
    "catch": _move("BoltCatch", (0, 0, MOV["BoltCatch"]["lift_cm"])),   # 0 down, 1 up holding the bolt
    "release": _move("MagRelease", (MOV.get("MagRelease", {}).get("press_cm", 0.3), 0, 0)),     # pressed in from the right
    "fa": _move("ForwardAssist", (0, MOV.get("ForwardAssist", {}).get("press_cm", 0.5), 0)),    # pushed forward
    "stock": _move("Stock", (0, 1, 0)),              # cm forward (collapsing)
    "cover": {"bone": "DustCover", "kind": "turn", "axis": Vector((0, 1, 0)), "deg": MOV["DustCover"]["open_deg"]},
    "trigger": {"bone": "Trigger", "kind": "turn", "axis": Vector((1, 0, 0)), "deg": MOV["Trigger"]["pull_deg"]},
}

# --- the clips: beats as (time s, value[, ease into it]) a channel ---------------------------------------------------
S = 1.0 / FPS
CLIPS = {
    "charge": {"about": "charge: the charging handle pulled to the rear with the carrier, then let go; the carrier "
                        "flies home and takes the handle with it; the cover springs open as the carrier moves",
               "len": 1.0, "view": "receiver",
               "bolt": [(0, 0), (0.2, 0), (0.55, TRAVEL, "out"), (0.65, TRAVEL), (0.69, 0, "in")],
               "handle": [(0, 0), (0.2, 0), (0.55, TRAVEL, "out"), (0.65, TRAVEL), (0.69, 0, "in")],
               "cover": [(0, 0), (0.2, 0), (0.212, 1, "out")]},
    "chamber_check": {"about": "a press check: the handle drawn back about 2 cm to show the brass in the chamber, held, "
                               "eased home, the forward assist pressed to seat the bolt",
                      "len": 1.7, "view": "port",
                      "bolt": [(0, 0), (0.2, 0), (0.6, 2.0, "inout"), (1.0, 2.0), (1.15, 0, "inout")],
                      "handle": [(0, 0), (0.2, 0), (0.6, 2.0, "inout"), (1.0, 2.0), (1.15, 0, "inout"), (1.2, 0)],
                      "cover": [(0, 0), (0.2, 0), (0.215, 1, "out")],
                      "fa": [(0, 0), (1.25, 0), (1.32, 1, "out"), (1.38, 1), (1.45, 0, "in")]},
    "fire": {"about": "one shot: the trigger pulled, the carrier cycles its full stroke in about 75 ms (gas back, the "
                      "buffer spring home), the trigger let out to reset", "len": 0.8, "view": "receiver", "slow": 4,
             "trigger": [(0, 0), (0.1, 0), (0.2, 1, "inout"), (0.4, 1), (0.5, 0, "inout")],
             "bolt": [(0, 0), (0.2, 0), (0.235, TRAVEL, "out"), (0.275, 0, "in")],
             "cover": [(0, 0), (0.2, 0), (0.205, 1, "out")]},
    "fire_last": {"about": "the last shot: the carrier goes back and the empty magazine's follower lifts the bolt catch; "
                           "the carrier stops on it, the bolt held open", "len": 0.8, "view": "receiver", "slow": 4,
                  "trigger": [(0, 0), (0.1, 0), (0.2, 1, "inout"), (0.4, 1), (0.5, 0, "inout")],
                  "bolt": [(0, 0), (0.2, 0), (0.235, TRAVEL, "out"), (0.262, CATCH, "in")],
                  "catch": [(0, 0), (0.24, 0), (0.25, 1, "out")],
                  "cover": [(0, 0), (0.2, 0), (0.205, 1, "out")]},
    "reload": {"about": "a magazine change with the bolt home: the release pressed, the magazine falls free, a full one "
                        "pushed up the well and seated with a slap", "len": 2.0, "view": "well",
               "release": [(0, 0), (0.2, 0), (0.25, 1, "out"), (0.4, 1), (0.45, 0, "in")],
               "mag": [(0, 0), (0.25, 0), (0.45, 20.0, "in"), (1.2, 20.0), (1.42, 0.0, "inout"), (1.47, 0.0)]},
    "reload_empty": {"about": "an empty reload: the bolt held open on its catch, the empty magazine dropped, a full one "
                              "seated, the catch pressed: the carrier flies home and strips the top round",
                     "len": 2.3, "view": "well",
                     "bolt": [(0, CATCH), (1.75, CATCH), (1.79, 0, "in")],
                     "catch": [(0, 1), (1.7, 1), (1.75, 0, "out")],
                     "cover": [(0, 1)],
                     "release": [(0, 0), (0.2, 0), (0.25, 1, "out"), (0.4, 1), (0.45, 0, "in")],
                     "mag": [(0, 0), (0.25, 0), (0.45, 20.0, "in"), (1.2, 20.0), (1.42, 0.0, "inout"), (1.47, 0.0)]},
    "stock": {"about": "the stock collapsed to its first position and drawn out again, one step at a time",
              "len": 2.0, "view": "stock", "needs": "Stock"},
}
if "Stock" in MOV:   # the stock steps in to position 0 and back out to where the build has it
    step, now = MOV["Stock"]["step_cm"], MOV["Stock"]["now"]
    keys, t = [(0, 0.0), (0.2, 0.0)], 0.2
    for k in range(1, now + 1):
        t += 0.18
        keys.append((t, k * step, "inout"))
    t += 0.3
    keys.append((t, now * step))
    for k in range(now - 1, -1, -1):
        t += 0.18
        keys.append((t, k * step, "inout"))
    CLIPS["stock"]["stock"] = keys
    CLIPS["stock"]["len"] = t + 0.3


def ease(t, kind):
    if kind == "in":
        return t * t
    if kind == "out":
        return 1 - (1 - t) ** 2
    if kind == "inout":
        return t * t * (3 - 2 * t)
    return t


def value(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for k0, k1 in zip(keys, keys[1:]):
        if k0[0] <= t <= k1[0]:
            u = (t - k0[0]) / (k1[0] - k0[0]) if k1[0] > k0[0] else 1.0
            return k0[1] + (k1[1] - k0[1]) * ease(u, k1[2] if len(k1) > 2 else "")
    return keys[-1][1]


rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}


def pose(vals):
    """The rig at a set of channel values (armature space; a move in cm along its gun axis, a turn about its head)."""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    for ch, v in vals.items():
        c = CHANNELS[ch]
        if c["bone"] not in arm.pose.bones or not v:
            continue
        b = arm.data.bones[c["bone"]]
        if c["kind"] == "move":
            W = Matrix.Translation(g(c["axis"] * v))
        else:
            h = b.head_local
            W = Matrix.Translation(h) @ Quaternion(c["axis"], math.radians(c["deg"] * v)).to_matrix().to_4x4() @ Matrix.Translation(-h)
        arm.pose.bones[c["bone"]].matrix = W @ arm.pose.bones[c["bone"]].matrix
        bpy.context.view_layer.update()


def heads():
    """Each moving bone's head in gun space (cm), as posed."""
    out = {}
    for pb in arm.pose.bones:
        h = pb.head
        out[pb.name] = Vector((h.x * 100, -h.y * 100, h.z * 100))
    return out


# --- the camera ----------------------------------------------------------------------------------------------------
cam = bpy.data.objects.get("cam")
sc.camera = cam


def aim(d, size, t, persp=False):
    d = Vector(d).normalized()
    cam.data.type = 'PERSP' if persp else 'ORTHO'
    if persp:
        cam.data.lens = 50
        loc = t + d * size * 2.6
    else:
        cam.data.ortho_scale = size
        loc = t + d * 2.0
    f = -d
    r = f.cross(Vector((0, 0, 1)))
    if r.length < 1e-6:
        r = Vector((0, -1, 0))
    r.normalize()
    u = (-f).cross(r).normalized()
    M = Matrix((r, u, -f)).transposed().to_4x4()
    M.translation = loc
    cam.matrix_world = M


scale = arm.matrix_world.to_scale().x
VIEWS = {
    "receiver": ((-1, 0, 0.12), 0.36, g((0, -6.0, -0.5)) * scale, False),
    "port": ((-1, 0.2, 0.3), 0.16, g(facts["marks"]["eject_port"]["at"]) * scale, True),
    "well": ((-1, 0, 0.05), 0.55, g((0, -5.0, -12.0)) * scale, False),
    "stock": ((-1, 0, 0.1), 0.6, g((0, facts["marks"]["butt"]["at"][1] + 18.0, -2.0)) * scale, False),
}

# --- each clip: key it, measure it, export it, render it -------------------------------------------------------------
want = job.get("clips") or list(CLIPS)
report = {"fps": FPS, "frame": facts["frame"], "clips": {}}
sc.render.resolution_x, sc.render.resolution_y = 960, 540
if sc.render.engine.startswith("BLENDER_EEVEE"):
    sc.eevee.taa_render_samples = 12
for name in want:
    clip = CLIPS[name]
    if clip.get("needs") and clip["needs"] not in MOV:
        report["clips"][name] = {"skipped": "the build has no %s" % clip["needs"]}
        continue
    chans = [c for c in CHANNELS if c in clip]
    n = int(round(clip["len"] * FPS)) + 1
    act = bpy.data.actions.new("%s_%s" % (NAME, name))
    arm.animation_data_create()
    arm.animation_data.action = act
    track = []
    for f in range(n):
        t = f * S
        vals = {c: value(clip[c], t) for c in chans}
        pose(vals)
        for pb in arm.pose.bones:
            pb.keyframe_insert("location", frame=f + 1)
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)
        track.append({"t": round(t, 4), "vals": vals, "heads": heads()})
    sc.frame_start, sc.frame_end = 1, n
    # the measures: every sliding part on its own line; each beat as the clip promises
    checks = []

    def check(cid, ok, val, want_, note=""):
        checks.append({"id": cid, "pass": bool(ok), "value": val, "want": want_, "note": note})
    rest_heads = track[0]["heads"]
    pose({})
    home = heads()
    for c in chans:
        ch = CHANNELS[c]
        if ch["kind"] != "move" or ch["bone"] not in home:
            continue
        ax = ch["axis"].normalized()
        off = 0.0
        for fr in track:
            d = fr["heads"][ch["bone"]] - home[ch["bone"]]
            off = max(off, (d - ax * d.dot(ax)).length)
        check("%s_on_axis" % ch["bone"], off < 0.005, round(off, 4), "< 0.005 cm", "slides only along its own line")
    series = {c: [fr["vals"][c] for fr in track] for c in chans}
    times = [fr["t"] for fr in track]
    if "bolt" in series and "handle" in series and name == "charge":
        gap = max(abs(a - b) for a, b in zip(series["bolt"], series["handle"]))
        check("handle_with_carrier", gap < 0.01, round(gap, 4), "< 0.01 cm", "the handle drags the carrier back and rides home with it")
        check("bolt_full_stroke", max(series["bolt"]) >= TRAVEL - 0.05, round(max(series["bolt"]), 2), TRAVEL, "to the buffer's stop")
    if "bolt" in series and "cover" in series:
        moved = next((i for i, b in enumerate(series["bolt"]) if abs(b - series["bolt"][0]) > 1.0), None)
        if moved is not None:
            check("cover_open_before_carrier", series["cover"][moved] > 0.95, round(series["cover"][moved], 3), "> 0.95",
                  "the cover is open before the carrier has moved 1 cm (the carrier pushes it open)")
    if name in ("fire", "fire_last"):
        start = next(i for i, b in enumerate(series["bolt"]) if b > 0.01)
        pulled = next(i for i, v in enumerate(series["trigger"]) if v > 0.99)
        check("trigger_before_carrier", pulled <= start, [times[pulled], times[start]], "pulled first", "the hammer falls, then the gas drives the carrier")
        peak = series["bolt"].index(max(series["bolt"]))
        check("bolt_full_stroke", max(series["bolt"]) >= TRAVEL - 0.3, round(max(series["bolt"]), 2), TRAVEL,
              "at 60 frames a second the stroke's peak falls between frames; within 0.3 cm")
        if name == "fire":
            back = next(i for i in range(peak, len(series["bolt"])) if series["bolt"][i] < 0.01)
            cyc = times[back] - times[start - 1]
            check("cycle_time", cyc <= 0.1, round(cyc, 3), "<= 0.1 s", "one cycle at about 800 rounds a minute is 75 ms")
        else:
            check("held_on_catch", abs(series["bolt"][-1] - CATCH) < 0.05 and series["catch"][-1] > 0.99,
                  [round(series["bolt"][-1], 2), series["catch"][-1]], [CATCH, 1], "the carrier rests on the raised catch")
    if name == "chamber_check":
        b = max(series["bolt"])
        check("press_check_travel", 1.0 <= b <= 3.0, round(b, 2), "1 to 3 cm", "back far enough to see the brass, not far enough to extract it")
        check("forward_assist_after", series["fa"].index(max(series["fa"])) > series["bolt"].index(b), True, True,
              "the forward assist after the bolt is home")
    if name in ("reload", "reload_empty"):
        low = max(series["mag"])
        need = WELL_DROP + 0.5
        check("magazine_clears_well", low >= need, round(low, 2), ">= %.2f" % need, "the magazine's lips drop below the well")
        check("magazine_seated", abs(series["mag"][-1]) < 0.01, round(series["mag"][-1], 3), 0.0, "seated at the end")
        first = next(i for i, m_ in enumerate(series["mag"]) if m_ > 0.05)
        check("release_pressed", series["release"][first] > 0.5, round(series["release"][first], 2), "> 0.5",
              "the button is in when the magazine starts to fall")
        if name == "reload_empty":
            seated = next(i for i, m_ in enumerate(series["mag"]) if i > first and m_ < 0.01)
            home_i = next(i for i, b_ in enumerate(series["bolt"]) if b_ < 0.01)
            check("bolt_held_until_seated", home_i > seated and all(abs(b_ - CATCH) < 0.01 for b_ in series["bolt"][:seated + 1]),
                  [times[seated], times[home_i]], "held open until the magazine is in", "the catch holds the carrier open")
            check("catch_released_bolt", series["catch"][home_i] < 0.5, round(series["catch"][home_i], 2), "< 0.5",
                  "the catch is down when the carrier flies home")
    if name == "stock":
        check("stock_steps", max(series["stock"]) <= MOV["Stock"]["now"] * MOV["Stock"]["step_cm"] + 1e-6, round(max(series["stock"]), 2),
              "within its positions", "the stock moves only between its real positions")
    # the clip alone, as FBX (the rig and its mesh, this action only)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    arm.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    fbx = os.path.join(OUT, "A_%s_%s.fbx" % (NAME, name))
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, mesh_smooth_type='FACE', colors_type='LINEAR')
    frames = []
    if job.get("render", True):
        view = VIEWS[clip["view"]]
        aim(view[0], view[1] * scale, view[2], view[3])
        slow = clip.get("slow", 1)
        stepf = 1 if slow > 1 else 2          # GIFs at 30 a second; slow clips every frame, shown slowed
        for f in range(1, n + 1, stepf):
            sc.frame_set(f)
            p = os.path.join(OUT, "frames", name, "%03d.png" % f)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            frames.append({"path": p, "t": round((f - 1) * S, 3)})
    report["clips"][name] = {"about": clip["about"], "seconds": clip["len"], "frames": n, "fbx": fbx, "action": act.name,
                             "beats": {c: clip[c] for c in chans}, "checks": checks, "all_pass": all(c["pass"] for c in checks),
                             "render": frames, "slow": clip.get("slow", 1), "view": clip["view"]}
    print("MODEL LAB CLIP %s: %d frames, %d checks, all pass %s" % (name, n, len(checks), report["clips"][name]["all_pass"]))
arm.animation_data.action = bpy.data.actions.get("%s_Cycle" % NAME)
json.dump(report, open(os.path.join(OUT, "clips.json"), "w", encoding="utf-8"), indent=1)
print("MODEL LAB CLIPS DONE")
