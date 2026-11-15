#!/usr/bin/env bash
# Set up the splat builder on a fresh GPU machine. These are the steps that worked on 15 Nov 2026
# on a Vast.ai RTX 4090 with the image pytorch/pytorch:2.2.0-cuda12.1-cudnn8-devel (Python 3.10,
# torch 2.2.0, CUDA 12.1: what AnySplat's pinned xformers and gsplat wheels need). About 4 minutes.
#
#   rsync -az splat root@HOST:/workspace/splat-builder/        # from the laptop, repo root
#   ssh root@HOST 'bash /workspace/splat-builder/splat/setup_vast.sh'
#
# It leaves the builder running on 127.0.0.1:8900 (splat/run.sh restarts it).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PIP_ROOT_USER_ACTION=ignore PIP_DISABLE_PIP_VERSION_CHECK=1

[ -d AnySplat ] || git clone -q --depth 1 https://github.com/OpenRobotLab/AnySplat.git

# AnySplat's requirements.txt minus what inference never touches (pytorch3d, open3d, gradio),
# plus the training-only packages its imports still pull in (lightning, wandb, moviepy, ...).
pip install -q -r splat/requirements.txt
pip install -q torch_scatter==2.1.2 -f https://data.pyg.org/whl/torch-2.2.0+cu121.html
pip install -q "https://github.com/nerfstudio-project/gsplat/releases/download/v1.4.0/gsplat-1.4.0%2Bpt22cu121-cp310-cp310-linux_x86_64.whl"

# The weights (2.9 GB, public, MIT). Downloaded once into ~/.cache/huggingface.
python -c "from huggingface_hub import snapshot_download; print(snapshot_download('lhjiang/anysplat'))"

bash splat/run.sh
