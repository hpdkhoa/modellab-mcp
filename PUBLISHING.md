# Publishing Model Lab

The order matters. The MCP Registry accepts the listing only after the PyPI package is live. It also checks that the
README on PyPI carries `mcp-name: io.github.hpdkhoa/modellab-mcp`. README.md holds that line as an HTML comment.

## 1. GitHub

Make an empty repo `hpdkhoa/modellab-mcp` on GitHub (no README, no licence: both are here). Then, in this folder:

    git remote add origin https://github.com/hpdkhoa/modellab-mcp.git
    git push -u origin main

If GitHub made a first commit (a README or a licence), fetch it and build on it instead:

    git fetch origin
    git rebase origin/main
    git push -u origin main

## 2. PyPI

With uv:

    uv build
    uv publish --token <your PyPI token>

or with pip tools:

    python -m pip install build twine
    python -m build
    python -m twine upload dist/*

Check it: `uvx modellab-mcp` starts the server (it waits for a client on stdin; Ctrl+C to stop).

## 3. The MCP Registry

Install the publisher (one of):

    npm install -g mcp-publisher
    # or download mcp-publisher from https://github.com/modelcontextprotocol/registry/releases

Then, in this folder (server.json is here):

    mcp-publisher login github
    mcp-publisher publish

`login github` proves you own the io.github.hpdkhoa namespace. Search for it afterwards:
https://registry.modelcontextprotocol.io/v0/servers?search=modellab

## Each release

Run the checks first, with Blender found (MODELLAB_BLENDER or on the PATH) and MODELLAB_OUT set to a scratch
folder: `python examples/selftest.py` (0 failed) and `python examples/smoke.py` (every tool answers; the bad parameter
comes back as a tool error).

Raise the version in three places: `pyproject.toml`, `src/modellab_mcp/__init__.py`, and `server.json` (both
`version` fields). Add the release to CHANGELOG.md. Build and upload to PyPI first, then `mcp-publisher publish`.
