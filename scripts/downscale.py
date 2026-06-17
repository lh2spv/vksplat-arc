"""Make a 1/N-downscaled copy of a COLMAP images/ dir for faster 3DGS training.

Per-pixel rasterization dominates 3DGS training time, so downscaling the input
images is the single biggest speed lever. 1/4 resolution = 1/16 the pixels.

VkSplat auto-rescales camera intrinsics from the actual loaded image dimensions,
so simply pointing --image-dir at the downscaled folder is enough. Naming the
folder images_2 / images_4 / images_8 also matches the gsplat convention.

Usage:
    python downscale.py <images_dir> [factor=4] [dst_dir]
"""
import os
import sys

import cv2

src = sys.argv[1]
factor = int(sys.argv[2]) if len(sys.argv) > 2 else 4
dst = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
    os.path.dirname(src.rstrip("/\\")), f"images_{factor}")

os.makedirs(dst, exist_ok=True)
exts = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
names = sorted(n for n in os.listdir(src) if n.lower().endswith(exts))
for i, n in enumerate(names):
    img = cv2.imread(os.path.join(src, n), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    out = cv2.resize(img, (w // factor, h // factor), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(dst, n), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"[{i+1}/{len(names)}] {n}  {w}x{h} -> {w//factor}x{h//factor}", flush=True)
print(f"DONE -> {dst}")
