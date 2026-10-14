"""modellab: the command line, the same calls as the MCP tools.

    modellab serve                                      the MCP server on stdio (what modellab-mcp runs)
    modellab presets | platforms | params [<platform>] | attachments | references | builds
    modellab build <preset> [key=value ...] [name=<Name>] [scale=<s>] [motion=1]
    modellab clips <build> [clip ...] [render=0]
    modellab compare [<reference>] [<build>]
    modellab facts <build>

A value is read as JSON when it can be (barrel_in=16, selector=["SAFE","SEMI"]), else as text (handguard=mlok)."""
import json
import sys

from . import core as M


def _value(v):
    try:
        return json.loads(v)
    except ValueError:
        return v


def run(args):
    if not args or args[0] in ("-h", "--help", "help"):
        raise SystemExit(__doc__)
    cmd, rest = args[0], args[1:]
    if cmd == "serve":
        from .server import main as serve
        serve()
        return None
    if cmd == "presets":
        return M.list_presets()
    if cmd == "platforms":
        return M.list_platforms()
    if cmd == "params":
        return M.describe_params(rest[0] if rest else "ar15")
    if cmd == "attachments":
        return M.list_attachments()
    if cmd == "references":
        return M.references()
    if cmd == "builds":
        return M.list_builds()
    if cmd == "facts":
        return M.read_build(rest[0])
    if cmd == "build":
        preset = rest[0] if rest and "=" not in rest[0] else None
        kv = dict(a.split("=", 1) for a in rest[1 if preset else 0:])
        name = kv.pop("name", None)
        scale = float(kv.pop("scale", 1.0))
        motion = kv.pop("motion", "0") not in ("0", "false", "no")
        return M.build(preset=preset, params={k: _value(v) for k, v in kv.items()}, name=name, scale=scale, motion=motion)
    if cmd == "clips":
        names = [a for a in rest[1:] if "=" not in a] or None
        return M.clips(rest[0], names, "render=0" not in rest)
    if cmd == "compare":
        return M.compare(rest[0] if rest else "m4a1_peo_side", rest[1] if len(rest) > 1 else None)
    raise SystemExit(__doc__)


def main():
    out = run(sys.argv[1:])
    if out is not None:
        print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
