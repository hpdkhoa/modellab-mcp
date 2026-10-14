"""Model Lab's self-test: parameters are refused when they are wrong, every preset builds with every check passing
(lengths against the published figures, the cover over the port, the magazine in its well, the bolt's travel, the sight
line, every part's features), the clips pass their beats, and the M4A1's outline matches the real gun's photo.
Needs Blender (MODELLAB_BLENDER, or on the PATH); writes under MODELLAB_OUT (set it to a scratch folder).
   python examples/selftest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from modellab_mcp import config, core as M  # noqa: E402

fails = []


def expect(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


# parameters
expect(M.validate("ar15", {"barrel_in": 14.5, "handguard": "mlok"}) == [], "good parameters pass")
expect(any("barrel_in" in b for b in M.validate("ar15", {"barrel_in": 40})), "a 40 in barrel is refused")
expect(any("handguard" in b for b in M.validate("ar15", {"handguard": "wood"})), "an unknown handguard is refused")
expect(any("unknown parameter" in b for b in M.validate("ar15", {"colour": "red"})), "an unknown parameter is refused")
expect(any("stock_pos" in b for b in M.validate("ar15", {"stock_pos": 2.5})), "a half stock position is refused")
for name, preset in M.PRESETS.items():
    expect(M.validate(preset["platform"], preset["params"]) == [], "preset %s's own parameters pass" % name)
expect(all(s for s in M.describe_params("ar15")["sources"]), "the platform lists its sources")
expect(any("item must be one of" in b for b in M.validate("ar15", {"attachments": ["laser_sword"]})), "an unknown attachment is refused")
expect(any("state" in b for b in M.validate("ar15", {"attachments": [{"item": "holo", "state": "down"}]})),
       "a state on an attachment that does not move is refused")
expect("red_dot" in M.list_attachments()["items"], "the attachment catalogue lists the red dot")

# builds
if M._running():
    print("skip the builds: another heavy job runs (%s; MODELLAB_WAIT_FOR)" % ", ".join(M._running()))
else:
    for name in M.PRESETS:
        r = M.build(name, name="Test" + name)
        expect(r["all_pass"], "%s builds with every check passing %s" % (name, [c["id"] for c in r["failed"]]))
        facts = M.read_build(r["build"])
        for mark in ("chamber", "eject_port", "magwell", "mag_lips", "grip_r", "support_l", "muzzle"):
            expect(mark in facts["marks"], "%s has the mark %s" % (name, mark))
        for bone in ("Bolt", "ChargingHandle", "DustCover", "Magazine", "Trigger", "Selector"):
            expect(bone in facts["bones"], "%s has the bone %s" % (name, bone))
        expect(all(Path(f).exists() for f in facts["files"].values()), "%s wrote its rig, magazine and blend" % name)
        if name == "M4A1":
            got = {c["id"]: c["value"] for c in facts["checks"]}
            expect(abs(got["length_stock_0"] - 75.57) < 0.2 and abs(got["length_stock_4"] - 83.82) < 0.2,
                   "M4A1 is 29.75 and 33 in long (%s, %s)" % (got["length_stock_0"], got["length_stock_4"]))
        for a in facts.get("attachments", []):
            expect(Path(a["file"]).exists(), "%s wrote its attachment %s" % (name, a["name"]))
    # two red dots asked for the same slot: the second finds no place, and the build says so
    r = M.build("M4A1", {"attachments": [{"item": "red_dot", "slot": 10}, {"item": "red_dot", "slot": 10}]}, name="TestTwoDots")
    expect(not r["all_pass"] and any(c["id"] == "attachment_red_dot_2_mounts" for c in r["failed"]),
           "a second attachment on a taken slot fails its mount check")
    # a magnifier alone has no sight ahead of it to magnify
    r = M.build("AR15", {"attachments": ["magnifier"]}, name="TestLoneMagnifier")
    expect(any(c["id"] == "magnifier_behind_optic" for c in r["failed"]), "a magnifier with no optic ahead fails")
    # the M4's detachable carry handle: its A2 rear aperture on the line of the A2 front post
    r = M.build("M4A1", {"attachments": ["carry_handle"]}, name="TestCarryHandle")
    expect(r["all_pass"], "M4A1 with the carry handle passes every check %s" % [c["id"] for c in r["failed"]])
    # a 4x prism sight: its axis under the iron line, as real
    r = M.build("AR15", {"attachments": ["prism_4x"]}, name="TestPrism")
    expect(r["all_pass"], "AR15 with the 4x prism passes every check %s" % [c["id"] for c in r["failed"]])
    # the prism's eyepiece hangs over the rail behind it: a folded rear sight fits under it but cannot be raised
    r = M.build("AR15", {"attachments": [{"item": "flip_rear", "state": "down"}, "prism_4x"]}, name="TestPrismOverFlip")
    flip = next(a for a in M.read_build(r["build"])["attachments"] if a["name"] == "flip_rear")
    expect(r["all_pass"] and any(b.startswith("prism_4x") for b in flip["blocked_by"]),
           "a folded rear sight fits under the prism's eyepiece, and the prism blocks raising it %s" % flip["blocked_by"])
    # the gun's own clips: every beat measured (no pictures here, to keep the test quick)
    c = M.clips(M.build("M4A1_Kitted", name="TestClips")["build"], render=False)
    expect(c["all_pass"], "the clips pass every check %s" % {k: [f["id"] for f in v.get("failed", [])] for k, v in c["clips"].items()})
    expect(all(Path(v["fbx"]).exists() for v in c["clips"].values() if "fbx" in v), "each clip is written as FBX")
    # every visible part with its features: the build's parts check passes on every preset (above) and fails a part
    # with a feature missing
    import importlib.util
    import types
    sys.modules.setdefault("mathutils", types.SimpleNamespace(Vector=lambda *a: a))
    spec = importlib.util.spec_from_file_location("modellab_ar15", config.SCRIPTS / "modellab_ar15.py")
    ar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ar)
    facts = M.read_build(M.build("M4A1", name="TestParts")["build"])
    names = {n for n in facts["shape_bounds"]} | {"Castle_Nut_Notch", "Stock_Recess", "Stock_SlingSlot"}
    expect(all(not r["missing"] for r in ar.parts_check(ar.fill(facts["params"]), names)), "the M4A1's drawn shapes cover every part's features")
    gone = ar.parts_check(ar.fill(facts["params"]), {n for n in names if not n.startswith("Charging_Latch")})
    expect(any(r["part"] == "charging handle" and "latch" in r["missing"] for r in gone), "a charging handle without its latch fails the parts check")
    # the real-gun outline: the M4A1 against the PEO Soldier photo, the gun's own outline within 1 cm but for stretches
    # under 1.75 cm (the optic is its class, not the photo's model: kept apart)
    rep = M.compare("m4a1_peo_side")
    long_ = [f for f in rep["differences"] if f["zone"] == "gun" and f["length_cm"] > 1.75 and (f["worst_cm"] is None or abs(f["worst_cm"]) > 1.0)]
    expect(not long_, "the M4A1's outline matches the real gun's photo %s" % [(f["from_y"], f["to_y"], f["worst_cm"], f["near"][:3]) for f in long_])
    # a changed barrel drops the preset's length target instead of failing it
    r = M.build("M4A1", {"barrel_in": 16.0}, name="TestM4A1Long")
    expect(r["all_pass"] and not any(c["id"].startswith("length") for c in M.read_build(r["build"])["checks"]),
           "a changed barrel builds without the preset's length target")

print("\n%d failed" % len(fails))
sys.exit(1 if fails else 0)
