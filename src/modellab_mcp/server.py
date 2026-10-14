"""Model Lab as an MCP server (stdio). Run: modellab-mcp, or python -m modellab_mcp serve"""
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from . import __version__, core as M

mcp = MCPServer("modellab", title="Model Lab", version=__version__, instructions=(
    "Model Lab draws game gun models in Blender from a platform and its parameters: real parts at real proportions, "
    "one bone a moving part (Bolt, ChargingHandle, DustCover, Magazine, ...), and facts in gun space (cm, +X the gun's "
    "left, +Y forward, +Z up; the origin is the bolt face at rest on the bore): the chamber, the port, the magazine "
    "well, the grip and support marks, the rails and their slots. Every build checks itself: lengths against published "
    "figures, the cover over the port, the magazine in its well, the bolt's travel, the sight line, every visible part "
    "with its features (parts_complete). compare_to_reference measures a build's outline against a photo of the real "
    "gun. Attachments (list_attachments) mount on rail and M-LOK sockets. build_gun_clips keys the gun's own clips. "
    "Game models only: outside shapes and moving parts, no fabrication data. Start with list_presets, then build_gun, "
    "and look at the sheet it returns."))


def _call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (ValueError, FileNotFoundError, M.Busy, RuntimeError) as e:
        raise ToolError(str(e))


@mcp.tool()
def list_platforms() -> dict:
    """The gun families Model Lab can draw, with their parameter names."""
    return M.list_platforms()


@mcp.tool()
def describe_params(platform: Annotated[str, Field(description="a platform id, e.g. ar15")] = "ar15") -> dict:
    """A platform's parameters (type, range or choices, unit, meaning) and the sources its real numbers come from."""
    return _call(M.describe_params, platform)


@mcp.tool()
def list_presets() -> dict:
    """The ready guns (M4A1, M16A2, AR15, M4A1_Kitted, AR15_Optic): their parameters and the published lengths each
    build is checked against."""
    return M.list_presets()


@mcp.tool()
def list_attachments() -> dict:
    """The attachments a build can mount on the rails and M-LOK slots (optics, backup sights, the carry handle, a
    vertical grip, a light): what each is, the rails it fits, its states and moving parts. Pass them to build_gun as
    params.attachments."""
    return M.list_attachments()


@mcp.tool()
def list_references() -> dict:
    """The real-gun photos compare_to_reference measures against: each photo's source, licence, scale and the build
    that matches it."""
    return M.references()


@mcp.tool()
def build_gun(preset: Annotated[str | None, Field(description="a preset to start from, e.g. M4A1")] = None,
              params: Annotated[dict | None, Field(description="parameters to set or change, e.g. {\"barrel_in\": 16}")] = None,
              name: Annotated[str | None, Field(description="the model's name in its files (letters, digits, _)")] = None,
              scale: Annotated[float, Field(description="the whole model's scale; 1 is real size")] = 1.0,
              platform: Annotated[str | None, Field(description="without a preset: the platform to build")] = None,
              motion: Annotated[bool, Field(description="also render the moving parts' cycle as GIFs (about a minute more)")] = False) -> dict:
    """Builds a gun in Blender (15 to 30 s): the rig FBX, the hand magazine FBX, one FBX an attachment, the .blend
    (with the cycle as an action), facts.json and a sheet of labelled dev views; with motion, GIFs of the cycle.
    Returns the checks that failed (none when all_pass), the size and the files."""
    return _call(M.build, preset=preset, params=params, name=name, scale=scale, platform=platform, motion=motion)


@mcp.tool()
def build_gun_clips(build: Annotated[str, Field(description="a build folder name from list_builds")],
                    clips: Annotated[list[str] | None, Field(description="charge, chamber_check, fire, fire_last, reload, reload_empty, stock; leave out for all")] = None,
                    render: Annotated[bool, Field(description="render a labelled GIF a clip")] = True) -> dict:
    """The gun's own clips on a build's rig, from real beats and timings at 60 frames a second: each measured (parts on
    their axes, the bolt's stroke, the cover open before the carrier, the magazine out of the well and seated, the bolt
    held on its catch), exported alone as FBX (A_<name>_<clip>.fbx) and shown as a GIF."""
    return _call(M.clips, build, clips, render)


@mcp.tool()
def compare_to_reference(reference: Annotated[str, Field(description="a reference id from list_references")] = "m4a1_peo_side",
                         build: Annotated[str | None, Field(description="a build folder; leave out to build the reference's own configuration")] = None) -> dict:
    """The real-gun check: draws the build's side outline at the reference photo's scale and alignment, measures both
    outlines column by column, and returns the stretches that differ by more than 0.4 cm, each with the parts there
    and its zone (the gun, or an attachment over the rail), and an overlay picture (the model in red over the photo)."""
    return _call(M.compare, reference, build)


@mcp.tool()
def list_builds() -> list:
    """The latest builds, newest first: name, whether every check passed, size."""
    return M.list_builds()


@mcp.tool()
def read_build(build: Annotated[str, Field(description="a build folder name from list_builds")]) -> dict:
    """A build's facts: parameters, marks, moving parts, rails, attachments, the parts table, every check, files."""
    return _call(M.read_build, build)


def main():
    mcp.run()
