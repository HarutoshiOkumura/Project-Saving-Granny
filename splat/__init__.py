"""The room splat builder: photos of one room in, a 3D Gaussian splat and its cameras out.

A separate process for a GPU machine (`splat/server.py`, Python 3.10, its own requirements). The
Save It backend never imports the model code; `scripts/build_room.py` talks to the server over
HTTP and shares only the pure helpers here (`frames`, `spz`, `geometry`). See `docs/SPLAT.md`.
"""
