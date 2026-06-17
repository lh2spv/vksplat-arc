"""Train a 3D Gaussian Splatting model with VkSplat on an Intel Arc (or any Vulkan) GPU.

VkSplat (https://github.com/harry7557558/vksplat, Apache-2.0) must be built and
importable first — see the repo README. This is a thin, path-safe driver around
its `simple_trainer.train()` that fixes the config gotchas needed on Windows/Arc.

Usage:
    python train_vksplat.py <dataset_dir> [options]

<dataset_dir> is a COLMAP workspace containing:
    <dataset_dir>/<image-dir>/   (images, e.g. images or images_4)
    <dataset_dir>/sparse/0/      (cameras.bin, images.bin, points3D.bin)

Run this from inside the VkSplat package dir (the folder holding simple_trainer.py
and the built vksplat .pyd), or pass --vksplat-dir.
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="Train 3DGS with VkSplat on a Vulkan GPU.")
    ap.add_argument("dataset_dir", help="COLMAP workspace (has <image-dir>/ and sparse/0/)")
    ap.add_argument("--out", default=None, help="output dir (default: <dataset_dir>/vksplat_out)")
    ap.add_argument("--image-dir", default="images",
                    help="image subfolder; use images_4 / images_2 for faster training")
    ap.add_argument("--sparse-dir", default="sparse/0", help="COLMAP sparse model subfolder")
    ap.add_argument("--steps", type=int, default=15000, help="training steps")
    ap.add_argument("--cache", choices=["cpu", "gpu"], default="gpu",
                    help="image cache location ('gpu' is faster when images fit in VRAM)")
    ap.add_argument("--device", type=int, default=-1, help="Vulkan device index, -1 = auto")
    ap.add_argument("--viewer", action="store_true", help="serve a live browser viewer while training")
    ap.add_argument("--viewer-port", type=int, default=7007)
    ap.add_argument("--vksplat-dir", default=None,
                    help="path to the VkSplat package dir (added to sys.path)")
    args = ap.parse_args()

    if args.vksplat_dir:
        sys.path.insert(0, os.path.abspath(args.vksplat_dir))

    try:
        import simple_trainer as st
        from simple_trainer import TrainerConfig
    except ImportError as e:
        sys.exit(f"Cannot import VkSplat's simple_trainer ({e}).\n"
                 f"Run from inside the VkSplat package dir or pass --vksplat-dir.")

    dataset = os.path.abspath(args.dataset_dir)
    out = os.path.abspath(args.out) if args.out else os.path.join(dataset, "vksplat_out")

    def sep(p):
        # VkSplat's C++ concatenates these directly (e.g. sparse_dir + "cameras.bin"),
        # so each must be an absolute path WITH a trailing separator.
        return p if p.endswith(os.sep) else p + os.sep

    st.TRAIN_DEVICE = args.device
    cfg = TrainerConfig(
        enable_viewer=args.viewer,
        viewer_port=args.viewer_port,
        output_dir=out,
        output_ply=os.path.join(out, "splat.ply"),
        train_steps=args.steps,
        dataset_dir=sep(dataset),
        image_dir=sep(os.path.join(dataset, args.image_dir)),
        sparse_dir=sep(os.path.join(dataset, *args.sparse_dir.split("/"))),
        mask_dir="",          # must be "" not None (C++ cast)
        image_cache_device=args.cache,
        save_train_renders=False,
    )

    print(f"=== VkSplat: device={args.device} steps={args.steps} "
          f"image_dir={args.image_dir} cache={args.cache} ===", flush=True)
    if args.viewer:
        print(f"Live viewer will serve at http://localhost:{args.viewer_port}", flush=True)
    st.train(cfg)
    print(f"=== DONE -> {os.path.join(out, 'splat.ply')} ===", flush=True)


if __name__ == "__main__":
    main()
