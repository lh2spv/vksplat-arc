# vksplat-arc

**完全無料・完全ローカル・ライセンスフリーの 3D ガウシアンスプラッティングを Intel Arc 内蔵GPUで — NVIDIA不要・クラウド不要。**

[VkSplat](https://github.com/harry7557558/vksplat)（Vulkan compute, Apache-2.0）を使い、
[3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) を
Intel Arc 140V で学習するためのヘルパースクリプトとセットアップ手順です。
Windows 11 でエンドツーエンド動作確認済み。

> このリポジトリには**ラッパースクリプトと手順だけ**を収録しています。
> VkSplat 本体・COLMAP・Vulkan SDK は別途インストールします（下記リンク参照）。

## なぜこの組み合わせなのか

目標は **無料 + 完全ローカル + ライセンスフリー** な 3DGS を、NVIDIA GPU の無いマシンで実現すること。
選択肢は次の通りです:

| バックエンド | 無料 | Intel Arc で動く | ライセンス |
|---|---|---|---|
| オリジナル 3DGS（Inria, CUDA） | ✅ | ❌ CUDA専用 | ❌ 研究・非商用 |
| gsplat（nerfstudio） | ✅ | ❌ CUDA専用 | ✅ Apache-2.0 |
| **VkSplat（Vulkan）** | ✅ | ✅ | ✅ **Apache-2.0** |

3条件すべてを満たすのは VkSplat だけです。寛容なライセンスを持ち、**かつ** Arc の Vulkan
バックエンドで動きます。（`gsplat` はライセンスは同じでも CUDA が必要。Inria 版は NVIDIA が
無いと動かず、しかも非商用です。）

## 収録物

- `scripts/photos_to_colmap.py` — 写真 → COLMAP ワークスペース（オフラインCPU SfM）。
- `scripts/downscale.py` — 画像を 1/N に縮小。学習速度の最大のレバー。
- `scripts/train_vksplat.py` — VkSplat の `simple_trainer` をパス安全に呼ぶドライバ。
  ライブブラウザビューア用フラグ付き。

## 前提条件

- **Vulkan SDK** — `winget install KhronosGroup.VulkanSDK`（`VULKAN_SDK` が設定される）。
- **C++17 コンパイラ** — Windows では MSVC（Visual Studio 2022 Build Tools）。
- **Python 3.8+** と `setuptools pybind11 numpy opencv-python tqdm`。
  （`python -m venv` で作った新規環境には `setuptools` が入らないので明示的に導入。）
- **COLMAP** — どのビルドでも可。CUDA無しの `colmap.exe` なら完全ローカルを保てます。

## VkSplat のビルド

```bash
git clone https://github.com/harry7557558/vksplat
cd vksplat/vksplat
# 環境変数 VULKAN_SDK を設定した状態で:
python -m pip install -e . --no-build-isolation --no-deps -v
```

`--no-deps` で `torchmetrics`/`torch` をスキップ（評価時のみ必要で、学習には不要）。
GLM は自動 clone され、SPIR-V シェーダはコンパイル済みで同梱されています。

### 実際にハマったポイント

1. **パッケージディレクトリ内から import する。** パス上に `vksplat` という名前のフォルダが
   あると、ビルドした `.pyd` が隠されます。`vksplat/vksplat/` の中から実行するか、
   `--vksplat-dir` を指定してください。
2. **`mask_dir` は `None` ではなく `""`** — `None` は C++ のキャストで失敗します（対応済み）。
3. **`sparse_dir` / `image_dir` は末尾区切り付きの絶対パス** — C++ 側が単純な文字列連結
   （`sparse_dir + "cameras.bin"`）を行うためです（対応済み）。

## 使い方

```bash
# 1. 写真 -> COLMAP のカメラ姿勢（すでに sparse/0 があればスキップ）
python scripts/photos_to_colmap.py path/to/photos --colmap path/to/colmap.exe

# 2. 高速化のための縮小（1/4解像度で約13倍速。intrinsics は自動補正）
python scripts/downscale.py path/to/workspace/images 4

# 3. 学習（VkSplat パッケージディレクトリ内で実行するか --vksplat-dir を指定）
python scripts/train_vksplat.py path/to/workspace --image-dir images_4 --steps 15000
```

出力: `path/to/workspace/vksplat_out/splat.ply`（標準3DGS PLY形式）+ 検証用レンダリング。

## 速度

per-pixel のラスタライズが処理時間の約88%を占めるため、**入力解像度が支配的なレバー**です。
Arc 140V（小規模シーン、学習画像13枚）での実測:

| 画像解像度 | スループット | 1000ステップ |
|---|---|---|
| フル（3072×2304） | 約9 steps/s | 108秒 |
| 1/4（`images_4`） | 約120 steps/s | 8.3秒 |

`images_4` での15000ステップのフル学習は約5.7分（約28万 splats）でした。
品質と速度の中間が欲しければ `--image-dir images_2`、画像が VRAM に収まるなら
`--cache gpu`（デフォルト）を使います。

## 結果を表示する

### A. 学習中にライブ表示（ブラウザ）

`train_vksplat.py` に `--viewer` を付けて実行し、ブラウザで `http://localhost:7007` を開きます。
Arc がフレームを描画してブラウザにストリーミングし、マウスで視点を操作できます。

```bash
python scripts/train_vksplat.py path/to/workspace --image-dir images_4 --steps 15000 --viewer
```

> ⚠️ このビューアは**学習プロセスが動いている間だけ**有効です（学習が終わるとプロセスと
> 一緒に閉じます）。保存済みのモデルを後からいつでも見たい場合は下の B を使います。

### B. 保存された `splat.ply` を後から表示

学習が終わると `path/to/workspace/vksplat_out/splat.ply` が生成されます。これは
**標準の 3DGS PLY 形式**（`x, y, z, f_dc_*, f_rest_*, opacity, scale_*, rot_*`）なので、
ほとんどのガウシアンスプラットビューアでそのまま開けます。

**ローカルアプリ（完全オフライン）— [Brush](https://github.com/ArthurBrussee/brush)（Apache-2.0, WebGPU）:**

```bash
# Windows
brush_app.exe path/to/workspace/vksplat_out/splat.ply
# macOS / Linux
brush_app path/to/workspace/vksplat_out/splat.ply
```

**ブラウザ（ドラッグ＆ドロップ、描画はローカルの WebGPU で実行）:**

- [Brush Web デモ](https://arthurbrussee.github.io/brush-demo) に `splat.ply` をドロップ
- または [SuperSplat](https://supersplat.playcanvas.com)（PlayCanvas, ブラウザ内で完結）

> どのビューアもファイルはアップロードされず、描画は各自の GPU 上で行われます。

## クレジット & ライセンス

- [VkSplat](https://github.com/harry7557558/vksplat) — Apache-2.0
- [COLMAP](https://github.com/colmap/colmap) — BSD
- [Brush](https://github.com/ArthurBrussee/brush) — Apache-2.0

このリポジトリのスクリプトは Apache-2.0 で公開しています（`LICENSE` 参照）。
