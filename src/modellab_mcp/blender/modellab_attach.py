"""Model Lab's attachments: the parts a real AR-15 takes on its rails and the M-LOK slots.
Each is drawn in its own frame, gun cm as the gun: +X its left, +Y forward, +Z away from the rail. The origin is the
centre of its recoil lug, on the rail's top surface (or, on M-LOK, the slot's centre on the handguard face). A build
mounts each one on a socket (a rail and a slot), exports it alone with that origin, and checks it: on its rail, clear
of the gun and of the others through all its moves, its sight on the iron sight line.

The catalogue below is plain data (ttools reads it without Blender); the drawing needs Blender and a modellab_parts Kit.

Numbers with a source are marked; the rest are estimates from photographs and listings, at real proportions.
  Picatinny: MIL-STD-1913, slots every 0.394 in, 0.206 in wide (as the gun's rails)
  M-LOK: slots 32 mm long, 7 mm wide, 40 mm apart centre to centre (the published spec)
  co-witness: the optic's axis at the iron sight line, about 1.41 in over a flattop rail for an absolute co-witness
  (the common figure; this model's sight line is SIGHT_Z over the bore)
  red dot: a 30 mm tube sight about 120 mm long, flip caps (the M68 CCO class)
  holographic: about 96 mm long, its window about 30 by 23 mm, a battery base under it
  magnifier: 3x, about 110 mm long, on a mount that flips it to the side
  prism 4x: a 4x32 fixed prism sight about 150 mm long, its axis about 1.1 in over the rail, under the iron line
  flip sights: folding backup sights, about 1.5 in (rear) and 1.25 in (front) long on the rail
  carry handle: the M4's detachable carry handle with the A2 rear sight, two thumb screws, about 6.3 in long
"""
import math

IN = 2.54
PIC_PITCH = 0.394 * IN
MLOK = {"length": 3.2, "width": 0.7, "pitch": 4.0}

# kind: what it is to the sight checks. axis: "co_witness" (its sight axis on the iron sight line) or a height over
# the rail (cm). base: the clamp's extent along the rail (cm, from its lug: rear, front). states: its rest state first
# (as drawn and exported), then the moved one; default: the state a build shows. moving: bone -> what moves.
ITEMS = {
    "flip_rear": {"kind": "iron_rear", "mount": ["picatinny"], "rails": ["upper", "hg_top"], "place": "rear",
                  "axis": "co_witness", "base": (-1.9, 1.9), "states": ["up", "down"], "default": "up",
                  "moving": {"Leaf": "folds forward flat on its base, 90 degrees about the gun's X"},
                  "about": "a folding rear sight with an aperture (backup iron sight)"},
    "flip_front": {"kind": "iron_front", "mount": ["picatinny"], "rails": ["hg_top"], "place": "front",
                   "axis": "co_witness", "base": (-1.6, 1.6), "states": ["up", "down"], "default": "up",
                   "moving": {"Leaf": "folds back flat on its base, 90 degrees about the gun's X"},
                   "about": "a folding front sight post with its protective ears (backup iron sight)"},
    "carry_handle": {"kind": "iron_rear", "mount": ["picatinny"], "rails": ["upper"], "place": "rear",
                     "axis": "co_witness", "base": (-10.5, 5.5), "states": [], "default": None, "moving": {},
                     "about": "the M4's detachable carry handle: the A2 rear sight, two thumb screws on the left"},
    "red_dot": {"kind": "optic", "mount": ["picatinny"], "rails": ["upper"], "place": "front",
                "axis": "co_witness", "base": (-2.3, 2.3), "states": ["closed", "open"], "default": "open",
                "moving": {"Cap_Front": "the front lens cap flips up and forward", "Cap_Rear": "the rear lens cap flips up and back"},
                "about": "a 30 mm tube red dot sight on a riser for an absolute co-witness, flip lens caps"},
    "holo": {"kind": "optic", "mount": ["picatinny"], "rails": ["upper"], "place": "front",
             "axis": "co_witness", "base": (-2.0, 2.0), "states": [], "default": None, "moving": {},
             "about": "a holographic sight: a battery base, a hooded window, buttons on the left"},
    "magnifier": {"kind": "magnifier", "mount": ["picatinny"], "rails": ["upper"], "place": "rear",
                  "axis": "co_witness", "base": (-1.8, 1.8), "states": ["inline", "aside"], "default": "inline",
                  "moving": {"Flip": "the mount swings the magnifier 90 degrees to the side, about the gun's Y"},
                  "options": {"flip": ["right", "left"]},
                  "about": "a 3x magnifier behind a red dot or holo, on a mount that flips it to the side"},
    "prism_4x": {"kind": "optic_low", "mount": ["picatinny"], "rails": ["upper"], "place": "rear",
                 "axis": 2.8, "base": (-2.5, 2.5), "states": [], "default": None, "moving": {},
                 "about": "a 4x32 prism sight on its own flattop mount; its axis sits under the iron sight line"},
    "vertical_grip": {"kind": "grip", "mount": ["picatinny", "mlok"], "rails": ["hg_bottom", "mlok_bottom"], "place": "middle",
                      "axis": None, "base": (-2.0, 2.0), "states": [], "default": None, "moving": {},
                      "about": "a vertical foregrip, stippled, under the handguard"},
    "weapon_light": {"kind": "light", "mount": ["picatinny", "mlok"], "rails": ["hg_right", "mlok_right", "hg_left", "mlok_left"],
                     "place": "front", "axis": None, "base": (-1.5, 1.5), "states": [], "default": None, "moving": {},
                     "about": "a weapon light on an offset mount, its tail switch at the back"},
}
FACES = {"top": 0.0, "left": 90.0, "right": -90.0, "bottom": 180.0}   # the turn about the gun's Y (Blender frame)


def entries(raw, p):
    """The build's attachment list: raw as given (names or {item, rail, slot, state, options}), or, when it is None,
    the backup sights the parameters ask for."""
    if raw is None:
        raw = []
        if p.get("upper") == "flattop" and p.get("rear_sight") == "flip":
            raw.append("flip_rear")
        if p.get("front_sight") == "flip":
            raw.append("flip_front")
    out = []
    for e in raw:
        e = {"item": e} if isinstance(e, str) else dict(e)
        out.append(e)
    return out


def validate(raw):
    """Errors in an attachments parameter, before any build (the rails are known only to the build)."""
    bad = []
    if raw is None:
        return bad
    if not isinstance(raw, list):
        return ["attachments must be a list, got %r" % (raw,)]
    for e in raw:
        e = {"item": e} if isinstance(e, str) else e
        if not isinstance(e, dict) or e.get("item") not in ITEMS:
            bad.append("attachment %r: item must be one of %s" % (e, ", ".join(ITEMS)))
            continue
        it = ITEMS[e["item"]]
        s = e.get("slot")
        if s is not None and not (isinstance(s, int) or s in ("front", "rear", "middle")):
            bad.append("%s: slot must be a number or front, rear, middle, got %r" % (e["item"], s))
        if e.get("state") is not None and e["state"] not in it["states"]:
            bad.append("%s: state must be one of %s, got %r" % (e["item"], it["states"] or "(none: it does not move)", e["state"]))
        for k, v in (e.get("options") or {}).items():
            if v not in it.get("options", {}).get(k, []):
                bad.append("%s: option %s must be one of %s, got %r" % (e["item"], k, it.get("options", {}).get(k, []), v))
    return bad


def resolve(items, rails):
    """Puts each attachment on a rail slot. items: from entries(); rails: the gun's rails. Returns (mounts, problems):
    a mount {item, name, rail, slot, y, state, options}; a problem says why an attachment found no place."""
    by = {r["name"]: r for r in rails}
    taken = {}   # rail -> [(y0, y1)]
    mounts, problems = [], []
    seen = {}
    # explicit slots first, then the rest in order
    order = sorted(range(len(items)), key=lambda i: 0 if isinstance(items[i].get("slot"), int) else 1)
    for i in order:
        e = items[i]
        it = ITEMS[e["item"]]
        seen[e["item"]] = seen.get(e["item"], 0) + 1
        name = e["item"] if seen[e["item"]] == 1 else "%s_%d" % (e["item"], seen[e["item"]])
        if e.get("rail"):
            rail = by.get(e["rail"])
            if rail is None:
                problems.append({"item": name, "why": "the gun has no rail %r; it has %s" % (e["rail"], ", ".join(by) or "none")})
                continue
        else:
            rail = next((by[r] for r in it["rails"] if r in by), None)
            if rail is None:
                problems.append({"item": name, "why": "the gun has none of the rails it fits (%s)" % ", ".join(it["rails"])})
                continue
        if rail["type"] not in it["mount"]:
            problems.append({"item": name, "why": "it mounts on %s, rail %s is %s" % (" or ".join(it["mount"]), rail["name"], rail["type"])})
            continue
        b0, b1 = it["base"]
        fits = []
        for k, y in enumerate(rail["slots"]):
            if y + b0 >= rail["y0"] - 0.01 and y + b1 <= rail["y1"] + 0.01:
                fits.append(k)
        free = [k for k in fits if all(rail["slots"][k] + b1 <= a or rail["slots"][k] + b0 >= b for a, b in taken.get(rail["name"], []))]
        s = e.get("slot", it["place"])
        if isinstance(s, int):
            if s not in fits:
                problems.append({"item": name, "why": "slot %d of rail %s leaves its base off the rail (slots that fit: %s)" % (
                    s, rail["name"], _span(fits))})
                continue
            if s not in free:
                problems.append({"item": name, "why": "slot %d of rail %s is under another attachment" % (s, rail["name"])})
                continue
            k = s
        else:
            if not free:
                problems.append({"item": name, "why": "no free slot on rail %s" % rail["name"]})
                continue
            k = free[0] if s == "rear" else free[-1] if s == "front" else free[len(free) // 2]
        y = rail["slots"][k]
        taken.setdefault(rail["name"], []).append((y + b0, y + b1))
        state = e.get("state") or it["default"]
        mounts.append({"item": e["item"], "name": name, "rail": rail["name"], "face": rail["face"], "type": rail["type"],
                       "slot": k, "y": round(y, 3), "surface": rail["surface"], "state": state,
                       "options": dict(e.get("options") or {})})
    return mounts, problems


def _span(ks):
    return "%d to %d" % (ks[0], ks[-1]) if ks else "none"


def socket(m):
    """A mount's place in gun space: (point, turn about the gun's Y in degrees, Blender frame)."""
    s, y = m["surface"] + 0.01, m["y"]   # a hair off the surface: resting on it, not through it
    at = {"top": (0.0, y, s), "bottom": (0.0, y, -s), "left": (s, y, 0.0), "right": (-s, y, 0.0)}[m["face"]]
    return at, FACES[m["face"]]


# --- the drawing (Blender) ------------------------------------------------------------------------------------------
def _ring_y(y, x, z, a, b, n=20, p=2.0):
    from modellab_parts import ring
    return ring((x, y, z), (1, 0, 0), (0, 0, 1), a, b, n, p)


def _ring_z(z, x, y, a, b, n=20, p=2.0):
    from modellab_parts import ring
    return ring((x, y, z), (1, 0, 0), (0, 1, 0), a, b, n, p)


def _clamp(kit, y0, y1, mat, bone="Root", screw_side=-1, lever=False):
    """A Picatinny clamp: the plate on the rail, its jaws down both sides of the dovetail, the recoil lug in the slot
    under the origin, the cross bolt (or a throw lever) on one side."""
    kit.prism("Clamp", [(-1.32, 0.0), (1.32, 0.0), (1.32, 0.5), (1.1, 0.72), (-1.1, 0.72), (-1.32, 0.5)], 'y', y0, y1, mat, bone,
              bevel=0.05, round_r=0.12)
    for sx in (1, -1):
        kit.prism("Clamp_Jaw", [(sx * 1.13, -0.3), (sx * 1.34, -0.3), (sx * 1.34, 0.02), (sx * 1.13, 0.02)], 'y', y0 + 0.1, y1 - 0.1,
                  mat, bone, bevel=0.03)
    kit.box("Clamp_Lug", (-0.8, -0.18, -0.28), (0.8, 0.18, 0.02), "Steel", bone, bevel=0.02)
    x0 = screw_side * 1.34
    if lever:
        kit.prism("Clamp_Lever", [(-1.0, 0.05), (1.8, 0.05), (1.8, 0.55), (-1.0, 0.45)], 'x', x0, x0 + screw_side * 0.28, "Detail", bone,
                  bevel=0.04, round_r=0.15)
    else:
        kit.tube_x("Clamp_Bolt", x0, x0 + screw_side * 0.35, 0.33, 0.0, 0.25, mat="Steel", bone=bone, verts=6)


def _mlok(kit, y0, y1, mat, bone="Root"):
    """An M-LOK base: the plate on the handguard face, its two T-nuts in the slot under the origin, their screw heads."""
    kit.prism("Mlok_Base", [(-1.1, 0.0), (1.1, 0.0), (1.1, 0.45), (0.85, 0.65), (-0.85, 0.65), (-1.1, 0.45)], 'y', y0, y1, mat, bone,
              bevel=0.05, round_r=0.15)
    for y in (-0.8, 0.8):
        kit.box("Mlok_TNut", (-0.28, y - 0.35, -0.28), (0.28, y + 0.35, 0.02), "Steel", bone, bevel=0.02)


def _mount(kit, m, b0, b1, mat, **kw):
    if m["type"] == "mlok":
        _mlok(kit, max(b0, -1.5), min(b1, 1.5), mat)
    else:
        _clamp(kit, b0, b1, mat, **kw)


def _hollow(kit, ob, z, r, x=0.0):
    """Bores a housing along its sight axis (y), so the eye looks through the optic, lens to lens."""
    bore = kit.rod("_bore", (x, -40.0, z), (x, 40.0, z), r, mat="Optic", bone="_cut", n=28)
    kit.cut(ob, None, None, cutter=bore)
    kit.__dict__.setdefault("bores", []).append((x, z, r))   # the build keeps the bore's walls unworn: no hand rubs them
    return ob


def _aperture(kit, name, y, z, r_out, r_hole, mat, bone, thick=0.25):
    disk = kit.tube(name, y - thick / 2, y + thick / 2, r_out, z=z, mat=mat, bone=bone, verts=20)
    hole = kit.rod("_hole", (0, y - 1.0, z), (0, y + 1.0, z), r_hole, mat=mat, bone="_cut", n=12)
    kit.cut(disk, None, None, cutter=hole)
    return disk


def build(kit, m, ax):
    """Draws mount m's attachment into kit in its own frame. ax: the height of the iron sight line over its rail (cm).
    Returns (bones [(bone, head, parent)], moves {bone: (kind, axis, amount)}, info)."""
    it = ITEMS[m["item"]]
    f = globals()["_draw_" + m["item"]]
    a = ax if it["axis"] == "co_witness" else it["axis"]
    bones, moves = f(kit, m, a)
    return [("Root", (0, 0, 0), None)] + bones, moves, {"axis_over_rail": a}


def _draw_flip_rear(kit, m, a):
    _clamp(kit, -1.9, 1.9, "Detail")
    kit.prism("Rear_Base", [(-1.9, 0.6), (1.9, 0.6), (1.6, 1.0), (-1.6, 1.0)], 'x', -1.1, 1.1, "Detail", "Root", bevel=0.05, round_r=0.15)
    # the leaf stands at the base's rear, its hinge on the rear top edge: it folds forward and lies flat on the base
    hinge = (0.0, -1.45, 1.05)
    for x0, x1 in ((0.45, 0.82), (-0.82, -0.45)):
        kit.prism("Rear_Ear", [(-1.7, 1.0), (-0.8, 1.0), (-0.95, a + 0.6), (-1.55, a + 0.6)], 'x', x0, x1, "Detail", "Leaf",
                  bevel=0.03, round_r=0.12)
    kit.box("Rear_Leaf", (-0.5, -1.4, 1.0), (0.5, -1.15, a - 0.38), "Detail", "Leaf", bevel=0.02)
    _aperture(kit, "Rear_Aperture", -1.27, a, 0.45, 0.1, "Detail", "Leaf")
    kit.tube_x("Rear_Knob", -1.1, -1.55, 0.32, 0.6, 0.85, mat="Detail")
    return [("Leaf", hinge, "Root")], {"Leaf": ("turn", (1, 0, 0), 90.0)}


def _draw_flip_front(kit, m, a):
    _clamp(kit, -1.6, 1.6, "Detail")
    kit.prism("Front_Base", [(-1.6, 0.6), (1.6, 0.6), (1.35, 1.0), (-1.35, 1.0)], 'x', -1.05, 1.05, "Detail", "Root", bevel=0.05, round_r=0.15)
    # the post stands at the base's front, hinged on the front top edge: it folds back and lies flat on the base
    hinge = (0.0, 1.25, 1.05)
    for x0, x1 in ((0.45, 0.8), (-0.8, -0.45)):
        kit.prism("Front_Ear", [(0.6, 1.0), (1.45, 1.0), (1.3, a + 0.42), (0.8, a + 0.42)], 'x', x0, x1, "Detail", "Leaf",
                  bevel=0.03, round_r=0.1)
    kit.box("Front_Leaf", (-0.48, 0.75, 1.0), (0.48, 1.4, 1.6), "Detail", "Leaf", bevel=0.03)
    kit.box("Front_Post", (-0.11, 0.95, 1.5), (0.11, 1.19, a), "Detail", "Leaf", bevel=0.02)
    return [("Leaf", hinge, "Root")], {"Leaf": ("turn", (1, 0, 0), -90.0)}


def _draw_carry_handle(kit, m, a):
    _clamp(kit, -10.5, 5.5, "Optic", screw_side=1)
    handle = kit.prism("Handle", [(-10.2, 0.6), (5.3, 0.6), (4.0, a - 1.05), (-9.7, a - 0.5)], 'x', -0.95, 0.95, "Optic", "Root",
                       bevel=0.12, round_r=0.45)
    kit.cut(handle, (-1.5, -7.6, 1.05), (1.5, 2.0, a - 1.9))
    housing = kit.prism("Rear_Housing", [(-10.5, a - 0.65), (-8.2, a - 0.65), (-8.5, a + 0.6), (-10.2, a + 0.6)], 'x', -0.8, 0.8,
                        "Optic", "Root", bevel=0.05, round_r=0.2)
    kit.cut(housing, (-0.45, -10.6, a - 0.12), (0.45, -8.1, a + 0.7))
    _aperture(kit, "Rear_Aperture", -9.4, a, 0.42, 0.1, "Detail", "Root")
    kit.tube_x("Rear_Windage", -1.15, 1.15, 0.38, -9.1, a - 0.38, mat="Detail")
    kit.rod("Rear_Elevation", (0, -9.4, a - 1.35), (0, -9.4, a - 0.68), 0.75, mat="Detail", bone="Root", n=20)
    for y in (-3.2, 2.6):            # the two thumb screws on the left
        kit.tube_x("Thumb_Screw", 1.34, 1.95, 0.55, y, 0.3, mat="Detail", verts=12)
    return [], {}


def _draw_red_dot(kit, m, a):
    _clamp(kit, -2.3, 2.3, "Optic", lever=True)
    kit.prism("Riser", [(-2.0, 0.6), (2.0, 0.6), (1.4, a - 1.5), (-1.4, a - 1.5)], 'x', -0.95, 0.95, "Optic", "Root", bevel=0.08, round_r=0.3)
    for ob in (kit.tube("Ring", -1.2, 1.2, 1.9, z=a, mat="Optic", verts=28, bevel=0.06),
               kit.tube("Body", -5.4, 4.6, 1.55, z=a, mat="Optic", verts=28),
               kit.tube("Objective", 4.5, 6.0, 1.62, 1.75, z=a, mat="Optic", verts=28, bevel=0.05),
               kit.tube("Ocular", -6.0, -4.9, 1.72, 1.62, z=a, mat="Optic", verts=28, bevel=0.05)):
        _hollow(kit, ob, a, 1.38)
    kit.tube("Lens_Front", 5.9, 5.98, 1.45, z=a, mat="Lens", verts=28)
    kit.tube("Lens_Rear", -5.98, -5.9, 1.45, z=a, mat="Glass", verts=28)
    kit.rod("Turret_Top", (0, -0.6, a + 1.4), (0, -0.6, a + 2.15), 0.62, mat="Optic", bone="Root", n=16)
    kit.tube_x("Turret_Right", -1.4, -2.15, 0.62, -0.6, a, mat="Optic", verts=16)
    kit.tube("Battery", -2.4, 2.6, 0.55, x=-1.25, z=a - 1.15, mat="Optic", verts=16)
    kit.tube_x("Battery_Knob", -1.5, -2.25, 0.45, 2.9, a - 1.15, mat="Detail", verts=16)
    # the flip caps, closed as drawn: each on its hinge over the lens
    kit.tube("Cap_Front", 6.0, 6.45, 1.85, z=a, mat="Rubber", bone="Cap_Front", verts=24)
    kit.box("Cap_Front_Tab", (-0.5, 6.0, a + 1.75), (0.5, 6.45, a + 2.25), "Rubber", "Cap_Front", bevel=0.05)
    kit.tube("Cap_Rear", -6.45, -6.0, 1.85, z=a, mat="Rubber", bone="Cap_Rear", verts=24)
    kit.box("Cap_Rear_Tab", (-0.5, -6.45, a + 1.75), (0.5, -6.0, a + 2.25), "Rubber", "Cap_Rear", bevel=0.05)
    return ([("Cap_Front", (0.0, 6.25, a + 1.95), "Root"), ("Cap_Rear", (0.0, -6.25, a + 1.95), "Root")],
            {"Cap_Front": ("turn", (1, 0, 0), -115.0), "Cap_Rear": ("turn", (1, 0, 0), 115.0)})


def _draw_holo(kit, m, a):
    _clamp(kit, -2.0, 2.0, "Optic", screw_side=1, lever=True)
    kit.prism("Base", [(-1.6, 0.5), (1.6, 0.5), (1.6, 1.55), (1.35, 1.8), (-1.35, 1.8), (-1.6, 1.55)], 'y', -4.8, 4.6, "Optic", "Root",
              bevel=0.08, round_r=0.25)
    hood = kit.prism("Hood", [(-2.25, 1.6), (2.25, 1.6), (2.25, a + 1.2), (1.7, a + 1.65), (-1.7, a + 1.65), (-2.25, a + 1.2)], 'y',
                     -2.9, 2.1, "Optic", "Root", bevel=0.08, round_r=0.45)
    kit.cut(hood, (-1.5, -3.5, a - 1.15), (1.5, 2.7, a + 1.15))
    kit.box("Window_Rear", (-1.5, -2.55, a - 1.15), (1.5, -2.5, a + 1.15), "Glass", "Root", bevel=0.0)
    kit.box("Window_Front", (-1.5, 1.7, a - 1.15), (1.5, 1.75, a + 1.15), "Lens", "Root", bevel=0.0)
    for y in (-4.0, -3.2):      # the buttons on the left
        kit.tube_x("Button", 1.6, 1.78, 0.28, y, 1.05, mat="Rubber", verts=12)
    for y in (3.2, 3.9):        # windage and elevation on the right
        kit.tube_x("Adjuster", -1.6, -1.82, 0.32, y, 1.05, mat="Detail", verts=12)
    return [], {}


def _draw_magnifier(kit, m, a):
    side = 1 if m["options"].get("flip", "right") == "left" else -1      # +1 swings to the gun's left
    _clamp(kit, -1.8, 1.8, "Optic", screw_side=-side, lever=True)
    pivot = (side * 1.2, 0.0, 1.0)
    kit.prism("Mount_Block", [(-1.32, 0.6), (1.32, 0.6), (1.32, 1.3), (-1.32, 1.3)], 'y', -1.6, 1.6, "Optic", "Root", bevel=0.06)
    kit.tube("Pivot", -1.7, 1.7, 0.32, x=pivot[0], z=pivot[2], mat="Steel", verts=12)
    kit.prism("Arm", [(-1.1, 1.2), (1.1, 1.2), (0.95, a - 1.45), (-0.95, a - 1.45)], 'y', -1.3, 1.3, "Optic", "Flip", bevel=0.06, round_r=0.2)
    for ob in (kit.tube("Ring", -1.1, 1.1, 1.85, z=a, mat="Optic", bone="Flip", verts=28, bevel=0.05),
               kit.tube("Body", -4.0, 4.4, 1.5, 1.42, z=a, mat="Optic", bone="Flip", verts=28),
               kit.tube("Eyepiece", -5.7, -3.9, 1.85, 1.6, z=a, mat="Optic", bone="Flip", verts=28, bevel=0.05),
               kit.tube("Diopter", -6.1, -5.6, 1.9, z=a, mat="Rubber", bone="Flip", verts=28)):
        _hollow(kit, ob, a, 1.22)
    kit.tube("Lens_Front", 4.35, 4.42, 1.3, z=a, mat="Glass", bone="Flip", verts=24)
    kit.tube("Lens_Rear", -6.12, -6.05, 1.55, z=a, mat="Glass", bone="Flip", verts=24)
    return [("Flip", pivot, "Root")], {"Flip": ("turn", (0, 1, 0), side * 90.0)}


def _draw_prism_4x(kit, m, a):
    _clamp(kit, -2.5, 2.5, "Optic", screw_side=1)
    for y in (-1.5, 1.5):
        kit.tube_x("Thumb_Screw", 1.34, 1.9, 0.5, y, 0.3, mat="Detail", verts=12)
    kit.prism("Mount", [(-2.4, 0.6), (2.4, 0.6), (2.1, a - 1.2), (-2.1, a - 1.2)], 'x', -1.2, 1.2, "Optic", "Root", bevel=0.06, round_r=0.25)
    for ob in (kit.prism("Housing", [(-5.5, a - 1.45), (4.0, a - 1.45), (4.6, a - 0.2), (4.0, a + 1.5), (-1.0, a + 1.75), (-5.5, a + 1.3)],
                         'x', -1.45, 1.45, "Optic", "Root", bevel=0.1, round_r=0.5),
               kit.tube("Eyepiece", -7.5, -5.3, 1.45, 1.3, z=a, mat="Optic", verts=28, bevel=0.05),
               kit.tube("Objective", 4.0, 7.4, 2.05, z=a, mat="Optic", verts=28, bevel=0.05)):
        _hollow(kit, ob, a, 1.02)
    kit.tube("Lens_Front", 7.0, 7.05, 1.8, z=a, mat="Glass", verts=28)
    kit.tube("Lens_Rear", -7.52, -7.47, 1.1, z=a, mat="Glass", verts=24)
    kit.box("Fiber", (-0.25, -4.5, a + 1.3), (0.25, 3.0, a + 1.75), "Detail", "Root", bevel=0.05)
    kit.rod("Turret_Top", (0, 1.8, a + 1.45), (0, 1.8, a + 2.0), 0.55, mat="Optic", bone="Root", n=16)
    kit.tube_x("Turret_Right", -1.45, -2.0, 0.55, 1.8, a, mat="Optic", verts=16)
    return [], {}


def _draw_vertical_grip(kit, m, a):
    _mount(kit, m, -2.0, 2.0, "Furniture")
    rings = [_ring_z(z, 0.0, 0.0, r, r * 1.05, n=24) for z, r in ((0.6, 1.5), (1.4, 1.65), (5.0, 1.55), (8.6, 1.5), (9.6, 1.6), (10.0, 1.3))]
    grip = kit.loft("Grip", rings, "Furniture", "Root", subdiv=1)
    for side in (1, -1):
        kit.texture("Grip_Stipple", grip, (0.0, 0.0, 5.2), (0, 0, 1), (0, 1, 0), 3.4, 1.2, side, "stippled", pitch=0.17, depth=0.05,
                    mat="Furniture", seed=11 + side)
    return [], {}


def _draw_weapon_light(kit, m, a):
    _mount(kit, m, -1.5, 1.5, "Optic")
    kit.prism("Offset", [(-1.4, 0.6), (1.4, 0.6), (1.1, 1.2), (-1.1, 1.2)], 'x', -0.9, 0.9, "Optic", "Root", bevel=0.05, round_r=0.2)
    z = 1.2 + 1.25
    kit.tube("Body", -5.8, 4.2, 1.25, z=z, mat="Optic", verts=24)
    kit.tube("Head", 4.2, 6.6, 1.3, 1.62, z=z, mat="Optic", verts=24, bevel=0.05)
    kit.tube("Lens", 6.55, 6.6, 1.42, z=z, mat="Glass", verts=24)
    kit.tube("Tailcap", -6.6, -5.8, 1.32, z=z, mat="Detail", verts=16)
    kit.tube("Switch", -6.95, -6.6, 0.62, z=z, mat="Rubber", verts=16)
    return [], {}
