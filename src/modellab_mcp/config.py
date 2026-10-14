"""Where Model Lab writes, how it finds Blender, and what it waits for.

MODELLAB_OUT       the only folder Model Lab writes to (builds, clips, comparisons); defaults to ~/.modellab
MODELLAB_BLENDER   Blender's executable, if it is not on the PATH or in the usual install folder
MODELLAB_WAIT_FOR  optional: process names that hold the machine (e.g. "UnrealEditor.exe,blender.exe"); while one
                   runs, a build refuses to start (one heavy job at a time). Empty by default: no waiting.
MODELLAB_IDLE_OK   optional: parts of a command line that mark a long-lived worker (default "poselab_mcp"): such a
                   process counts only while it is busy (1 CPU second or more in 5 s)."""
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
SCRIPTS = PACKAGE / "blender"
REFS = PACKAGE / "refs"


def out():
    p = Path(os.environ.get("MODELLAB_OUT") or Path.home() / ".modellab")
    p.mkdir(parents=True, exist_ok=True)
    return p


def builds():
    p = out() / "builds"
    p.mkdir(parents=True, exist_ok=True)
    return p


def blender():
    """Blender: MODELLAB_BLENDER, the PATH, then the usual install folders."""
    for cand in (os.environ.get("MODELLAB_BLENDER"), shutil.which("blender")):
        if cand and Path(cand).exists():
            return Path(cand)
    pats = []
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), r"D:\Blender", r"C:\Blender"):
            pats += [os.path.join(base, "Blender Foundation", "Blender*", "blender.exe"), os.path.join(base, "blender.exe")]
    elif sys.platform == "darwin":
        pats += ["/Applications/Blender.app/Contents/MacOS/Blender"]
    else:
        pats += ["/usr/bin/blender", "/snap/bin/blender", os.path.expanduser("~/blender*/blender")]
    for pat in pats:
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return Path(hits[0])
    raise FileNotFoundError("Blender not found: install Blender 4.2 or later, or set MODELLAB_BLENDER to its executable")


def _processes():
    """(name, cpu seconds over 5 s, command line) for every running process whose name MODELLAB_WAIT_FOR lists."""
    names = [n.strip().lower() for n in os.environ.get("MODELLAB_WAIT_FOR", "").split(",") if n.strip()]
    if not names:
        return []
    rows = []
    if sys.platform == "win32":
        flt = " -or ".join("Name='%s'" % n for n in names)
        ps = ("$p = Get-CimInstance Win32_Process -Filter \"%s\"; $a = @{}; "
              "foreach ($x in $p) { $g = Get-Process -Id $x.ProcessId -ErrorAction SilentlyContinue; "
              "if ($g) { $a[$x.ProcessId] = $g.TotalProcessorTime.TotalSeconds } }; Start-Sleep -Seconds 5; "
              "foreach ($x in $p) { $g = Get-Process -Id $x.ProcessId -ErrorAction SilentlyContinue; if ($g) { "
              "'{0}|{1}|{2}' -f $x.Name, [math]::Round($g.TotalProcessorTime.TotalSeconds - $a[$x.ProcessId], 2), $x.CommandLine } }") % flt
        try:
            txt = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout
        except Exception:
            return [(n, 99.0, "") for n in names]
        for line in txt.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                try:
                    rows.append((parts[0].lower(), float(parts[1].replace(",", ".")), parts[2]))
                except ValueError:
                    rows.append((parts[0].lower(), 99.0, parts[2]))
        return rows

    def snap():
        try:
            txt = subprocess.run(["ps", "-eo", "pid=,time=,comm=,args="], capture_output=True, text=True, timeout=30).stdout
        except Exception:
            return {}
        got = {}
        for line in txt.splitlines():
            f = line.split(None, 3)
            if len(f) >= 3 and os.path.basename(f[2]).lower() in names:
                h, m, s = (["0"] * 3 + f[1].replace("-", ":").split(":"))[-3:]
                got[f[0]] = (os.path.basename(f[2]).lower(), int(h) * 3600 + int(m) * 60 + float(s), f[3] if len(f) > 3 else "")
        return got
    import time
    a = snap()
    if not a:
        return []
    time.sleep(5)
    b = snap()
    return [(v[0], v[1] - a[k][1], v[2]) for k, v in b.items() if k in a]


def busy():
    """The processes holding the machine (MODELLAB_WAIT_FOR), but for an idle long-lived worker (MODELLAB_IDLE_OK)."""
    idle_ok = [p for p in os.environ.get("MODELLAB_IDLE_OK", "poselab_mcp").split(",") if p.strip()]
    out_ = []
    for name, cpu, cmd in _processes():
        if any(p in cmd for p in idle_ok) and cpu < 1.0:
            continue
        out_.append(name)
    return out_
