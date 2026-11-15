# The room scan: splat builder and 3D room view

Built 15 Nov 2026 at Tom's request (D25 A). A video of the room becomes a 3D Gaussian splat in
seconds, and `GET /room` shows it with a pin where the memory says each thing is now.

## How it meshes with Save It

```
video or photo folder (laptop)
  -> scripts/build_room.py: cut frames, pick the sharpest evenly spaced 32, shrink to 448 px
  -> POST /build on the splat builder (GPU, through an SSH tunnel)
       AnySplat (one forward pass) -> filter, level, coarse copy on the GPU -> .spz files
  -> ROOM_DIR (.cache/room/): preview.spz, full.spz, scene.json

family -> GET /room -> GET /room/scene   the scan's views + landmark pins + ask.snapshot()
                    -> GET /room/splat   the .spz (preview first, then full)
                    -> PUT /room/pins    a tap in the 3D view -> landmarks.x/y/z
                    -> GET /moments/{sighting}/photo   the last-seen photo beside the answer
```

- **The scan is the stage, the database is still the only memory.** A scan is one moment; things
  move all day. The view never shows a thing where it was when the room was scanned. It asks
  `ask.snapshot()` where each item is now and flies to that landmark's pin.
- **Pins are `landmarks.x/y/z`** (the columns were already in `0001`; no migration). The family
  places each one once: Place pins, choose a place, tap it in the room. The backend matches the
  tap's ray against the scan's points (`geometry.pick_on_ray`).
- **Nothing else changed.** No model call on the read path, no change to perception, ingest,
  sightings or voice. `app/room.py` reads; its one write is a pin.

## Use it

```bash
scripts/splat_gpu.sh tunnel                      # its own terminal tab; reconnects by itself
uv run python -m scripts.build_room ~/Downloads/IMG_2101.MOV     # a slow 20 to 40 s walk
uv run python -m scripts.build_room photos/ --frames 48          # or a folder of photos
open "http://localhost:8000/room"                # type APP_TOKEN once, or add #token=...
```

- Film slowly, moving sideways, each landmark seen from at least two angles, in good light.
- On a slow network add `--full 400000` (about 3 MB instead of 8 to 13) or `--no-full`.
- No ffmpeg needed on a Mac: frames are cut with AVFoundation (`scripts/video_frames.swift`,
  compiled once into `.cache/bin/`). HEIC photos are converted with `sips`.
- Without a GPU: `SPLAT_MODEL=mock uv run python -m splat.server` serves a made-up room on the
  same API (for working on the page).

## The GPU machine

A Vast.ai RTX 4090 (24 GB), image `pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel`, label
`saveit-splat`. The builder listens on `127.0.0.1:8900` only; there is no public port.

```bash
vastai search offers 'gpu_name=RTX_4090 num_gpus=1 verified=true rentable=true inet_down>400 disk_space>=80 reliability>0.98 cuda_vers>=12.1' -o dph_total
vastai create instance <offer id> --image pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel --disk 60 --ssh --direct --label saveit-splat
rsync -az -e "ssh -p <port>" splat root@<host>:/workspace/splat-builder/
ssh -p <port> root@<host> 'bash /workspace/splat-builder/splat/setup_vast.sh'    # about 4 minutes
scripts/splat_gpu.sh status | restart | destroy
```

After changing anything in `splat/`: rsync again, then `scripts/splat_gpu.sh restart` (the model
reloads in about 25 s). **Destroy the instance after the event**: it bills about $0.47 an hour
while it exists.

## Builder API (`splat/server.py`)

| Call | Returns |
|---|---|
| `GET /health` | `{ok, model, gpu_name, models_loaded}` |
| `POST /build` (multipart `frames`, repeated; `max_frames`, `preview_gaussians`, `full_gaussians`) | the scene, as soon as its preview is ready |
| `POST /scenes`, `POST /scenes/{id}/frames`, `POST /scenes/{id}/build` | the same in steps, for frames sent as they are taken |
| `GET /scenes/{id}` | `{status, version, n_frames, gaussians, bytes, timings_ms, error}` |
| `GET /scenes/{id}/splat?level=preview\|full` | the `.spz` |
| `GET /scenes/{id}/cameras` | every camera and view, in viewer axes |
| `DELETE /scenes/{id}` | removes it from the GPU machine (`build_room.py` does this at the end) |

`status`: `capturing` -> `building` -> `ready_preview` (version 1) -> `ready` (version 2), or
`failed`. Frames stay in memory and are dropped when the build ends. `SPLAT_TOKEN` adds a Bearer
check if the builder is ever put behind something other than the tunnel.

## Why it is fast

Measured 15 Nov on the RTX 4090 with AnySplat's own sample scenes (no network):

| Scene | AnySplat | To preview | Both files | Gaussians from the model |
|---|---|---|---|---|
| 16 photos | 0.96 s | 1.34 s | 2.65 s | 2.1 million |
| 17 photos (kitchen) | 1.14 s | 1.50 s | 2.46 s | 1.7 million |
| 32 photos (apartment) | 2.19 s | 2.58 s | 3.94 s | 3.1 million |

From a video on Tom's Mac through the tunnel (17 frames, 606 KB up): preview saved after
**4.4 s**, both files after **5.8 s**. Earlier the same night, on the hall network at its worst
(about 30 KB/s up, 60 KB/s down): 44 s to the preview, 4 minutes to a 13 MB full file. The
network, not the GPU, decides; hence:

- **One forward pass, no training.** AnySplat predicts the Gaussians and every camera at once.
  Its transformer is 1.6 s of the 2.2 s for 32 photos.
- **Frames are chosen and shrunk on the laptop**: 32 squares of 448 px are about 1 MB. A video
  is never uploaded.
- **Straight to `.spz`** from the model's arrays (`splat/spz.py`): no PLY export, no converter
  subprocess. AnySplat's `export_ply` builds a Python tuple per Gaussian.
- **The work after the model runs on the GPU** (`scene.py`, `TorchScene`): 1.9 s in numpy became
  0.25 s for 3 million Gaussians.
- **Two files.** A coarse preview (one soft blob per grid cell, about 100,000, 0.75 MB) is
  published first and the viewer swaps the full file in behind it without moving the camera.
- **One request**: photos up, scene back when the preview exists.

Not built: the plan's refinement pass (gsplat, 60 to 90 s). AnySplat's instant result is what
the room view shows.

## Privacy

- A scan of a real home is as sensitive as the frames (D25). **Staged rooms only**, and keep
  people out of the walk: the frames go to a rented marketplace GPU.
- Frames sent to the builder are 448 px squares with no metadata; they are never written to disk
  there, and the scene is deleted from the GPU machine when `build_room.py` finishes.
- The scan lives in `ROOM_DIR` (`.cache/room/`, gitignored) on the backend's machine. `/room/*`
  data needs `APP_TOKEN`; the page takes it from `#token=` (never sent to a server) or a prompt,
  and keeps it for the tab only.
- Not done: the private-bucket copy D25 describes. A backend on another machine needs its own
  `build_room.py` run or a copy of `.cache/room/`.

## What differs from the plan Tom gave (`Splat memory assistant: build plan`)

- No Expo app: the capture side is a video or a photo folder, the viewer is a page of the Save
  It backend.
- Item positions come from the memory and landmark pins, not from masks at scan time, because
  the plan's items never move and ours do.
- `.spz` is written directly (gzip container, version 3) instead of PLY plus SplatTransform.
- The server keeps frames in memory instead of `data/scenes/<id>/frames/`.
- The viewer libraries (three.js 0.180.0, Spark 2.4.0) are served from `app/web/vendor/`, not a
  Vite build, to keep `app/web/` free of a build step and independent of the venue network.
- AnySplat needs `lightning`, `wandb`, `moviepy`, `scikit-video` and `colorspacious` installed
  even for inference (its package imports them); it does not need `pytorch3d` or `open3d`.
- AnySplat's cameras are camera-to-world in OpenCV axes (confirmed in its code); Spark shows an
  `.spz` as stored, with no flip, so the server writes viewer axes and levels the scene by the
  cameras' average up.
