"""Convert a folder of photos -> COLMAP dataset (fully offline, CPU SfM).

Produces a workspace that both VkSplat and Brush can train on:

    <workspace>/
        images/         (copied photos)
        sparse/0/       (cameras.bin, images.bin, points3D.bin)

Requires a COLMAP binary. Set --colmap to its path (e.g. a no-CUDA colmap.exe).
GPU is disabled so it runs anywhere; use --matcher sequential for video frames.

Usage:
    python photos_to_colmap.py <photos_dir> --colmap path/to/colmap.exe [--workspace DIR]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def run(cmd):
    print(">>>", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos_dir", type=Path)
    ap.add_argument("--colmap", type=Path, required=True, help="path to colmap executable")
    ap.add_argument("--workspace", type=Path, default=None)
    ap.add_argument("--matcher", choices=["exhaustive", "sequential"], default="exhaustive")
    args = ap.parse_args()

    colmap = args.colmap
    photos_dir = args.photos_dir.resolve()
    if not photos_dir.is_dir():
        sys.exit(f"not a directory: {photos_dir}")

    photos = sorted(p for p in photos_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not photos:
        sys.exit(f"no images in {photos_dir}")
    print(f"found {len(photos)} images")

    workspace = (args.workspace or photos_dir.parent / f"{photos_dir.name}_colmap").resolve()
    images_out = workspace / "images"
    sparse_out = workspace / "sparse"
    db_path = workspace / "database.db"
    images_out.mkdir(parents=True, exist_ok=True)
    sparse_out.mkdir(exist_ok=True)

    print(f"workspace: {workspace}")
    for p in photos:
        dst = images_out / p.name
        if not dst.exists():
            shutil.copy2(p, dst)

    if db_path.exists():
        db_path.unlink()

    run([colmap, "feature_extractor",
         "--database_path", db_path,
         "--image_path", images_out,
         "--ImageReader.single_camera_per_folder", "1",
         "--FeatureExtraction.use_gpu", "0"])

    matcher = "exhaustive_matcher" if args.matcher == "exhaustive" else "sequential_matcher"
    run([colmap, matcher,
         "--database_path", db_path,
         "--FeatureMatching.use_gpu", "0"])

    run([colmap, "mapper",
         "--database_path", db_path,
         "--image_path", images_out,
         "--output_path", sparse_out])

    model_dirs = sorted(d for d in sparse_out.iterdir() if d.is_dir())
    if not model_dirs:
        sys.exit("mapper produced no model — try more/better-overlapping photos")
    print(f"models reconstructed: {[d.name for d in model_dirs]}")
    print(f"\nDONE -> {workspace}")
    print("Next: python downscale.py "
          f"\"{images_out}\" 4   then   python train_vksplat.py \"{workspace}\" --image-dir images_4")


if __name__ == "__main__":
    main()
