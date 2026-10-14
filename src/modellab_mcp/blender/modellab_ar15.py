"""Model Lab's AR-15 family (AR-15, M4A1, M16A2), in Blender: every part from parameters, in gun space (cm, +X the gun's
left, +Y forward, +Z up). The origin is the bolt face at rest on the bore: the chamber's rear. Game models only: the
outside shapes and the moving parts at real proportions, no working internals and no fabrication data.

Numbers with a source are marked; the rest are estimates, sized from photographs.
  M4: 14.5 in barrel, 33 in long with the stock out, 29.75 in with it in (Wikipedia, M4 carbine)
  M16A2: 20 in barrel, 39.63 in long (Wikipedia, M16 rifle; GlobalSecurity)
  magazine: 2.25 in front to back, 1.125 in wide (Mission First Tactical 30-round listing)
  buffer tube: 1.148 in across, mil-spec carbine (Brownells)
  port door: about 3.1 in long (Brownells)
  rail: MIL-STD-1913, 0.835 in wide, slots every 0.394 in, 0.206 in wide
  sight line: about 2.5 in over the bore with A2 sights (forum figure: an estimate)
  the lower, the trigger guard, the magazine well and the pistol grip: measured from the PEO Soldier side photo of an
  M4A1 (Wikimedia Commons, File:M4A1-flattop.jpg, public domain), scaled by its rail teeth (0.394 in apart): the lower
  5.5 cm under the bore at the guard, the guard's bottom 8.4 cm under it, its opening 2.6 by 4.5 cm, the well's front
  lip 7.0 cm under the bore, the grip from 5.5 to 15.0 cm under it, 5 cm front to back, raked 27 degrees, the RIS
  6.35 cm across
  carrier travel 8.4 cm and the catch at 7.6 cm: estimates, as build_ar15_rig.py
  colours: the common names of real finishes (anodized black, Flat Dark Earth, OD green, wolf gray, tungsten, coyote),
  as linear colours by eye: approximate"""
import math

from mathutils import Vector

IN = 2.54

# the upper and the lower (estimates at real size; the lower's depth from the M4A1 photo)
UP_FRONT, UP_REAR = 2.7, -15.3
UP_HW, UP_BOT, UP_TOP = 1.35, -1.9, 1.55
RAIL_W, RAIL_BASE, RAIL_TOP = 1.06, 2.55, 2.98      # the rail's top 2.98 cm over the bore (the M4A1 photo)
RAIL_REAR = -17.0                                     # the flattop rail runs back over the charging handle (the photo)
RAIL_PITCH, RAIL_SLOT = 0.394 * IN, 0.206 * IN
PORT = {"y": (-7.3, 0.5), "z": (-0.6, 1.4)}          # the port: 7.8 cm long, the cover a little larger
COVER = {"y": (-7.6, 0.8), "z": (-0.6, 1.6), "x": (-UP_HW - 0.12, -UP_HW)}
HINGE = (-UP_HW - 0.06, (COVER["y"][0] + COVER["y"][1]) / 2, PORT["z"][0])
COVER_OPEN_DEG = -175.0      # about the gun's Y: the most it may open; the build stops it where it meets the lower
MAG_W, MAG_LEN = 1.125 * IN, 2.25 * IN
LIPS_HW = 1.1   # the feed lips' half width: the magazine's top fits inside the upper (UP_HW 1.35)
LOWER_DY = 1.55   # the lower's parts sit 1.55 cm further forward than first drawn (the M4A1 photo: the well's front,
                  # the grip's front edge at two heights and the guard's opening all agree within 0.2 cm)
MAG_FRONT, MAG_TOP = -0.8 + LOWER_DY, -0.9           # the magazine's front wall and its feed lips
WELL_GAP, WELL_WALL, WELL_BOT = 0.12, 0.35, -7.1      # the well's lip 7.0 cm under the bore (the M4A1 photo)
LOWER_BOT, GUARD_BOT = -5.5, -8.4                      # the lower's bottom at the guard, the guard's bottom (the photo)
GRIP_RAKE = 27.0                                       # the grip's rake from upright (the photo: 28 at its front edge)
BOLT_TRAVEL, BOLT_CATCH = 8.4, 7.6
TUBE_R = 1.148 * IN / 2
TOWER = 1.2                                          # the lower's buffer tower behind the upper (estimate)
TUBE_LEN = {"carbine": 7.25 * IN, "side_tubes": 7.25 * IN, "a2": 9.625 * IN}   # carbine (estimate); A2 9 5/8 in (Brownells)
SIGHT_Z = 2.5 * IN
GAS_IN = {"carbine": 7.95, "mid": 9.0, "rifle": 12.0}  # the front sight base's middle ahead of the upper: carbine from the
                                                        # M4A1 photo (7.95 in); mid and rifle estimates
BIRDCAGE = 1.75 * IN                                   # the A2 flash hider past the crown (estimate)
STOCK_STEP = 3.25 * IN / 4                              # M4: 33 - 29.75 in over four steps
A2_PAST_TUBE = 5.07                                     # estimate, sized so the M16A2 comes to its 39.63 in
# the magazine's spine (cm along it) and its curve: straight through the well, then an arc (the M4A1 photo: the 30's
# front edge 2.4 cm ahead by 17 cm down, its floor's corners at 17.3 and 19.2 cm under the bore); the GI 20 is straight
MAG_SPINE = {30: (17.7, 27.4), 20: (12.4, None)}
MAG_BACK_CURVE = 0.6                                      # the back's share of the spine's curve (the M4A1 photo)
ROUND = {"case": 4.5, "bullet": 1.24, "r": 0.48}        # 5.56x45: 57.4 mm long, 9.6 mm across

# finishes: (linear colour, metallic, roughness); names as the trade uses them, colours approximate
COLORS = {
    "black": ((0.028, 0.028, 0.032), 0.1, 0.45), "fde": ((0.23, 0.165, 0.095), 0.1, 0.6),
    "odg": ((0.065, 0.075, 0.03), 0.1, 0.6), "wolf_gray": ((0.085, 0.088, 0.092), 0.15, 0.55),
    "tungsten": ((0.075, 0.076, 0.08), 0.25, 0.45), "coyote": ((0.21, 0.12, 0.055), 0.1, 0.6),
}
MAGAZINES = {"gi_aluminum": "the GI aluminium magazine, pressed ribs", "polymer": "a polymer magazine, its floor ribbed"}
GRIPS = {"a2": "the A2 grip with its finger nub", "beavertail": "a smooth grip without the nub, with a beavertail",
         "flared": "a grip without the nub, its base flared forward under the little finger"}
GRIP_TEXTURES = {"auto": "the grip's own: checkered on the A2, stippled on the others", "checkered": "diamond checkering",
                 "stippled": "random stipple", "none": "smooth sides"}
STOCKS = {"carbine": "the M4 collapsible stock", "side_tubes": "a stock with battery tubes down its sides (the SOPMOD class)", "a2": "the fixed A2 rifle stock"}

DEFAULTS = {
    "barrel_in": 14.5, "gas": "carbine", "handguard": "round", "handguard_in": None, "front_sight": "a2",
    "upper": "flattop", "rear_sight": "flip", "stock": "carbine", "stock_pos": 4, "magazine": 30,
    "muzzle": "a2_birdcage", "selector": ["SAFE", "SEMI", "AUTO"], "grip": "a2", "grip_texture": "auto", "magazine_type": "gi_aluminum",
    "receiver_color": "black", "furniture_color": "black", "handguard_color": None, "magazine_color": None,
}


# --- the parts table: every part a person sees on the real gun, with the features that make it read as that part ---
# The rule: a part is done when every one of its features is drawn. Each feature names the
# shapes that draw it (a shape's name, or the start of it); the build checks each one and fails a feature it cannot
# find. "when" limits a part to the builds that have it. "texture" lists what a real part carries as marks or
# finish, not shape (engraved numbers, letters): listed, not drawn. New detail starts here: add the feature, then
# draw it. The real-gun outline check (modellab_refs, the compare tool) finds what this list does not know yet.
PARTS = [
    {"part": "upper receiver", "features": {"body": ["Upper"], "barrel nut ring": ["Upper_Ring"], "brass deflector": ["Upper_Deflector"],
                                             "forward assist housing": ["Upper_FA_Housing"]}},
    {"part": "flattop rail", "when": lambda p: p["upper"] == "flattop",
     "features": {"rail base": ["Rail_Base"], "dovetail teeth": ["Rail_Tooth"]}, "texture": ["slot numbers (T-marks)"]},
    {"part": "carry handle upper", "when": lambda p: p["upper"] == "carry_handle",
     "features": {"handle": ["Upper_CarryHandle"], "rear sight housing": ["Rear_Housing"], "aperture": ["Rear_Aperture"],
                  "windage knob": ["Rear_Windage"]}},
    {"part": "forward assist", "features": {"button": ["ForwardAssist"], "grooves": ["ForwardAssist_Groove"]}},
    {"part": "ejection port cover", "features": {"door": ["DustCover_Plate"], "stamped rib": ["DustCover_Rib"], "hinge rod": ["DustCover_Rod"],
                                                  "E-clip on the rod": ["DustCover_Clip"]}},
    {"part": "charging handle", "features": {"stem": ["Charging_Shaft"], "hub": ["Charging_Hub"], "swept wing with finger hook": ["Charging_Wing"],
                                              "latch": ["Charging_Latch"], "finger ridges": ["Charging_Wing_Ridge"],
                                              "latch serrations": ["Charging_Latch_Serration"], "latch roll pin": ["Charging_Latch_Pin"]}},
    {"part": "bolt carrier group (through the port)", "features": {"carrier": ["Bolt_Carrier"], "bolt head": ["Bolt_Head"], "gas key": ["Bolt_GasKey"],
                                                                   "forward assist notches": ["Bolt_Carrier_Notch"], "extractor": ["Bolt_Extractor"]}},
    {"part": "lower receiver", "features": {"body": ["Lower"], "magazine well": ["Lower_Well"], "buffer tower": ["Lower_Tower"],
                                             "pivot pin head": ["Pin_Pivot_Head"], "takedown pin head": ["Pin_Takedown_Head"],
                                             "hammer and trigger pins": ["Pin"]}, "texture": ["selector marks (SAFE, SEMI, AUTO)", "roll marks"]},
    {"part": "trigger guard", "features": {"guard": ["Guard"], "rear roll pin": ["Guard_Pin"], "front detent": ["Guard_Detent"]}},
    {"part": "trigger", "features": {"blade": ["Trigger"]}},
    {"part": "selector", "features": {"hub": ["Selector_Hub"], "lever": ["Selector_Lever"], "right end": ["Selector_Nub"]}},
    {"part": "magazine catch", "features": {"button": ["MagRelease"], "fence": ["MagRelease_Fence"], "left end": ["MagCatch"]}},
    {"part": "bolt catch", "features": {"catch": ["BoltCatch"], "roll pin": ["BoltCatch_Pin"], "paddle serrations": ["BoltCatch_Serration"]}},
    {"part": "pistol grip", "features": {"grip": ["Grip"], "grip screw": ["Grip_Screw"]}},
    {"part": "grip texture", "when": lambda p: p.get("grip_texture", "auto") != "none",
     "features": {"checkering or stipple": ["Grip_Checkering", "Grip_Stipple"]}},
    {"part": "buffer tube", "features": {"tube": ["Buffer_Tube"], "castle nut": ["Castle_Nut"], "castle nut notches": ["Castle_Nut_Notch"],
                                          "end plate": ["End_Plate"]}},
    {"part": "carbine buffer tube", "when": lambda p: p["stock"] in ("carbine", "side_tubes"),
     "features": {"keyway rib": ["Buffer_Tube_Key"], "position holes": ["Buffer_Tube_Hole"]}},
    {"part": "carbine stock", "when": lambda p: p["stock"] in ("carbine", "side_tubes"),
     "features": {"body": ["Stock_Body"], "side recesses": ["Stock_Recess"], "butt sling slot": ["Stock_SlingSlot"], "butt pad": ["Stock_Pad"],
                  "rim on the sloped edge": ["Stock_Ridge"], "lock lever": ["Stock_Lever"], "sling loop": ["Stock_SlingLoop"]}},
    {"part": "A2 stock", "when": lambda p: p["stock"] == "a2", "features": {"body": ["Stock_Body"], "butt plate": ["Stock_Plate"],
                                                                            "trap door": ["Stock_TrapDoor"]}},
    {"part": "barrel", "features": {"barrel": ["Barrel"], "barrel nut": ["Barrel_Nut"]}},
    {"part": "M4 barrel profile", "when": lambda p: p["front_sight"] == "a2" and p["gas"] == "carbine",
     "features": {"M203 cut": ["Barrel_M203_Cut"]}},
    {"part": "front sight base", "when": lambda p: p["front_sight"] == "a2",
     "features": {"clamp": ["FSB_Clamp"], "tower": ["FSB_Tower"], "protective wings": ["FSB_Wing"], "post": ["FSB_Post"],
                  "bayonet lug": ["FSB_Lug"], "sling swivel": ["FSB_Swivel"], "swivel loop": ["FSB_SwivelLoop"],
                  "taper pins": ["FSB_Pin"]}},
    {"part": "gas block", "when": lambda p: p["front_sight"] != "a2", "features": {"block": ["Gas_Block"]}},
    {"part": "round handguard", "when": lambda p: p["handguard"] == "round",
     "features": {"shell": ["Handguard"], "ribs": ["Handguard_Rib"], "vent holes": ["Handguard_Vent"], "delta ring": ["Handguard_Ring"],
                  "cap": ["Handguard_Cap"]}},
    {"part": "quad rail", "when": lambda p: p["handguard"] == "quad_rail",
     "features": {"body": ["Handguard"], "rails": ["HG_Tooth"], "cross bolts": ["HG_Bolt"]}, "texture": ["slot numbers"]},
    {"part": "M-LOK handguard", "when": lambda p: p["handguard"] == "mlok",
     "features": {"body": ["Handguard"], "top rail": ["HG_Tooth"]}},
    {"part": "A2 flash hider", "when": lambda p: p["muzzle"] == "a2_birdcage",
     "features": {"birdcage": ["Muzzle_Device"], "crown": ["Muzzle_Crown"], "peel washer": ["Muzzle_Washer"]}},
    {"part": "magazine", "features": {"body": ["Magazine_Body"], "feed lips": ["Magazine_Lips"], "floor plate": ["Magazine_Floor"],
                                       "catch slot": ["Magazine_CatchSlot"], "top round": ["Round_Case", "Round_Bullet"]}},
    {"part": "GI magazine", "when": lambda p: p["magazine_type"] == "gi_aluminum", "features": {"pressed ribs": ["Magazine_Rib"]}},
    {"part": "polymer magazine", "when": lambda p: p["magazine_type"] == "polymer", "features": {"floor plate ribs": ["Magazine_FloorRib"]}},
]


def parts_check(p, names):
    """Each part this build has, each of its features drawn or missing. names: the shape names the build drew."""
    out = []
    for part in PARTS:
        if "when" in part and not part["when"](p):
            continue
        # a shape counts for a feature when its name is the feature's name, or that name and "_<more>"
        feats = {f: any(n == pre or n.startswith(pre + "_") for n in names for pre in pres) for f, pres in part["features"].items()}
        out.append({"part": part["part"], "features": feats, "missing": [f for f, ok in feats.items() if not ok],
                    "texture": part.get("texture", [])})
    return out



def fill(p):
    p = dict(DEFAULTS, **{k: v for k, v in (p or {}).items() if v is not None})
    if p.get("handguard_color") is None:
        p["handguard_color"] = p["furniture_color"] if p["handguard"] == "round" else p["receiver_color"]
    if p.get("magazine_color") is None:
        p["magazine_color"] = "wolf_gray" if p["magazine_type"] == "gi_aluminum" else "black"
    return p


def materials(p):
    """The build's material slots, coloured from the finish parameters."""
    p = fill(p)
    alu, steel = (0.55, 0.56, 0.58), (0.32, 0.32, 0.33)   # the bare metal under a worn finish
    rail_hg = p["handguard"] != "round"
    gi = p["magazine_type"] == "gi_aluminum"
    return {"Receiver": COLORS[p["receiver_color"]] + (alu,), "Furniture": COLORS[p["furniture_color"]],
            # finer slots for coatings (slot_of): the upper and the lower are two forgings, often finished apart; the
            # barrel assembly takes its own finish (phosphate, nitride, stainless) apart from the bolt group
            "Upper": COLORS[p["receiver_color"]] + (alu,), "Lower": COLORS[p["receiver_color"]] + (alu,),
            "Barrel": ((0.05, 0.05, 0.052), 0.75, 0.38, steel),
            "Handguard": COLORS[p["handguard_color"]] + ((alu,) if rail_hg else ()),
            "Magazine": COLORS[p["magazine_color"]] + ((alu,) if gi else ()),
            "Steel": ((0.05, 0.05, 0.052), 0.75, 0.38, steel), "Detail": ((0.02, 0.02, 0.022), 0.4, 0.45, steel),
            "Rubber": ((0.018, 0.018, 0.018), 0.0, 0.9), "Brass": ((0.75, 0.53, 0.2), 0.95, 0.3),
            "Copper": ((0.72, 0.33, 0.16), 0.95, 0.32),
            # the attachments: anodized optic housings, plain glass, and the amber-red coated lens of a red dot
            "Optic": ((0.025, 0.025, 0.028), 0.15, 0.42, alu), "Glass": ((0.02, 0.03, 0.04), 0.0, 0.04, None, 0.18),
            "Lens": ((0.12, 0.035, 0.02), 0.0, 0.05, None, 0.3)}


LOWER_SHAPES = ("Lower", "Buffer_Tube", "Castle_Nut", "End_Plate", "Trigger_Guard", "Guard", "Takedown", "Pivot",
                "MagRelease_Fence")                   # the fences round the magazine release are the lower's forging
BARREL_SHAPES = ("Barrel", "Muzzle", "Gas_Block", "Gas_Tube", "FSB")   # the barrel nut is steel too: the barrel's group
STEEL_SHAPES = ("DustCover_Plate", "DustCover_Rib")  # the dust cover is a steel stamping, not the upper's aluminium
DETAIL_SHAPES = ("Charging_Shaft",)                   # the charging handle is its own part, with its latch (Detail)


def slot_of(name, slot):
    """A shape's coating slot: the receiver's shapes split into the upper and the lower forging, the barrel
    assembly out of the steel group (the bolt, pins and springs stay Steel), the parts that are other parts in a
    real rifle (the dust cover, the charging handle) to their own group."""
    if slot in ("Receiver", "Steel") and name.startswith(BARREL_SHAPES):
        return "Barrel"
    if slot == "Receiver":
        if name.startswith(STEEL_SHAPES):
            return "Steel"
        if name.startswith(DETAIL_SHAPES):
            return "Detail"
        return "Lower" if name.startswith(LOWER_SHAPES) else "Upper"
    return slot


def _rail(kit, name, y0, y1, base_z, face="top", mat="Receiver", rail=None):
    """A Picatinny rail's teeth (their dovetail cross-section) on one face: top, bottom, left or right. Returns the
    rail for the sockets: its slots' centres (y, from the rear: slot 0 is the rearmost) and its top surface."""
    y = y0 + 0.2
    w = RAIL_PITCH - RAIL_SLOT
    teeth = []
    prof = [(-0.86, 0.0), (0.86, 0.0), (RAIL_W, 0.17), (0.86, 0.45), (-0.86, 0.45), (-RAIL_W, 0.17)]
    while y + w < y1:
        if face == "top":
            pts = [(x, base_z + z) for x, z in prof]
        elif face == "bottom":
            pts = [(x, -base_z - z) for x, z in prof]
        else:
            sx = 1 if face == "left" else -1
            pts = [(sx * (base_z + z), x) for x, z in prof]
        kit.prism(name, pts, 'y', y, y + w, mat, "Root", bevel=0.02)
        teeth.append(y)
        y += RAIL_PITCH
    return {"name": rail or name, "type": "picatinny", "face": face, "surface": round(base_z + 0.45, 3),
            "y0": round(teeth[0], 3), "y1": round(teeth[-1] + w, 3),
            "slots": [round(t + w + RAIL_SLOT / 2, 3) for t in teeth[:-1]]}


def build(kit, p):
    """Builds the gun into kit from parameters p. Returns (bones, marks, moving, measures, parameters)."""
    p = fill(p)
    L = p["barrel_in"] * IN
    y_gas = UP_FRONT + GAS_IN[p["gas"]] * IN
    h0 = UP_FRONT + 0.4
    h1 = h0 + (p["handguard_in"] * IN if p.get("handguard_in") else (y_gas - 2.6 - h0 if p["front_sight"] == "a2" else min(L - 4.0, y_gas + 8.0) - h0))

    rails = []   # the sockets' rails; the attachments (modellab_attach) mount on their slots
    # --- the upper: its cross-section (sides up, chamfered in to the rail), the port, the forward assist, the deflector
    sect = [(-UP_HW, UP_BOT), (UP_HW, UP_BOT), (UP_HW, 0.75), (0.95, UP_TOP), (-0.95, UP_TOP), (-UP_HW, 0.75)]
    upper = kit.prism("Upper", sect, 'y', UP_REAR, UP_FRONT, "Receiver", "Root", bevel=0.06, round_r=0.18)
    kit.cut(upper, (-UP_HW - 0.6, PORT["y"][0], PORT["z"][0]), (0.3, PORT["y"][1], PORT["z"][1]))
    kit.tube("Upper_Ring", UP_FRONT - 0.5, UP_FRONT + 0.05, 1.62, mat="Receiver", verts=24)
    # the forward assist: a round housing on the right, tapering into the receiver, its grooved button at the back
    kit.loft("Upper_FA_Housing", [_ring_y(-12.7, -1.55, 0.45, 0.9, 0.9), _ring_y(-10.4, -1.55, 0.45, 0.88, 0.88),
                                  _ring_y(-9.2, -1.35, 0.45, 0.45, 0.62)], "Receiver", "Root")
    kit.tube("ForwardAssist", -13.75, -12.7, 0.62, x=-1.6, z=0.45, mat="Detail", bone="ForwardAssist", verts=20)
    for k in range(4):
        kit.tube("ForwardAssist_Groove", -13.7 + k * 0.25, -13.6 + k * 0.25, 0.66, x=-1.6, z=0.45, mat="Detail", bone="ForwardAssist", verts=20)
    # the brass deflector: just behind the port, clear of the cover's rear edge as it closes and swings
    yd = COVER["y"][0] - 0.1
    kit.prism("Upper_Deflector", [(-UP_HW + 0.05, yd - 2.1), (-UP_HW + 0.05, yd), (-2.25, yd - 0.75), (-2.3, yd - 1.7)], 'z', -0.3, 1.35,
              "Receiver", "Root", bevel=0.08, round_r=0.2)
    if p["upper"] == "carry_handle":
        handle = kit.prism("Upper_CarryHandle", [(UP_REAR + 0.3, UP_TOP - 0.05), (-2.0, UP_TOP - 0.05), (-3.4, SIGHT_Z - 1.0),
                                                 (UP_REAR + 0.8, SIGHT_Z - 0.45)], 'x', -0.95, 0.95, "Receiver", "Root", bevel=0.12, round_r=0.4)
        kit.cut(handle, (-1.5, -12.0, UP_TOP + 0.15), (1.5, -4.2, SIGHT_Z - 2.0))
        housing = kit.prism("Rear_Housing", [(-14.8, SIGHT_Z - 0.6), (-12.6, SIGHT_Z - 0.6), (-12.9, SIGHT_Z + 0.6), (-14.5, SIGHT_Z + 0.6)],
                            'x', -0.8, 0.8, "Receiver", "Root", bevel=0.05, round_r=0.2)
        kit.cut(housing, (-0.45, -14.9, SIGHT_Z - 0.1), (0.45, -12.5, SIGHT_Z + 0.7))
        kit.tube("Rear_Aperture", -13.9, -13.6, 0.42, z=SIGHT_Z, mat="Detail", verts=16)
        kit.tube_x("Rear_Windage", -1.15, 1.15, 0.38, -13.7, SIGHT_Z - 0.35, mat="Detail")
    else:
        kit.prism("Rail_Base", [(-0.9, UP_TOP - 0.05), (0.9, UP_TOP - 0.05), (0.9, RAIL_BASE), (-0.9, RAIL_BASE)], 'y', UP_REAR, UP_FRONT,
                  "Receiver", "Root", bevel=0.03)
        # behind the receiver the rail bridges over the charging handle's T (it rides under it)
        kit.prism("Rail_Base", [(-0.9, RAIL_BASE - 0.25), (0.9, RAIL_BASE - 0.25), (0.9, RAIL_BASE), (-0.9, RAIL_BASE)], 'y', RAIL_REAR,
                  UP_REAR + 0.1, "Receiver", "Root", bevel=0.03)
        rails.append(_rail(kit, "Rail_Tooth", RAIL_REAR, UP_FRONT, RAIL_BASE - 0.02, rail="upper"))

    # --- inside: the barrel's extension (seen past the open carrier) and the bolt carrier through the port
    kit.tube("Barrel_Extension", 0.0, UP_FRONT, 1.3, mat="Steel", verts=20)
    kit.tube("Bolt_Head", -1.6, 0.0, 0.85, mat="Steel", bone="Bolt", verts=20)
    kit.tube("Bolt_Carrier", -10.0, -1.6, 1.2, mat="Steel", bone="Bolt", verts=24)
    kit.box("Bolt_GasKey", (-0.4, -9.0, 1.15), (0.4, -4.2, 1.5), "Steel", "Bolt", bevel=0.05)
    # through the port: the carrier's forward assist notches on its right side, the extractor on the bolt's right
    for k in range(9):
        y = -6.9 + k * 0.32
        kit.box("Bolt_Carrier_Notch", (-1.27, y, -0.15), (-1.12, y + 0.16, 0.55), "Steel", "Bolt", bevel=0.0)
    kit.box("Bolt_Extractor", (-0.98, -1.75, -0.25), (-0.72, -0.05, 0.35), "Steel", "Bolt", bevel=0.03)
    _charging_handle(kit)

    # --- the dust cover: closed over the port at rest, hinged at the port's bottom edge
    kit.box("DustCover_Plate", (COVER["x"][0], COVER["y"][0], COVER["z"][0]), (COVER["x"][1], COVER["y"][1], COVER["z"][1]),
            "Receiver", "DustCover", bevel=0.03)
    kit.box("DustCover_Rib", (COVER["x"][0] - 0.08, -5.0, 0.35), (COVER["x"][0], -2.6, 0.65), "Receiver", "DustCover", bevel=0.02)
    kit.tube("DustCover_Rod", COVER["y"][0] - 0.2, COVER["y"][1] + 0.2, 0.1, x=HINGE[0], z=HINGE[2], mat="Steel", verts=10)
    kit.tube("DustCover_Clip", COVER["y"][1] + 0.05, COVER["y"][1] + 0.17, 0.2, x=HINGE[0], z=HINGE[2], mat="Steel", verts=12)

    # --- the lower: the body, the flared magazine well with its hole, the guard, the pins, the controls, the grip
    mag_rear = MAG_FRONT - MAG_LEN
    well_in = (mag_rear - WELL_GAP, MAG_FRONT + WELL_GAP)
    well_out = (well_in[0] - WELL_WALL, well_in[1] + WELL_WALL)
    hw_in = MAG_W / 2 + WELL_GAP
    lower = kit.prism("Lower", [(UP_REAR - TOWER, UP_BOT), (UP_FRONT + 0.3, UP_BOT), (UP_FRONT + 0.3, -3.4), (0.4, -3.9),
                                (well_out[1], -4.3), (well_out[0], LOWER_BOT), (-11.6 + LOWER_DY, LOWER_BOT), (-13.0 + LOWER_DY, LOWER_BOT + 0.2),
                                (-15.2, -4.6), (UP_REAR - TOWER, -3.3)], 'x', -1.3, 1.3, "Receiver", "Root", bevel=0.1, round_r=0.3)
    kit.tube("Lower_Tower", UP_REAR - TOWER, UP_REAR, TUBE_R + 0.14, mat="Receiver", verts=24)   # just over the tube's threads
    kit.prism("Lower_TowerWeb", [(UP_REAR - TOWER, -1.2), (UP_REAR, -1.2), (UP_REAR, UP_BOT - 0.1), (UP_REAR - TOWER, -2.4)], 'x', -1.3, 1.3,
              "Receiver", "Root", bevel=0.05)
    mid_y = (well_out[0] + well_out[1]) / 2
    half_y = (well_out[1] - well_out[0]) / 2
    rings = []
    for z, ax, ay, dy in ((UP_BOT - 0.02, hw_in + 0.33, half_y, 0.0), (-2.6, hw_in + 0.33, half_y, 0.0), (-5.6, hw_in + 0.36, half_y + 0.05, 0.05),
                          (WELL_BOT + 0.25, hw_in + 0.55, half_y + 0.28, 0.1), (WELL_BOT, hw_in + 0.6, half_y + 0.32, 0.1)):
        rings.append(_ring_z(z, 0.0, mid_y + dy, ax, ay, p=5.0))
    well = kit.loft("Lower_Well", rings, "Receiver", "Root", smooth=False)
    for ob in (lower, well):
        kit.cut(ob, (-hw_in, well_in[0], WELL_BOT - 1.0), (hw_in, well_in[1], UP_BOT + 0.01))
    g_in = GUARD_BOT + 0.22
    kit.sweep("Guard", [(0, well_out[0] + 0.1, LOWER_BOT + 0.15), (0, well_out[0] - 0.25, -6.9), (0, well_out[0] - 0.9, g_in),
                        (0, -9.6 + LOWER_DY, g_in - 0.04), (0, -12.95 + LOWER_DY, g_in + 0.1), (0, -13.7 + LOWER_DY, -7.6)],
              0.42, 0.24,
              "Receiver", "Root", n=12, p=4.0)
    # the trigger: its pin in the lower, the blade curving down into the guard's opening for the index finger
    kit.prism("Trigger", [(y + LOWER_DY, z) for y, z in ((-8.75, -4.6), (-8.25, -4.6), (-8.35, -5.9), (-8.7, -7.0), (-9.25, -7.2),
                                                          (-9.05, -6.6), (-8.85, -5.7))], 'x',
              -0.22, 0.22, "Steel", "Trigger", bevel=0.04, round_r=0.15)
    for y, z, r in ((UP_FRONT - 0.5, -2.45, 0.32), (-14.4, -2.45, 0.32), (-8.6 + LOWER_DY, -4.1, 0.2), (-10.0 + LOWER_DY, -3.5, 0.2)):
        for x0, x1 in ((1.28, 1.4), (-1.4, -1.28)):
            kit.tube_x("Pin", x0, x1, r, y, z, mat="Steel")
    # the pivot and takedown pins' heads stand proud on the left, a detent groove round each
    for name, y in (("Pin_Pivot_Head", UP_FRONT - 0.5), ("Pin_Takedown_Head", -14.4)):
        kit.tube_x(name, 1.3, 1.5, 0.45, y, -2.45, mat="Steel", verts=20)
        kit.tube_x(name + "_Groove", 1.5, 1.56, 0.36, y, -2.45, mat="Steel", verts=20)
    # the guard: a roll pin through the lower's ears at the grip, the spring detent at the front in the well's ear
    kit.tube_x("Guard_Pin", -0.58, 0.58, 0.12, -13.45 + LOWER_DY, -7.75, mat="Steel", verts=10)
    kit.tube_x("Guard_Detent", -0.6, 0.6, 0.14, well_out[0] - 0.05, LOWER_BOT - 0.35, mat="Steel", verts=10)
    kit.tube_x("Selector_Hub", 1.28, 1.6, 0.48, -11.6 + LOWER_DY, -2.6, mat="Detail", bone="Selector")
    kit.prism("Selector_Lever", [(y + LOWER_DY, z) for y, z in ((-11.6, -2.32), (-13.2, -2.42), (-13.75, -2.6), (-13.2, -2.78), (-11.6, -2.88))],
              'x', 1.48, 1.7,
              "Detail", "Selector", bevel=0.03, round_r=0.1)
    kit.tube_x("Selector_Nub", -1.45, -1.28, 0.3, -11.6 + LOWER_DY, -2.6, mat="Detail", bone="Selector")
    kit.tube_x("MagRelease", -1.78, -1.25, 0.43, -7.75 + LOWER_DY, -2.9, mat="Detail", bone="MagRelease", verts=20)
    kit.tube_x("MagCatch", 1.25, 1.42, 0.36, -7.75 + LOWER_DY, -2.9, mat="Detail", bone="MagRelease", verts=16)   # its left end
    kit.prism("MagRelease_Fence", [(y + LOWER_DY, z) for y, z in ((-8.75, -2.0), (-8.45, -2.0), (-8.45, -3.85), (-8.75, -3.75))], 'x',
              -1.62, -1.25, "Receiver", "Root",
              bevel=0.04, round_r=0.1)
    kit.prism("BoltCatch", [(y + LOWER_DY, z) for y, z in ((-6.35, -1.05), (-7.3, -1.3), (-7.35, -3.15), (-6.75, -3.4), (-6.4, -2.6))],
              'x', 1.28, 1.74, "Detail",
              "BoltCatch", bevel=0.05, round_r=0.18)
    kit.tube_x("BoltCatch_Pin", 1.26, 1.8, 0.1, -6.85 + LOWER_DY, -1.5, mat="Steel", verts=10)
    for k in range(4):   # the lower paddle's serrations, for the thumb that drops the bolt
        z = -2.55 - k * 0.18
        kit.box("BoltCatch_Serration", (1.72, -7.2 + LOWER_DY, z - 0.05), (1.8, -6.6 + LOWER_DY, z + 0.05), "Detail", "BoltCatch", bevel=0.0)
    _grip(kit, p["grip"], p["grip_texture"])

    # --- the back: the buffer tube, the castle nut and the stock
    tube_end = UP_REAR - TUBE_LEN[p["stock"]]
    kit.tube("Buffer_Tube", tube_end, UP_REAR - TOWER, TUBE_R, mat="Receiver", verts=28)
    nut = kit.tube("Castle_Nut", UP_REAR - TOWER - 0.7, UP_REAR - TOWER, TUBE_R + 0.3, mat="Receiver", verts=24)
    for k in range(6):   # the castle nut's notches round its rear rim (the wrench's teeth go in them)
        a = math.radians(30 + k * 60)
        cx, cz = math.sin(a) * (TUBE_R + 0.32), math.cos(a) * (TUBE_R + 0.32)
        notch = kit.box("_notch", (cx - 0.2, UP_REAR - TOWER - 0.75, cz - 0.2), (cx + 0.2, UP_REAR - TOWER - 0.4, cz + 0.2), "Receiver", "_cut",
                        bevel=0.0)
        kit.cut(nut, None, None, cutter=notch)
    kit.named["Castle_Nut_Notch"] = nut   # the notches are cut into the nut: the nut itself carries the feature
    kit.tube("End_Plate", UP_REAR - TOWER - 0.15, UP_REAR - TOWER, TUBE_R + 0.45, mat="Receiver", verts=20)
    if p["stock"] in ("carbine", "side_tubes"):
        # the carbine tube's keyway along its bottom, with the stock's six position holes
        kit.box("Buffer_Tube_Key", (-0.32, tube_end + 0.2, -TUBE_R - 0.18), (0.32, UP_REAR - TOWER - 0.8, -TUBE_R + 0.15), "Receiver", "Root",
                bevel=0.04)
        for k in range(6):
            y = tube_end + 1.2 + k * STOCK_STEP
            kit.rod("Buffer_Tube_Hole", (0.0, y, -TUBE_R - 0.22), (0.0, y, -TUBE_R - 0.12), 0.2, mat="Rubber", bone="Root", n=12)
        yb = tube_end + 0.43 - int(p["stock_pos"]) * STOCK_STEP   # position 0: all the way in (the M4 lengths)
        _stock_carbine(kit, yb, p["stock"] == "side_tubes")
        stock_head = (0.0, yb, 0.0)
        butt_y = yb - 1.0
    else:
        yb = tube_end - A2_PAST_TUBE   # the A2 stock's butt reaches past its tube
        _stock_a2(kit, yb)
        stock_head = None
        butt_y = yb - 0.6

    # --- the front: the barrel, the nut, the handguard, the gas block or the front sight, the muzzle device
    yg = max(y_gas, h1 + 2.6) if p["front_sight"] == "a2" else y_gas
    kit.tube("Barrel", UP_FRONT, yg, 1.0, mat="Steel", verts=24)
    if p["front_sight"] == "a2" and p["gas"] == "carbine":
        # the M4's barrel: stepped down ahead of the front sight for the M203's mount (the "M203 cut")
        cut0 = L - 12.07 + BIRDCAGE    # the M4A1 photo: the step 10.0 to 12.1 cm behind the flash hider's front
        kit.tube("Barrel_Front", yg, cut0, 0.92, mat="Steel", verts=24)
        kit.tube("Barrel_M203_Cut", cut0, cut0 + 2.07, 0.72, mat="Steel", verts=24)
        kit.tube("Barrel_Front_Muzzle", cut0 + 2.07, L, 0.92, mat="Steel", verts=24)
    else:
        kit.tube("Barrel_Front", yg, L, 0.92, mat="Steel", verts=24)
    kit.tube("Barrel_Nut", UP_FRONT, UP_FRONT + 2.0, 1.8, mat="Receiver", verts=20)
    rails += _handguard(kit, p["handguard"], h0, h1)
    front_sight = None
    if p["front_sight"] == "a2":
        # the A2 front sight base as the M4A1 photo draws it: 5.2 cm along the barrel, its front face upright, its flat
        # top 1.1 cm long, its back sloping down to the clamp; the wings stand round the post on top
        kit.tube("FSB_Clamp", yg - 2.5, yg + 2.4, 1.45, mat="Steel", verts=20)
        kit.prism("FSB_Tower", [(yg - 2.55, 1.2), (yg + 2.4, 1.2), (yg + 2.3, 2.6), (yg + 1.95, 3.6), (yg + 1.4, 4.4), (yg + 0.1, 4.4),
                                (yg - 1.1, 3.2), (yg - 2.55, 1.9)], 'x', -0.6, 0.6, "Steel", "Root", bevel=0.08, round_r=0.3)
        for x0, x1 in ((0.55, 0.9), (-0.9, -0.55)):
            kit.prism("FSB_Wing", [(yg + 0.1, 4.2), (yg + 2.0, 4.2), (yg + 2.0, SIGHT_Z), (yg + 1.4, SIGHT_Z + 0.05), (yg + 0.4, SIGHT_Z - 0.4)],
                      'x', x0, x1, "Steel", "Root", bevel=0.04, round_r=0.15)
        kit.box("FSB_Post", (-0.12, yg + 1.0, 4.3), (0.12, yg + 1.28, SIGHT_Z), "Detail", "Root", bevel=0.02)
        # the bayonet lug under the base's front, reaching 1 cm past its face (the photo)
        kit.prism("FSB_Lug", [(yg + 1.6, -1.35), (yg + 3.4, -1.35), (yg + 3.3, -2.25), (yg + 1.7, -2.25)], 'x', -0.4, 0.4, "Steel", "Root",
                  bevel=0.04, round_r=0.1)
        # the sling swivel under the base's rear: its loop on a rivet (the photo: down to 2.1 cm under the bore)
        kit.tube_x("FSB_Swivel", -0.6, 0.6, 0.18, yg - 1.6, -1.45, mat="Steel")
        loop = [(0.0, yg - 1.6 + 0.75 * math.cos(t), -1.75 + 0.35 * math.sin(t)) for t in [2 * math.pi * k / 12 for k in range(12)]]
        kit.sweep("FSB_SwivelLoop", loop, 0.1, 0.1, "Steel", "Root", n=8, closed=True)
        for dy in (-1.3, 1.2):   # the two taper pins through the base and the barrel
            kit.tube_x("FSB_Pin", -1.52, 1.52, 0.11, yg + dy, -0.95, mat="Steel", verts=10)
        front_sight = (0.0, yg + 1.14, SIGHT_Z)
    else:
        kit.tube("Gas_Block", yg - 1.0, yg + 1.0, 1.35, mat="Steel", verts=20)
        # a flip front sight is an attachment (modellab_attach), on the handguard's top rail
    muzzle_y = L
    if p["muzzle"] == "a2_birdcage":
        kit.tube("Muzzle_Washer", L - 0.45, L - 0.3, 1.12, mat="Steel", verts=12)   # the peel washer, its flats
        cage = kit.tube("Muzzle_Device", L - 0.3, L + BIRDCAGE - 0.5, 1.1, mat="Steel", verts=24)
        for k in range(4):            # the A2's slots: round the top and sides, the bottom closed so it kicks up no dust
            a = math.radians(-75 + k * 50)
            x, z = math.sin(a) * 1.15, math.cos(a) * 1.15
            slot = kit.rod("_slot", (x, L + 1.0, z), (x, L + BIRDCAGE - 1.2, z), 0.22, mat="Steel", bone="_cut", n=8)
            kit.cut(cage, None, None, cutter=slot)
        kit.tube("Muzzle_Crown", L + BIRDCAGE - 0.5, L + BIRDCAGE, 1.1, 1.0, mat="Steel", verts=24)
        muzzle_y = L + BIRDCAGE

    # --- the magazine: seated straight in the well, curved below it, a round on its lips
    height, curve = MAG_SPINE[int(p["magazine"])]
    front, rear = _mag_edges(mag_rear, height, R=curve)
    body = kit.prism("Magazine_Body", front + list(reversed(rear)), 'x', -MAG_W / 2, MAG_W / 2, "Magazine", "Magazine",
                     bevel=0.12 if p["magazine_type"] == "gi_aluminum" else 0.22)
    # the top narrows in to the feed lips: the body stops under the upper, only the lips go up into it
    neck = UP_BOT - 0.25
    kit.cut(body, (-MAG_W, mag_rear - 2.0, neck), (MAG_W, MAG_FRONT + 2.0, MAG_TOP + 1.0))
    mid, half = (mag_rear + MAG_FRONT) / 2, MAG_LEN / 2
    kit.loft("Magazine_Lips", [_ring_z(neck - 0.02, 0.0, mid, MAG_W / 2 - 0.02, half - 0.02, n=24, p=6.0),
                               _ring_z(UP_BOT - 0.05, 0.0, mid, LIPS_HW + 0.08, half - 0.05, n=24, p=6.0),
                               _ring_z(MAG_TOP, 0.0, mid, LIPS_HW, half - 0.1, n=24, p=6.0)],
             "Magazine", "Magazine", smooth=False)
    if p["magazine_type"] == "gi_aluminum":
        below = [(f, r) for f, r in zip(front, rear) if f[1] <= MAG_TOP - 2.5]
        for f0, f1 in ((0.18, 0.3), (0.62, 0.74)):   # the pressed ribs down each side
            pts = [(r[0] + (f[0] - r[0]) * f1, f[1]) for f, r in below] + [(r[0] + (f[0] - r[0]) * f0, f[1]) for f, r in reversed(below)]
            for x0, x1 in ((MAG_W / 2 - 0.02, MAG_W / 2 + 0.07), (-MAG_W / 2 - 0.07, -MAG_W / 2 + 0.02)):
                kit.prism("Magazine_Rib", pts, 'x', x0, x1, "Magazine", "Magazine", bevel=0.02)
    # the catch's slot in the magazine's left side, just behind the front wall
    kit.box("Magazine_CatchSlot", (MAG_W / 2 - 0.08, MAG_FRONT - 2.3, -3.25), (MAG_W / 2 + 0.01, MAG_FRONT - 1.4, -2.6), "Detail",
            "Magazine", bevel=0.0)
    (fy, fzf), (ry, rzr) = front[-1], rear[-1]
    ty, tz = (front[-1][0] - front[-2][0]), (front[-1][1] - front[-2][1])     # down the spine at the bottom
    tn = math.hypot(ty, tz)
    ty, tz = ty / tn, tz / tn

    def floor(dn, out=0.0):   # the floor's outline: the bottom corners, dn further down the spine, out beyond the walls
        ny, nz = -tz, ty      # forward along the floor
        return [(ry - ny * out, rzr - nz * out), (fy + ny * out, fzf + nz * out),
                (fy + ny * out + ty * dn, fzf + nz * out + tz * dn), (ry - ny * out + ty * dn, rzr - nz * out + tz * dn)]
    if p["magazine_type"] == "polymer":
        fl = floor(0.9, 0.15)
        kit.prism("Magazine_Floor", [(yy - ty * 0.1, zz - tz * 0.1) for yy, zz in fl], 'x', -MAG_W / 2 - 0.2, MAG_W / 2 + 0.2, "Magazine",
                  "Magazine", bevel=0.1, round_r=0.25)
        for k in range(3):     # the floor's ribs, across it
            u = 0.25 + 0.25 * k
            cy_, cz_ = ry + (fy - ry) * u + ty * 0.5, rzr + (fzf - rzr) * u + tz * 0.5
            kit.box("Magazine_FloorRib", (-MAG_W / 2 - 0.25, cy_ - 0.12, cz_ - 0.3), (MAG_W / 2 + 0.25, cy_ + 0.12, cz_ + 0.3), "Magazine",
                    "Magazine", bevel=0.04)
    else:
        fl = floor(0.55, 0.1)
        kit.prism("Magazine_Floor", [(yy - ty * 0.1, zz - tz * 0.1) for yy, zz in fl], 'x', -MAG_W / 2 - 0.15, MAG_W / 2 + 0.15,
                  "Magazine", "Magazine", bevel=0.12, round_r=0.15)
    r_y = mag_rear + 0.35
    kit.tube("Round_Case", r_y, r_y + ROUND["case"], ROUND["r"], z=MAG_TOP - 0.3, mat="Brass", bone="MagRound", verts=16)
    kit.tube("Round_Bullet", r_y + ROUND["case"], r_y + ROUND["case"] + ROUND["bullet"], ROUND["r"] * 0.85, 0.12,
             z=MAG_TOP - 0.3, mat="Copper", bone="MagRound", verts=16)

    mag_mid = (MAG_FRONT + mag_rear) / 2
    bones = [("Root", (0, 0, 0), None), ("Bolt", (0, 0, 0), "Root"), ("ChargingHandle", (0, -15.9, 1.5), "Root"),
             ("DustCover", HINGE, "Root"), ("BoltCatch", (1.5, -6.9 + LOWER_DY, -2.6), "Root"), ("MagRelease", (-1.55, -7.75 + LOWER_DY, -2.9), "Root"),
             ("Selector", (0, -11.6 + LOWER_DY, -2.6), "Root"), ("Trigger", (0, -8.6 + LOWER_DY, -4.1), "Root"), ("ForwardAssist", (-1.6, -13.2, 0.45), "Root"),
             ("Magazine", (0, mag_mid, MAG_TOP), "Root"), ("MagRound", (0, r_y, MAG_TOP - 0.3), "Magazine")]
    if stock_head:
        bones.append(("Stock", stock_head, "Root"))
    marks = {
        "chamber": {"at": [0.0, 0.0, 0.0], "note": "the bolt face at rest on the bore: the chamber's rear"},
        "bore": {"at": [0.0, 0.0, 0.0], "axis": [0.0, 1.0, 0.0]},
        "eject_port": {"at": [-UP_HW, (PORT["y"][0] + PORT["y"][1]) / 2, (PORT["z"][0] + PORT["z"][1]) / 2], "normal": [-1.0, 0.0, 0.0],
                       "box": {"y": list(PORT["y"]), "z": list(PORT["z"])}},
        "magwell": {"at": [0.0, mag_mid, UP_BOT], "axis": [0.0, 0.0, -1.0], "inner": {"x": [-hw_in, hw_in], "y": list(well_in)},
                    "bottom_z": WELL_BOT},
        "mag_lips": {"at": [0.0, mag_mid, MAG_TOP]},
        "grip_r": {"at": [0.0, -16.6 + LOWER_DY, -10.0], "note": "the pistol grip's middle"},
        "trigger": {"at": [0.0, -8.9 + LOWER_DY, -6.6], "note": "the trigger blade, where the index finger rests"},
        "support_l": {"at": [0.0, (h0 + h1) / 2, -(RAIL_BASE + 0.03 if p["handguard"] == "quad_rail" else 2.2) - 0.25],
                      "note": "under the handguard's middle"},
        "charging_handle": {"at": [0.0, -16.0, 1.5]},
        "muzzle": {"at": [0.0, muzzle_y, 0.0]},
        "rail_top": {"at": [0.0, (UP_REAR + UP_FRONT) / 2, RAIL_TOP]} if p["upper"] == "flattop" else None,
        "front_sight": {"at": list(front_sight)} if front_sight else None,
        "rear_sight": {"at": [0.0, -13.75, SIGHT_Z]} if p["upper"] == "carry_handle" else None,   # flip sights: their attachments
        "butt": {"at": [0.0, butt_y, 0.0]},
    }
    marks = {k: v for k, v in marks.items() if v}
    moving = {
        "Bolt": {"travel_cm": BOLT_TRAVEL, "catch_cm": BOLT_CATCH, "axis": [0, -1, 0], "note": "estimates (build_ar15_rig.py)"},
        "ChargingHandle": {"travel_cm": BOLT_TRAVEL, "axis": [0, -1, 0]},
        "DustCover": {"hinge": list(HINGE), "axis": [0, 1, 0], "open_deg": COVER_OPEN_DEG, "rest": "closed over the port"},
        "Magazine": {"axis": [0, 0, -1], "note": "drops straight along the well"},
        "Trigger": {"pull_deg": 12.0},
        "Selector": {"positions": p["selector"], "deg": [0, 90, 180][:len(p["selector"])]},
        "BoltCatch": {"lift_cm": 0.25},
        "MagRelease": {"press_cm": 0.3, "axis": [1, 0, 0], "note": "the button pressed in from the right"},
        "ForwardAssist": {"press_cm": 0.5, "axis": [0, 1, 0], "note": "pushed forward to seat the bolt"},
    }
    if stock_head:
        moving["Stock"] = {"axis": [0, -1, 0], "step_cm": STOCK_STEP, "positions": 5, "now": int(p["stock_pos"])}
    measures = {"muzzle_y": muzzle_y, "butt_y": butt_y, "well_in": well_in, "hw_in": hw_in, "mag_rear": mag_rear,
                "round_rear_y": r_y, "front_sight": front_sight, "tube_end": tube_end, "stock": p["stock"],
                "stock_pos": int(p["stock_pos"]), "rails": rails, "sight_z": SIGHT_Z}
    return bones, marks, moving, measures, p


# --- part helpers ---------------------------------------------------------------------------------------------------
def _ring_y(y, x, z, a, b, n=20, p=2.0):
    """A ring across the gun at y: a along X, b along Z."""
    from modellab_parts import ring
    return ring((x, y, z), (1, 0, 0), (0, 0, 1), a, b, n, p)


def _ring_z(z, x, y, a, b, n=20, p=2.0):
    """A level ring at height z: a along X, b along Y."""
    from modellab_parts import ring
    return ring((x, y, z), (1, 0, 0), (0, 1, 0), a, b, n, p)


def _mag_edges(mag_rear, height, straight=None, R=None, steps=12):
    """The magazine's front and rear edges (y, z): either side of its spine, which runs straight down through the well
    and then curves forward on radius R; each pair square to the spine, so the floor sits square to the curve."""
    half = (MAG_FRONT - mag_rear) / 2
    mid = (MAG_FRONT + mag_rear) / 2
    straight = MAG_TOP - WELL_BOT if straight is None else straight
    front, rear = [], []
    for k in range(steps + 1):
        sd = height * k / steps
        if R is None or sd <= straight:
            th, cy, cz = 0.0, mid, MAG_TOP - sd
        else:
            th = (sd - straight) / R
            cy, cz = mid + R * (1 - math.cos(th)), MAG_TOP - straight - R * math.sin(th)
        ny, nz = math.cos(th), math.sin(th)      # forward, square to the spine
        # the front curves with the spine; the back curves less (MAG_BACK_CURVE of the spine's forward run), so the
        # body widens toward its floor, as real AR magazines do (the photo: 6.8 cm front to back at the bottom)
        front.append((cy + half * ny, cz + half * nz))
        rear.append((cy - half * ny - (1.0 - MAG_BACK_CURVE) * (cy - mid), cz - half * nz))
    return front, rear


CH_HALF = 2.3      # the charging handle's T, about 1.8 in across (estimate, from photographs of the mil-spec part)


def _charging_handle(kit):
    """The mil-spec charging handle: the stem in its channel under the rail, the T behind the upper with its wings
    curving back to finger hooks, ridges on their rear faces, and on the left wing the latch that locks it, pivoting
    on its roll pin, its top serrated for the thumb."""
    yt, zc = -15.85, 1.95          # the T's middle: just behind the upper's rear face, above the buffer tower, level with the rail's end
    kit.box("Charging_Shaft", (-0.6, -14.9, 1.5), (0.6, -2.5, 1.95), "Receiver", "ChargingHandle", bevel=0.04)
    kit.loft("Charging_Hub", [_ring_y(y, 0.0, zc + 0.05, 0.75 * w, 0.42 * w, n=20, p=3.0)
                              for y, w in ((-15.32, 0.9), (-15.45, 1.0), (-16.3, 1.0), (-16.45, 0.85))],
             "Detail", "ChargingHandle", smooth=True, subdiv=1)
    for side, name in ((-1, "Charging_Wing"), (1, "Charging_Latch")):
        # the wing: a bar out from the hub, swept back toward its tip, its end rounded into a hook for the fingers
        x0 = 0.55 if side < 0 else 0.85          # the latch stands a hair off the hub: it pivots
        path = []
        for k in range(7):
            u = k / 6
            x = side * (x0 + (CH_HALF - x0) * u)
            path.append((x, yt - 0.48 * u * u, zc + 0.04 * u))
        kit.sweep(name, path, 0.33, 0.4 - 0.06 * (1 if side > 0 else 0), "Detail", "ChargingHandle", n=14, p=3.2)
        tip = path[-1]
        kit.loft(name + "_Hook", [_ring_y(tip[1] + dy, tip[0] - side * 0.03 * k, tip[2], 0.36 * w, 0.38 * w, n=16)
                                  for k, (dy, w) in enumerate(((0.25, 0.85), (0.15, 1.0), (-0.2, 1.0), (-0.3, 0.8)))],
                 "Detail", "ChargingHandle", smooth=True)
        # finger ridges across the wing's rear face, near its tip
        for j in range(3):
            u = 0.62 + 0.13 * j
            x = side * (x0 + (CH_HALF - x0) * u)
            y = yt - 0.48 * u * u - 0.33
            kit.rod(name + "_Ridge", (x, y + 0.04, zc - 0.25), (x, y + 0.04, zc + 0.27), 0.085, mat="Detail", bone="ChargingHandle", n=8)
    # the latch: its serrated top for the thumb, and the roll pin it turns on
    for j in range(5):
        x = 1.35 + 0.17 * j
        u = (x - 0.85) / (CH_HALF - 0.85)
        y = yt - 0.48 * u * u
        kit.box("Charging_Latch_Serration", (x - 0.04, y - 0.28, zc + 0.3), (x + 0.04, y + 0.28, zc + 0.4), "Detail",
                "ChargingHandle", bevel=0.0)
    kit.rod("Charging_Latch_Pin", (0.8, yt + 0.05, zc - 0.48), (0.8, yt + 0.05, zc + 0.46), 0.11, mat="Steel", bone="ChargingHandle", n=10)


def _grip(kit, kind, texture="auto"):
    """The pistol grip: level sections down a spine raked 25 degrees back; the A2's nub under the second finger."""
    top_y, top_z, bot_z = -13.5 + LOWER_DY, -5.2, -15.0
    rake = math.tan(math.radians(GRIP_RAKE))
    rings = []
    nub_z = -9.6
    for z in (top_z + 0.3, top_z - 0.5, -6.8, -8.2, nub_z, -10.4, -12.0, -13.6, bot_z + 0.5, bot_z):
        t = (top_z - z) / (top_z - bot_z)
        cy = top_y - (top_z - z) * rake - 1.0
        half_w = 1.32 - 0.12 * math.sin(math.pi * t) + (0.12 if t > 0.85 else 0.0)
        half_d = 2.5 - 0.15 * t
        push = 0.45 if kind == "a2" and abs(z - nub_z) < 0.05 else 0.0   # the finger nub
        if z == bot_z:
            half_w, half_d = half_w - 0.35, half_d - 0.4
        rings.append(_ring_z(z, 0.0, cy + push / 2, half_w, half_d + push / 2, n=24, p=2.6))
        if kind == "flared" and t > 0.8:      # the base flares forward under the little finger: it stops the hand sliding off
            heel = (t - 0.8) / 0.2
            half_w += 0.1 * heel
            rings[-1] = _ring_z(z, 0.0, cy + push / 2 + 0.45 * heel, half_w, half_d + push / 2 + 0.45 * heel, n=24, p=2.6)
    if kind == "beavertail":   # a beavertail over the web of the hand
        rings.insert(0, _ring_z(top_z + 0.55, 0.0, top_y - 1.6, 1.2, 2.9, n=24, p=2.6))
    grip = kit.loft("Grip", rings, "Furniture", "Root", subdiv=1)
    by = top_y - (top_z - bot_z) * rake - 1.0
    kit.rod("Grip_Screw", (0.0, by + 0.1, bot_z - 0.06), (0.0, by + 0.1, bot_z + 0.25), 0.38, mat="Steel", bone="Root", n=12)
    if texture == "auto":
        texture = "checkered" if kind == "a2" else "stippled"
    if texture == "none":
        return
    # the side panels: down the raked spine, between the front and back straps, under the nub
    s = Vector((0.0, -math.sin(math.radians(GRIP_RAKE)), -math.cos(math.radians(GRIP_RAKE))))
    f = Vector((0.0, math.cos(math.radians(GRIP_RAKE)), -math.sin(math.radians(GRIP_RAKE))))
    zc = -10.4
    centre = Vector((0.0, top_y - (top_z - zc) * rake - 1.15, zc))
    for side in (1, -1):
        if texture == "checkered":
            kit.texture("Grip_Checkering", grip, centre, s, f, 3.3, 1.7, side, "checkered", pitch=0.32, depth=0.07,
                        mat="Furniture")
        else:
            kit.texture("Grip_Stipple", grip, centre, s, f, 3.5, 1.8, side, "stippled", pitch=0.17, depth=0.05,
                        mat="Furniture", seed=7 + side)


def _stock_carbine(kit, yb, side_tubes):
    """The M4 collapsible stock as the M4A1 photo draws it (distances from the butt pad's rear, u, and heights from the
    bore): its top flush with the buffer tube's top, 1.6 cm over the bore; its body 5.4 cm under the bore for its front
    half, its bottom sloping down to the butt, which stands from 1.6 over to 11.5 cm under the bore for its last 4.4 cm;
    five long recesses down each side, a sling slot through the butt, the lock lever under the body, a sling loop
    under the butt, and the rounded rim along the sloped bottom edge."""
    y0 = yb - 1.0                     # the pad's rear: u = 0

    def at(u, z):
        return (y0 + u, z)
    body = kit.prism("Stock_Body", [at(0.9, 1.6), at(15.9, 1.6), at(16.9, 1.0), at(16.9, -2.2), at(15.8, -2.9), at(14.1, -2.9),
                                    at(13.95, -5.0), at(13.6, -5.4), at(10.4, -5.4), at(4.4, -7.8), at(4.4, -11.0), at(3.9, -11.5),
                                    at(0.9, -11.5)], 'x', -1.85, 1.85,
                     "Furniture", "Stock", bevel=0.15, round_r=0.5)
    for k in range(5):                # the long recesses down each side
        u_a = 1.3 + k * 3.05
        for sx in (1, -1):
            rec = kit.prism("_recess", [at(u_a, -1.3), at(u_a + 2.6, -1.3), at(u_a + 2.6, -1.9), at(u_a, -1.9)], 'x', sx * 1.65, sx * 2.2,
                            "Furniture", "_cut", bevel=0.0, round_r=0.28)
            kit.cut(body, None, None, cutter=rec)
    slot = kit.prism("_slot", [at(1.4, -3.4), at(4.0, -3.4), at(4.0, -4.2), at(1.4, -4.2)], 'x', -2.5, 2.5, "Furniture", "_cut",
                     bevel=0.0, round_r=0.35)
    kit.cut(body, None, None, cutter=slot)
    kit.named["Stock_Recess"] = body          # the recesses are cut into the body: the body carries the feature
    kit.named["Stock_SlingSlot"] = body
    kit.loft("Stock_Pad", [_ring_y(y0 + 0.9, 0.0, -4.95, 1.95, 6.7, n=28, p=4.0), _ring_y(y0, 0.0, -4.95, 1.9, 6.65, n=28, p=4.0)],
             "Rubber", "Stock", smooth=True)
    kit.sweep("Stock_Ridge", [(0.0,) + at(u, z) for u, z in ((4.2, -7.95), (7.4, -6.6), (10.6, -5.35), (13.5, -5.35))], 1.9, 0.3,
              "Furniture", "Stock", n=12, p=3.0)
    kit.prism("Stock_Lever", [at(10.6, -5.3), at(11.8, -5.3), at(11.6, -6.25), at(10.8, -6.2)], 'x', -0.55, 0.55, "Detail", "Stock",
              bevel=0.05, round_r=0.2)
    # the sling loop under the butt, on its rivet
    loop = [(0.0, y0 + 2.9 + 0.7 * math.cos(t), -11.8 + 0.4 * math.sin(t)) for t in [2 * math.pi * k / 12 for k in range(12)]]
    kit.sweep("Stock_SlingLoop", loop, 0.12, 0.12, "Steel", "Stock", n=8, closed=True)
    kit.tube_x("Stock_SlingPin", -0.6, 0.6, 0.15, y0 + 2.9, -11.45, mat="Steel", bone="Stock")
    if side_tubes:   # the battery tubes down its sides, a cheek weld on top
        for sx in (1, -1):
            kit.loft("Stock_Tube", [_ring_y(yb + 13.5, sx * 2.05, 0.7, 0.9, 1.0, n=20), _ring_y(yb + 12.8, sx * 2.1, 0.7, 1.05, 1.15, n=20),
                                    _ring_y(yb + 2.0, sx * 2.1, 0.7, 1.05, 1.15, n=20), _ring_y(yb + 1.4, sx * 2.0, 0.7, 0.95, 1.05, n=20)],
                     "Furniture", "Stock", subdiv=1)
        kit.prism("Stock_Cheek", [(yb + 13.0, 1.8), (yb + 1.8, 2.3), (yb + 1.8, 1.2), (yb + 13.0, 1.0)], 'x', -1.5, 1.5, "Furniture", "Stock",
                  bevel=0.3, round_r=0.5, smooth=True)


def _stock_a2(kit, yb):
    """The fixed A2 stock: lofted from the receiver's back to the butt, its plate with the trap door."""
    rings = [_ring_y(y, 0.0, (top + bot) / 2, hw, (top - bot) / 2, n=28, p=3.2)
             for y, top, bot, hw in ((UP_REAR - TOWER, 1.7, -3.2, 1.55), (UP_REAR - TOWER - 6.0, 1.9, -4.6, 1.7),
                                     (UP_REAR - TOWER - 16.0, 2.3, -7.6, 1.85), (yb + 1.2, 2.6, -10.2, 1.95), (yb, 2.65, -10.4, 1.95))]
    kit.loft("Stock_Body", rings, "Furniture", "Root", subdiv=1)
    kit.loft("Stock_Plate", [_ring_y(yb, 0.0, -3.9, 2.0, 6.65, n=28, p=4.0), _ring_y(yb - 0.6, 0.0, -3.9, 1.95, 6.6, n=28, p=4.0)],
             "Detail", "Root", smooth=True)
    kit.box("Stock_TrapDoor", (-1.2, yb - 0.75, -6.5), (1.2, yb - 0.55, -2.0), "Detail", "Root", bevel=0.08)


def _handguard(kit, kind, h0, h1):
    """The handguard. Returns its rails for the sockets (none on the round one)."""
    if kind == "round":
        # the M4 and M16's ribbed round handguard: the shell, its long ribs, the delta ring and the cap
        kit.tube("Handguard", h0, h1, 2.15, mat="Handguard", verts=32)
        for k in range(14):
            a = 2 * math.pi * k / 14
            x, z = math.sin(a) * 2.18, math.cos(a) * 2.18
            kit.rod("Handguard_Rib", (x, h0 + 0.8, z), (x, h1 - 0.8, z), 0.17, mat="Handguard", bone="Root", n=8)
        # the vent holes, a row down each upper side between the ribs (darker: the heat shield behind them)
        n_v = int((h1 - h0 - 3.0) // 2.2)
        for k in range(n_v):
            y = h0 + 1.8 + k * 2.2
            for sx in (1, -1):
                a = math.radians(sx * 52)
                kit.rod("Handguard_Vent", (math.sin(a) * 2.14, y, math.cos(a) * 2.14), (math.sin(a) * 2.14, y + 0.9, math.cos(a) * 2.14),
                        0.24, mat="Rubber", bone="Root", n=10)
        kit.tube("Handguard_Ring", h0 - 0.5, h0 + 0.6, 2.5, mat="Receiver", verts=28)
        kit.tube("Handguard_Cap", h1 - 0.5, h1, 2.1, mat="Receiver", verts=24)
        return []
    r = 2.2
    if kind == "quad_rail":
        r = RAIL_BASE + 0.03   # the RIS: its top rail level with the upper's (the photo: 2.98 cm over the bore)
        kit.prism("Handguard", [(-r, -r), (r, -r), (r, r), (-r, r)], 'y', h0, h1, "Handguard", "Root", bevel=0.2, round_r=0.6)
        for sx in (1, -1):   # the cross bolts that clamp the rail to the barrel nut, at the rear, and its front
            for y in (h0 + 1.4, h1 - 1.4):
                kit.tube_x("HG_Bolt", sx * r, sx * (r + 0.28), 0.32, y, -1.95, mat="Steel", verts=6)   # low, under the side rail
        return [_rail(kit, "HG_Tooth", h0, h1, r - 0.05, face=face, mat="Handguard", rail="hg_" + face)
                for face in ("top", "bottom", "left", "right")]
    c = r * math.tan(math.radians(22.5))
    hg = kit.prism("Handguard", [(c, r), (r, c), (r, -c), (c, -r), (-c, -r), (-r, -c), (-r, c), (-c, r)], 'y', h0, h1, "Handguard", "Root",
                   bevel=0.08, round_r=0.25)
    # M-LOK slots (the published spec: 32 mm by 7 mm, 40 mm apart) down both sides and along the bottom
    L, W, P = 3.2, 0.7, 4.0
    count = int((h1 - h0 - 1.6 - L) // P) + 1
    first = h0 + (h1 - h0 - (count - 1) * P) / 2           # the row centred on the handguard
    centres = [round(first + k * P, 3) for k in range(count)]
    for y in centres:
        for sx in (1, -1):
            slot = kit.prism("_slot", [(y - L / 2, -W / 2), (y + L / 2, -W / 2), (y + L / 2, W / 2), (y - L / 2, W / 2)], 'x',
                             sx * r - 0.6, sx * r + 0.6, "Handguard", "_cut", bevel=0.0, round_r=W / 2 - 0.01)
            kit.cut(hg, None, None, cutter=slot)
        slot = kit.prism("_slot", [(-W / 2, y - L / 2), (W / 2, y - L / 2), (W / 2, y + L / 2), (-W / 2, y + L / 2)], 'z',
                         -r - 0.6, -r + 0.6, "Handguard", "_cut", bevel=0.0, round_r=W / 2 - 0.01)
        kit.cut(hg, None, None, cutter=slot)
    mlok = [{"name": "mlok_" + face, "type": "mlok", "face": face, "surface": r, "y0": round(h0 + 0.3, 3), "y1": round(h1 - 0.3, 3),
             "slots": centres} for face in ("left", "right", "bottom")]
    # the top rail level with the upper's, on a riser along the handguard's top face
    kit.prism("HG_Riser", [(-0.9, r - 0.1), (0.9, r - 0.1), (0.9, RAIL_BASE), (-0.9, RAIL_BASE)], 'y', h0, h1, "Handguard", "Root",
              bevel=0.03)
    return [_rail(kit, "HG_Tooth", h0, h1, RAIL_BASE - 0.02, face="top", mat="Handguard", rail="hg_top")] + mlok
