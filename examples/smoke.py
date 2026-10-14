"""Starts modellab-mcp over stdio as an MCP client would, lists its tools, calls the read-only ones, builds a gun and
asks for an error on a bad parameter (it must come back as a tool error, not a crash).
   python examples/smoke.py            (needs Blender for the build: MODELLAB_BLENDER or on the PATH)"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "modellab_mcp", "serve"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            print("tools:", tools)
            for name, args in (("list_platforms", {}), ("list_presets", {}), ("list_attachments", {}), ("list_references", {}),
                               ("describe_params", {"platform": "ar15"}), ("build_gun", {"preset": "AR15", "name": "SmokeAR15"}),
                               ("build_gun", {"preset": "AR15", "params": {"barrel_in": 99}})):
                res = await s.call_tool(name, args)
                text = "".join(getattr(c, "text", "") for c in res.content)
                err = getattr(res, "is_error", getattr(res, "isError", None))
                brief = text[:160].replace("\n", " ")
                if name == "build_gun" and not err:
                    d = json.loads(text)
                    brief = "build %s all_pass %s failed %s" % (d["build"], d["all_pass"], d["failed"])
                print("%-18s error=%s  %s" % (name, err, brief))


if __name__ == "__main__":
    asyncio.run(main())
