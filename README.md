# vksplat-arc

**Free, fully-local, license-free 3D Gaussian Splatting on an Intel Arc iGPU — no NVIDIA, no cloud.**

Helper scripts + a setup guide for training [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
with [VkSplat](https://github.com/harry7557558/vksplat) (Vulkan compute, Apache-2.0)
on an Intel Arc 140V. Verified end-to-end on Windows 11.

> This repo contains only the wrapper scripts and documentation. VkSplat itself,
> COLMAP, and the Vulkan SDK are installed separately (links below).

## Why this combination

The goal was 3DGS that is **free + fully local + license-free**, on a machine with
no NVIDIA GPU. The options:

| Backend | Free | Runs on Intel Arc | License |
|---|---|---|---|
| Original 3DGS (Inria, CUDA) | ✅ | ❌ CUDA-only | ❌ research / non-commercial |
| gsplat (nerfstudio) | ✅ | ❌ CUDA-only | ✅ Apache-2.0 |
| **VkSplat (Vulkan)** | ✅ | ✅ | ✅ **Apache-2.0** |

Only VkSplat clears all three: permissive license **and** it runs on the Arc's
Vulkan backend. (`gsplat` shares the license but needs CUDA; the Inria reference
runs nowhere without NVIDIA and is non-commercial.)

## What's here

- `scripts/photos_to_colmap.py` — photos → COLMAP workspace (offline CPU SfM).
- `scripts/downscale.py` — make a 1/N image copy; the biggest training-speed lever.
- `scripts/train_vksplat.py` — path-safe driver around VkSplat's `simple_trainer`,
  with a live browser viewer flag.

## Prerequisites

- **Vulkan SDK** — `winget install KhronosGroup.VulkanSDK` (sets `VULKAN_SDK`).
- **C++17 compiler** — MSVC (Visual Studio 2022 Build Tools) on Windows.
- **Python 3.8+** with `setuptools pybind11 numpy opencv-python tqdm`.
  (A fresh `python -m venv` omits `setuptools` — install it explicitly.)
- **COLMAP** — any build works; a no-CUDA `colmap.exe` keeps it fully local.

## Build VkSplat

```bash
git clone https://github.com/harry7557558/vksplat
cd vksplat/vksplat
# with VULKAN_SDK set in the environment:
python -m pip install -e . --no-build-isolation --no-deps -v
```

`--no-deps` skips `torchmetrics`/`torch` (only needed for evaluation, not training).
GLM is auto-cloned; the SPIR-V shaders ship precompiled.

### Gotchas that cost real debugging time

1. **Import from the package dir.** A folder named `vksplat` on your path shadows
   the built `.pyd`. Run the trainer from inside `vksplat/vksplat/`, or pass
   `--vksplat-dir`.
2. **`mask_dir` must be `""`, not `None`** — `None` fails the C++ cast. (Handled.)
3. **`sparse_dir` / `image_dir` need a trailing separator and an absolute path** —
   the C++ does naive string concat (`sparse_dir + "cameras.bin"`). (Handled.)

## Use it

```bash
# 1. photos -> COLMAP poses (skip if you already have sparse/0)
python scripts/photos_to_colmap.py path/to/photos --colmap path/to/colmap.exe

# 2. downscale for speed (1/4 res = ~13x faster; intrinsics auto-adjust)
python scripts/downscale.py path/to/workspace/images 4

# 3. train (run from the VkSplat package dir, or pass --vksplat-dir)
python scripts/train_vksplat.py path/to/workspace --image-dir images_4 --steps 15000
```

Output: `path/to/workspace/vksplat_out/splat.ply` (standard 3DGS PLY) + validation renders.

## Speed

Per-pixel rasterization is ~88% of step time, so **input resolution is the dominant
lever**. On the Arc 140V (mini scene, 13 training images):

| Image res | Throughput | 1000 steps |
|---|---|---|
| full (3072×2304) | ~9 steps/s | 108 s |
| 1/4 (`images_4`) | ~120 steps/s | 8.3 s |

A full 15000-step train at `images_4` took ~5.7 min (≈280k splats). Use
`--image-dir images_2` for a quality/speed middle ground, `--cache gpu` (default)
when images fit in VRAM.

## View the result

- **Live, in-browser, during training:** add `--viewer` and open
  `http://localhost:7007`. The Arc renders frames and streams them to the browser.
- **The saved `splat.ply`** is standard 3DGS format — open it in any splat viewer,
  e.g. [Brush](https://github.com/ArthurBrussee/brush) (`brush_app <splat.ply>`,
  Apache-2.0, WebGPU) locally or its web demo.

## Credits & licenses

- [VkSplat](https://github.com/harry7557558/vksplat) — Apache-2.0
- [COLMAP](https://github.com/colmap/colmap) — BSD
- [Brush](https://github.com/ArthurBrussee/brush) — Apache-2.0

The scripts in this repo are released under Apache-2.0 (see `LICENSE`).
