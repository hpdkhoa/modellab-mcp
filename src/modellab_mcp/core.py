"""Model Lab: draws game gun models in Blender from a platform and its parameters, with real parts at real
proportions, one bone a moving part, and the facts a game needs (the chamber, the port, the magazine well, the grip
and support marks, the rails and their sockets). Every build checks itself; compare checks its outline against a
photo of the real gun. Game models only: outside shapes and moving parts, no working internals, no fabrication data.
It writes only under MODELLAB_OUT (see config.py)."""
import json
import subprocess
import time
from pathlib import Path

from . import config

HERE = config.SCRIPTS        # the scripts Blender runs


def _root():
    return config.builds()


def _attach():
    """The attachment catalogue (blender/modellab_attach.py: plain data, no Blender needed to read it)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("modellab_attach", HERE / "modellab_attach.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Busy(RuntimeError):
    pass


IN = 2.54
CHOICES = {
    "gas": ["carbine", "mid", "rifle"],
    "handguard": ["round", "quad_rail", "mlok"],
    "front_sight": ["a2", "flip", "none"],
    "upper": ["flattop", "carry_handle"],
    "rear_sight": ["flip", "none"],
    "stock": ["carbine", "side_tubes", "a2"],
    "magazine": [20, 30],
    "muzzle": ["a2_birdcage", "none"],
    "grip": ["a2", "beavertail", "flared"],
    "grip_texture": ["auto", "checkered", "stippled", "none"],
    "magazine_type": ["gi_aluminum", "polymer"],
    "color": ["black", "fde", "odg", "wolf_gray", "tungsten", "coyote"],
}
PLATFORMS = {
    "ar15": {
        "name": "AR-15 family (AR-15, M4A1, M16A2)",
        "params": {
            "barrel_in": {"type": "number", "min": 7.5, "max": 24.0, "unit": "in", "meaning": "from the bolt face to the crown"},
            "gas": {"type": "choice", "choices": CHOICES["gas"], "meaning": "where the gas block (or the A2 front sight) sits"},
            "handguard": {"type": "choice", "choices": CHOICES["handguard"]},
            "handguard_in": {"type": "number", "min": 4.0, "max": 16.0, "unit": "in", "meaning": "leave out: up to the gas block"},
            "front_sight": {"type": "choice", "choices": CHOICES["front_sight"]},
            "upper": {"type": "choice", "choices": CHOICES["upper"], "meaning": "carry_handle has its own rear sight"},
            "rear_sight": {"type": "choice", "choices": CHOICES["rear_sight"], "meaning": "on a flattop"},
            "stock": {"type": "choice", "choices": CHOICES["stock"], "meaning": "carbine: the M4's; side_tubes: with battery tubes down its sides; a2: fixed"},
            "stock_pos": {"type": "integer", "min": 0, "max": 4, "meaning": "a carbine stock: 0 all the way in, 4 all out"},
            "magazine": {"type": "choice", "choices": CHOICES["magazine"], "unit": "rounds"},
            "muzzle": {"type": "choice", "choices": CHOICES["muzzle"]},
            "selector": {"type": "list", "meaning": "the marks round the selector, e.g. SAFE SEMI AUTO"},
            "grip": {"type": "choice", "choices": CHOICES["grip"], "meaning": "a2: the finger nub; beavertail: smooth, a beavertail; flared: no nub, the base flared forward"},
            "grip_texture": {"type": "choice", "choices": CHOICES["grip_texture"],
                             "meaning": "the grip's side panels: auto (checkered on the A2, stippled on the others), checkered, stippled, none"},
            "magazine_type": {"type": "choice", "choices": CHOICES["magazine_type"], "meaning": "GI aluminium (pressed ribs) or polymer (a ribbed floor)"},
            "receiver_color": {"type": "choice", "choices": CHOICES["color"], "meaning": "the upper, the lower and the metal parts"},
            "furniture_color": {"type": "choice", "choices": CHOICES["color"], "meaning": "the stock and the grip"},
            "handguard_color": {"type": "choice", "choices": CHOICES["color"], "meaning": "leave out: the furniture's for a round handguard, the receiver's for a rail"},
            "magazine_color": {"type": "choice", "choices": CHOICES["color"], "meaning": "leave out: wolf gray for GI, black for polymer"},
            "attachments": {"type": "attachments",
                            "meaning": "what goes on the rails: item names, or {item, rail, slot, state, options} (see list_attachments); "
                                       "slot a number (0 the rearmost) or front, rear, middle. Leave out: the flip sights that "
                                       "front_sight and rear_sight ask for. Given, it is the whole list"},
        },
        "sources": [
            "M4 carbine: 14.5 in barrel, 33 in with the stock out, 29.75 in with it in (en.wikipedia.org/wiki/M4_carbine)",
            "M16A2: 20 in barrel, 39.63 in long (en.wikipedia.org/wiki/M16_rifle; globalsecurity.org m16-specs)",
            "30-round magazine 2.25 in front to back, 1.125 in wide (Mission First Tactical listing, gun.deals)",
            "mil-spec carbine buffer tube 1.148 in across; A2 rifle tube 9 5/8 in long (Brownells)",
            "ejection port door about 3.1 in long (Brownells)",
            "rail: MIL-STD-1913, 0.835 in wide, slots every 0.394 in",
            "M-LOK: slots 32 mm by 7 mm, 40 mm apart (the published spec)",
            "attachments: real classes at real proportions (a 30 mm red dot of the M68 CCO class, a holographic sight, a "
            "3x magnifier on a flip mount, a 4x32 prism sight, folding backup sights, the M4 carry handle); "
            "absolute co-witness about 1.41 in over a flattop rail; see modellab_attach.py",
            "colours: the trade's finish names (anodized black, Flat Dark Earth, OD green, wolf gray, tungsten, "
            "coyote), the colours by eye",
            "estimates: the receiver's outline, the sight line at 2.5 in over the bore, the gas port distances, the "
            "carrier's 8.4 cm travel and the catch at 7.6 cm, magazine heights",
        ],
    },
}
PRESETS = {
    "M4A1": {"platform": "ar15", "real_model": "the M4A1 carbine, 5.56x45",
             "params": {"barrel_in": 14.5, "gas": "carbine", "handguard": "quad_rail", "front_sight": "a2", "upper": "flattop",
                        "rear_sight": "flip", "stock": "carbine", "stock_pos": 4, "magazine": 30, "muzzle": "a2_birdcage",
                        "selector": ["SAFE", "SEMI", "AUTO"]},
             "targets": {"oal_cm": {"0": round(29.75 * IN, 2), "4": round(33.0 * IN, 2)}, "source": "Wikipedia, M4 carbine: 29.75 and 33 in"}},
    "M16A2": {"platform": "ar15", "real_model": "M16A2 rifle, 5.56x45",
              "params": {"barrel_in": 20.0, "gas": "rifle", "handguard": "round", "front_sight": "a2", "upper": "carry_handle",
                         "stock": "a2", "magazine": 30, "muzzle": "a2_birdcage", "selector": ["SAFE", "SEMI", "BURST"]},
              "targets": {"oal_cm": round(39.63 * IN, 2), "source": "Wikipedia, M16 rifle; GlobalSecurity: 39.63 in"}},
    "M4A1_Kitted": {"platform": "ar15", "real_model": "M4A1 with a SOPMOD Block I style kit: red dot, backup rear sight folded, "
                                                      "vertical grip and a light on the rail handguard",
                    "params": {"barrel_in": 14.5, "gas": "carbine", "handguard": "quad_rail", "front_sight": "a2", "upper": "flattop",
                               "stock": "carbine", "stock_pos": 4, "magazine": 30, "muzzle": "a2_birdcage",
                               "selector": ["SAFE", "SEMI", "AUTO"],
                               "attachments": [{"item": "flip_rear", "state": "down"}, "red_dot", "vertical_grip", "weapon_light"]},
                    "targets": {"oal_cm": {"0": round(29.75 * IN, 2), "4": round(33.0 * IN, 2)},
                                "source": "Wikipedia, M4 carbine: 29.75 and 33 in"}},
    "AR15": {"platform": "ar15", "real_model": "a civilian AR-15, 16 in barrel, semi-automatic",
             "params": {"barrel_in": 16.0, "gas": "mid", "handguard": "mlok", "handguard_in": 13.0, "front_sight": "flip",
                        "upper": "flattop", "rear_sight": "flip", "stock": "carbine", "stock_pos": 3, "magazine": 30,
                        "muzzle": "a2_birdcage", "selector": ["SAFE", "SEMI"], "grip": "flared", "magazine_type": "polymer",
                        "receiver_color": "tungsten", "furniture_color": "fde", "magazine_color": "fde"},
             "targets": {}},
    "AR15_Optic": {"platform": "ar15", "real_model": "a civilian AR-15 with a holographic sight and a 3x magnifier, backup sights "
                                                     "folded, a light and a vertical grip on M-LOK",
                   "params": {"barrel_in": 16.0, "gas": "mid", "handguard": "mlok", "handguard_in": 13.0, "front_sight": "flip",
                              "upper": "flattop", "rear_sight": "flip", "stock": "side_tubes", "stock_pos": 3, "magazine": 30,
                              "muzzle": "a2_birdcage", "selector": ["SAFE", "SEMI"], "grip": "flared", "magazine_type": "polymer",
                              "receiver_color": "black", "furniture_color": "fde", "magazine_color": "fde",
                              "attachments": [{"item": "flip_rear", "state": "down"}, {"item": "flip_front", "state": "down"},
                                              "magnifier", "holo", "weapon_light", "vertical_grip"]},
                   "targets": {}},
}


def list_platforms():
    return {k: {"name": v["name"], "params": list(v["params"])} for k, v in PLATFORMS.items()}


def describe_params(platform="ar15"):
    if platform not in PLATFORMS:
        raise ValueError("no platform %r; platforms: %s" % (platform, ", ".join(PLATFORMS)))
    return PLATFORMS[platform]


def list_presets():
    return {k: {"platform": v["platform"], "real_model": v["real_model"], "params": v["params"], "targets": v["targets"]}
            for k, v in PRESETS.items()}


def list_attachments():
    """The attachments a build can mount: what each is, what it mounts on, the rails it goes to, its states and moves."""
    A = _attach()
    return {"items": {k: {"about": v["about"], "kind": v["kind"], "mount": v["mount"], "rails": v["rails"], "place": v["place"],
                          "states": v["states"], "default_state": v["default"], "moving": v["moving"], "options": v.get("options", {}),
                          "axis": "on the iron sight line (absolute co-witness)" if v["axis"] == "co_witness" else
                                  ("%.1f cm over the rail" % v["axis"] if v["axis"] else None)}
                      for k, v in A.ITEMS.items()},
            "rails": "upper (the flattop), hg_top, hg_bottom, hg_left, hg_right (a quad rail), mlok_left, mlok_right, "
                     "mlok_bottom (an M-LOK handguard, with its hg_top rail); a round handguard has none",
            "note": "the A2 front sight base is not an attachment: it is pinned to the barrel and is the gas block"}


def validate(platform, params):
    """Problems with parameters against the platform's schema; [] when they are fine."""
    schema = describe_params(platform)["params"]
    bad = []
    for k, v in params.items():
        if k not in schema:
            bad.append("unknown parameter %r; parameters: %s" % (k, ", ".join(schema)))
            continue
        s = schema[k]
        if v is None:
            continue
        if s["type"] == "choice" and v not in s["choices"]:
            bad.append("%s must be one of %s, got %r" % (k, s["choices"], v))
        elif s["type"] in ("number", "integer"):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                bad.append("%s must be a number, got %r" % (k, v))
            elif not s["min"] <= v <= s["max"]:
                bad.append("%s must be %s to %s %s, got %s" % (k, s["min"], s["max"], s.get("unit", ""), v))
            elif s["type"] == "integer" and int(v) != v:
                bad.append("%s must be a whole number, got %s" % (k, v))
        elif s["type"] == "attachments":
            bad += _attach().validate(v)
        elif s["type"] == "list" and not (isinstance(v, list) and all(isinstance(x, str) for x in v) and 1 <= len(v) <= 3):
            bad.append("%s must list one to three marks, got %r" % (k, v))
    return bad


def _running():
    return config.busy()


def build(preset=None, params=None, name=None, scale=1.0, platform=None, motion=False):
    """Builds a gun: a preset, with params changing any of its parameters, or a platform and params alone. Returns
    the build's summary: its checks, its files and its picture sheet. motion: also renders the moving parts' cycle
    (pull the handle, let it fly, drop and seat the magazine, shut the cover) as GIFs, about two minutes more."""
    if preset is not None and preset not in PRESETS:
        raise ValueError("no preset %r; presets: %s" % (preset, ", ".join(PRESETS)))
    base = PRESETS[preset] if preset else {"platform": platform or "ar15", "params": {}, "targets": {}}
    plat = base["platform"]
    p = dict(base["params"], **(params or {}))
    bad = validate(plat, p)
    if bad:
        raise ValueError("; ".join(bad))
    if not 0.1 <= float(scale) <= 10.0:
        raise ValueError("scale must be 0.1 to 10, got %s" % scale)
    name = name or preset or "Gun"
    if not name.replace("_", "").isalnum():
        raise ValueError("name: letters, digits and _ only, got %r" % name)
    busy = _running()
    if busy:
        raise Busy("another heavy job runs (%s; MODELLAB_WAIT_FOR): one at a time" % ", ".join(busy))
    # targets hold only for the preset's own parameters: a changed barrel or stock changes the length
    changed = {k for k in (params or {}) if base["params"].get(k) != params[k]}
    targets = base["targets"] if not (changed & {"barrel_in", "stock", "muzzle"}) else {}
    out = ensure_dir(_root() / ("%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), name)))
    job = {"platform": plat, "name": name, "params": p, "targets": targets, "scale": float(scale), "out": str(out), "motion": bool(motion),
           "tools": str(HERE)}
    (out / "job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    t0 = time.time()
    r = subprocess.run([str(config.blender()), "-b", "--factory-startup", "-P", str(HERE / "modellab_blender.py"), "--", str(out / "job.json")],
                       capture_output=True, text=True, timeout=1200)
    (out / "blender.log").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8", errors="replace")
    facts_path = out / "facts.json"
    if not facts_path.exists():
        tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()][-12:]
        raise RuntimeError("the build wrote no facts; see %s:\n%s" % (out / "blender.log", "\n".join(tail)))
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    sheet = _sheet(out, name, facts)
    gifs = _motion_gifs(out, name, facts)
    return {"build": out.name, "folder": str(out), "seconds": round(time.time() - t0, 1), "all_pass": facts["all_pass"],
            "failed": [c for c in facts["checks"] if not c["pass"]], "checks": len(facts["checks"]),
            "size_cm": facts["size_cm"], "triangles": facts["triangles"], "files": facts["files"], "sheet": sheet,
            "motion": gifs, "action": facts.get("action")}


def clips(build, names=None, render=True):
    """The gun's own clips on a build's rig (modellab_clips.py): charge, chamber_check, fire, fire_last, reload,
    reload_empty, stock. Each is keyed at 60 frames a second from real beats, measured, exported alone as FBX and,
    with render, shown as a labelled GIF. Returns each clip's checks and files."""
    folder = _root() / build
    facts_path = folder / "facts.json"
    if not facts_path.exists():
        raise FileNotFoundError("no build %r; see list_builds" % build)
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    busy = _running()
    if busy:
        raise Busy("another heavy job runs (%s; MODELLAB_WAIT_FOR): one at a time" % ", ".join(busy))
    out = ensure_dir(folder / "clips")
    job = {"facts": str(facts_path), "out": str(out), "clips": names, "render": bool(render)}
    (out / "clips_job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    t0 = time.time()
    r = subprocess.run([str(config.blender()), "-b", str(folder / ("%s.blend" % facts["name"])), "-P", str(HERE / "modellab_clips.py"), "--",
                        str(out / "clips_job.json")], capture_output=True, text=True, timeout=3600)
    (out / "blender.log").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8", errors="replace")
    rep_path = out / "clips.json"
    if not rep_path.exists():
        tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()][-12:]
        raise RuntimeError("the clips wrote no report; see %s:\n%s" % (out / "blender.log", "\n".join(tail)))
    report = json.loads(rep_path.read_text(encoding="utf-8"))
    summary = {}
    for cname, c in report["clips"].items():
        if "skipped" in c:
            summary[cname] = c
            continue
        gif = _clip_gif(out, facts["name"], cname, c)
        summary[cname] = {"all_pass": c["all_pass"], "failed": [k for k in c["checks"] if not k["pass"]], "seconds": c["seconds"],
                          "fbx": c["fbx"], "gif": gif, "about": c["about"]}
    return {"build": build, "seconds": round(time.time() - t0, 1), "all_pass": all(v.get("all_pass", True) for v in summary.values()),
            "clips": summary, "report": str(rep_path)}


def _clip_gif(out, name, cname, c):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    frames = []
    for fr in c.get("render", []):
        if not Path(fr["path"]).exists():
            continue
        im = Image.open(fr["path"]).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, im.width, 24), fill=(0, 0, 0))
        d.text((6, 6), "DEV VIEW (Blender, Model Lab %s, not in game): clip %s" % (name, cname), fill=(255, 255, 0))
        d.rectangle((0, im.height - 26, im.width, im.height), fill=(0, 0, 0))
        slow = c.get("slow", 1)
        d.text((6, im.height - 20), "t = %.3f s%s" % (fr["t"], "   slow motion x%d" % slow if slow > 1 else ""), fill=(255, 255, 255))
        frames.append(im.quantize(colors=128))
    if not frames:
        return None
    slow = c.get("slow", 1)
    ms = int(1000 / 60 * slow) if slow > 1 else int(1000 / 30)
    path = out / ("clip_%s.gif" % cname)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=max(ms, 20), loop=0)
    return str(path)


def references():
    """The real-gun references the outline check measures against (the package's refs folder)."""
    return json.loads((config.REFS / "references.json").read_text(encoding="utf-8"))


def _outline(mask, w, h):
    """Each column's top and bottom dark row in a mask (a function (x, y) -> dark), or None."""
    cols = []
    for x in range(w):
        t = b = None
        for y in range(h):
            if mask(x, y):
                if t is None:
                    t = y
                b = y
        cols.append((t, b))
    return cols


def compare(ref="m4a1_peo_side", build_name=None, threshold_cm=0.4, min_run_cm=0.6):
    """The real-gun check: builds the reference's configuration (or uses build_name), draws its side outline exactly as
    the reference photo shows the real gun, and measures the two outlines column by column. Returns the stretches
    where they differ by more than threshold_cm, each with the model's shapes there, and an overlay picture."""
    from PIL import Image, ImageDraw
    R = references()[ref]
    photo = Image.open(config.REFS / R["file"]).convert("RGB")
    W, H = photo.size
    e0, e1 = R["scale"]["edges_px"]
    S = R["scale"]["slots"] * 0.394 * IN / (e1 - e0)
    px = photo.load()
    dark = lambda x, y: sum(px[x, y]) / 3 < R["dark_below"]
    pcols = _outline(dark, W, H)
    muzzle_col = max(x for x, (t, b) in enumerate(pcols) if t is not None)
    if build_name is None:
        b = R["build"]
        build_name = build(b["preset"], b.get("params"), name="Ref_" + ref.split("_")[0].upper())["build"]
    folder = _root() / build_name
    facts = json.loads((folder / "facts.json").read_text(encoding="utf-8"))
    out = ensure_dir(folder / "compare")
    job = {"facts": str(folder / "facts.json"), "width": W, "height": H, "cm_per_px": S, "bore_row": R["bore_row_px"],
           "muzzle_col": muzzle_col, "out": str(out / ("%s_render.png" % ref))}
    (out / "compare_job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    busy = _running()
    if busy:
        raise Busy("another heavy job runs (%s; MODELLAB_WAIT_FOR): one at a time" % ", ".join(busy))
    subprocess.run([str(config.blender()), "-b", str(folder / ("%s.blend" % facts["name"])), "-P", str(HERE / "modellab_compare.py"), "--",
                    str(out / "compare_job.json")], capture_output=True, text=True, timeout=600)
    render = Image.open(job["out"]).convert("RGB")
    rpx = render.load()
    mcols = _outline(lambda x, y: sum(rpx[x, y]) / 3 < 128, W, H)
    B = R["bore_row_px"]
    muzzle_y = facts["marks"]["muzzle"]["at"][1]
    gy = lambda x: round(muzzle_y + (x - muzzle_col) * S, 2)
    gz = lambda row: round((B - row) * S, 2)
    # the stretches: per edge, the columns where the photo and the model differ by more than the threshold
    spans = []
    for edge, k in (("top", 0), ("bottom", 1)):
        run = []
        for x in range(W):
            pr, mr = pcols[x][k], mcols[x][k]
            if pr is None and mr is None:
                diff = None
            elif pr is None or mr is None:
                diff = 99.0
            else:
                diff = (mr - pr) * S * (1 if k == 0 else -1)   # + : the model reaches less far than the real gun
            if diff is not None and abs(diff) > threshold_cm:
                run.append((x, diff, pr, mr))
            elif run:
                spans.append((edge, run))
                run = []
        if run:
            spans.append((edge, run))
    bounds = facts.get("shape_bounds", {})
    found = []
    for edge, run in spans:
        if (run[-1][0] - run[0][0] + 1) * S < min_run_cm:
            continue
        y0, y1 = gy(run[0][0]), gy(run[-1][0])
        big = max(run, key=lambda r: abs(r[1]))
        zp = gz(big[2]) if big[2] is not None else None
        zm = gz(big[3]) if big[3] is not None else None
        # the model's shapes there: overlapping the stretch, their edge near the outline the model draws
        near = []
        for n, (lo, hi) in bounds.items():
            if hi[1] < y0 - 0.3 or lo[1] > y1 + 0.3:
                continue
            ez = hi[2] if edge == "top" else lo[2]
            if zm is not None and abs(ez - zm) < 0.6 or zp is not None and abs(ez - zp) < 1.0:
                near.append(n)
        # over the rail's top, on the top edge: an attachment's outline (the reference's optic or sight is a real model,
        # the attachment its class), kept apart from the gun's own
        rail_top = facts["marks"].get("rail_top", {}).get("at", [0, 0, 99])[2]
        zone = "attachment" if edge == "top" and max(z for z in (zp, zm) if z is not None) > rail_top + 0.4 else "gun"
        found.append({"zone": zone, "edge": edge, "from_y": y0, "to_y": y1, "length_cm": round(y1 - y0, 2),
                      "worst_cm": round(big[1], 2) if big[1] != 99.0 else None,
                      "real_z": zp, "model_z": zm, "kind": "the model is short of the real gun" if big[1] > 0 else "the model stands out past the real gun",
                      "near": sorted(set(near))[:8]})
    found.sort(key=lambda f: -(f["length_cm"] * (abs(f["worst_cm"]) if f["worst_cm"] else 3)))
    # the overlay: the photo, with the model's outline drawn over it
    # the model's silhouette laid over the photo in see-through red: red where only the model is, the photo's dark
    # where only the real gun is, both where they agree
    mask = render.convert("L").point(lambda v: 110 if v < 128 else 0)
    red = Image.new("RGB", (W, H), (230, 30, 30))
    over = Image.composite(red, photo, mask)
    over = Image.blend(photo, over, 0.6)
    d = ImageDraw.Draw(over)
    for f in found:
        x0 = muzzle_col + (f["from_y"] - muzzle_y) / S
        x1 = muzzle_col + (f["to_y"] - muzzle_y) / S
        yy = 2 if f["edge"] == "top" else H - 6
        d.rectangle((x0, yy, x1, yy + 4), fill=(20, 90, 230))
    big = over.resize((W * 2, H * 2))
    canvas = Image.new("RGB", (W * 2, H * 2 + 30), (0, 0, 0))
    canvas.paste(big, (0, 30))
    ImageDraw.Draw(canvas).text((8, 9), "DEV VIEW (Model Lab %s outline in red over the real-gun photo %s; blue bars: differences over %.1f cm)"
                                % (facts["name"], R["file"], threshold_cm), fill=(255, 255, 0))
    overlay = out / ("%s_overlay.png" % ref)
    canvas.save(overlay)
    both = sum(1 for x in range(W) if pcols[x][0] is not None and mcols[x][0] is not None)
    report = {"reference": ref, "build": build_name, "cm_per_px": round(S, 5), "columns_compared": both, "differences": found,
              "overlay": str(overlay), "render": job["out"]}
    (out / ("%s_report.json" % ref)).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)
    return p


def _sheet(out, name, facts):
    """One picture of every view, each labelled as a dev view (they are Blender renders, not the game)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    views = [v for v in facts.get("views", []) if Path(v["path"]).exists()]
    if not views:
        return None
    w, h = 800, 450
    cols = 3
    rows = (len(views) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), (40, 40, 40))
    for i, v in enumerate(views):
        im = Image.open(v["path"]).convert("RGB").resize((w, h))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w, 22), fill=(0, 0, 0))
        d.text((6, 5), "DEV VIEW (Blender, Model Lab %s, not in game): %s" % (name, v["view"]), fill=(255, 255, 0))
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    path = out / "sheet.png"
    sheet.save(path)
    return str(path)


def _motion_gifs(out, name, facts):
    """The cycle's frames joined into one GIF a view, every frame labelled a dev view with its phase."""
    m = facts.get("motion")
    if not m:
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    phases = m["phases"]
    gifs = {}
    for view, paths in m["views"].items():
        frames = []
        for i, path in enumerate(paths, start=1):
            if not Path(path).exists():
                continue
            im = Image.open(path).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, im.width, 24), fill=(0, 0, 0))
            d.text((6, 6), "DEV VIEW (Blender, Model Lab %s, not in game): motion, %s" % (name, view), fill=(255, 255, 0))
            now = [p["name"] for p in phases if p["frame"] <= i][-1]
            d.rectangle((0, im.height - 26, im.width, im.height), fill=(0, 0, 0))
            d.text((6, im.height - 20), "frame %d/%d  %s" % (i, m["frames"], now), fill=(255, 255, 255))
            frames.append(im.quantize(colors=128))
        if not frames:
            continue
        path = out / ("motion_%s.gif" % view)
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / m["fps"]), loop=0)
        gifs[view] = str(path)
    return gifs


def list_builds(limit=20):
    if not _root().exists():
        return []
    rows = []
    for d in sorted((p for p in _root().iterdir() if p.is_dir()), reverse=True)[:limit]:
        f = d / "facts.json"
        if f.exists():
            facts = json.loads(f.read_text(encoding="utf-8"))
            rows.append({"build": d.name, "name": facts["name"], "all_pass": facts["all_pass"], "size_cm": facts["size_cm"]})
        else:
            rows.append({"build": d.name, "failed": "no facts (see blender.log)"})
    return rows


def read_build(build):
    d = _root() / build
    f = d / "facts.json"
    if not f.exists():
        raise FileNotFoundError("no build %r with facts under %s" % (build, _root()))
    facts = json.loads(f.read_text(encoding="utf-8"))
    facts["sheet"] = str(d / "sheet.png") if (d / "sheet.png").exists() else None
    return facts
