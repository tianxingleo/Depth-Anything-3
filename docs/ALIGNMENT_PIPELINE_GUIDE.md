# 🌐 点云自动扶正 Pipeline 使用指南

> **DA3 → 3DGS + 自动对齐** — 让你的 3D 高斯泼溅模型自动"站正"

## 📖 概述

在使用 Depth Anything 3 (DA3) 生成的数据训练 3DGS 时，输出的点云模型通常是"歪的"——地面不在水平面上，模型整体可能倾斜或翻转。这是因为 DA3 的相机位姿是相对坐标系，没有重力方向的先验信息。

本工具集提供了 **三种方案** 来自动扶正点云，让地面对齐到 X-Y 平面（Z 轴朝上），方便在 SuperSplat、SIBR 等查看器中正确浏览。

---

## 📁 文件清单

### ⭐ 推荐使用 (Python 脚本, 高性能)

| 文件 | 说明 |
|------|------|
| `run_da3_to_3dgs_aligned.py` | **融合 Pipeline** — 训练+双重对齐，基于 nerfstudio splatfacto |
| `batch_align_existing_ply.py` | **批量扶正** — 对已有 PLY 文件进行 Open3D 扶正 |
| `auto_align_ply.py` | **独立工具** — 对单个 PLY 文件扶正 |

### Shell 脚本 (旧版, 基于 SuGaR/vanilla 3DGS)

| 文件 | 说明 |
|------|------|
| `da3_to_3dgs_aligned.sh` | 融合方案 shell 版 |
| `da3_to_3dgs_aligned_colmap.sh` | 方案 A (仅 COLMAP) |
| `da3_to_3dgs_aligned_open3d.sh` | 方案 B (仅 Open3D) |

---

## 🚀 快速开始

### 1. 训练新模型 + 自动扶正 (推荐)

```bash
# 默认参数，双重对齐
python run_da3_to_3dgs_aligned.py

# 仅 COLMAP 对齐
python run_da3_to_3dgs_aligned.py --skip_open3d

# 仅 Open3D 扶正
python run_da3_to_3dgs_aligned.py --skip_colmap

# 完全自定义
python run_da3_to_3dgs_aligned.py \
    --da3_output output/sugar_streaming \
    --iterations 30000 \
    --colmap_error 0.05 \
    --open3d_threshold 0.03 \
    --translate_to_ground
```

### 2. 扶正已有 PLY 文件

```bash
# 批量扶正 da3_dn_splatter_output/export*/splat.ply
python batch_align_existing_ply.py

# 扶正单个文件
python batch_align_existing_ply.py --input_file /path/to/some.ply

# 自定义参数
python batch_align_existing_ply.py --threshold 0.05 --translate_to_ground
```

### 3. 对任意 PLY 扶正 (独立工具)

```bash
python auto_align_ply.py input.ply output.ply
python auto_align_ply.py model.ply --inplace
```

---

## 📋 详细用法

### ⭐ `run_da3_to_3dgs_aligned.py` — 融合 Pipeline

基于 `run_da3_to_3dgs_direct.py` 的模式，使用 nerfstudio `splatfacto` 训练引擎。

**完整参数表:**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--da3_output` | `output/sugar_streaming` | DA3 输出目录 |
| `--iterations` | `15000` | 训练迭代次数 |
| `--colmap_error` | `0.02` | COLMAP 对齐最大误差 (米) |
| `--open3d_threshold` | `0.02` | Open3D RANSAC 距离阈值 (米) |
| `--translate_to_ground` | 关闭 | 将地面平移到 Z=0 |
| `--skip_colmap` | 关闭 | 跳过 COLMAP 对齐 (仅用方案B) |
| `--skip_open3d` | 关闭 | 跳过 Open3D 扶正 (仅用方案A) |

**流程:**
```
Step 1: 同步图片
Step 2: DA3 → COLMAP 转换
Step 3: 🅰️ COLMAP model_aligner 对齐 (可跳过)
Step 4: splatfacto 训练
Step 5: 导出 PLY
Step 6: 🅱️ Open3D RANSAC 扶正 (可跳过)
```

**输出:**
```
output/sugar_streaming/da3_3dgs_aligned_pipeline/
├── data/               # 训练数据
├── outputs/            # 训练输出
└── export/
    ├── splat.ply           # 原始
    └── splat_aligned.ply   # 扶正后 ← 推荐使用
```

---

### ⭐ `batch_align_existing_ply.py` — 批量扶正已有 PLY

专门针对 `da3_dn_splatter_output/export*` 下的 `splat.ply` 文件，一键批量扶正。

**完整参数表:**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input_dir` | `da3_dn_splatter_output` | 包含 `export*/splat.ply` 的根目录 |
| `--input_file` | 无 | 单个 PLY 路径 (优先于 --input_dir) |
| `--output_suffix` | `_aligned` | 输出文件后缀 |
| `--threshold` | `0.02` | RANSAC 距离阈值 (米) |
| `--num_iterations` | `1000` | RANSAC 迭代次数 |
| `--translate_to_ground` | 关闭 | 平移地面到 Z=0 |
| `--inplace` | 关闭 | 原地覆盖 (谨慎!) |
| `--ply_name` | `splat.ply` | 要查找的 PLY 文件名 |

**示例:**
```bash
# 默认: 扶正 da3_dn_splatter_output 下所有 export*/splat.ply
python batch_align_existing_ply.py

# 自定义目录
python batch_align_existing_ply.py --input_dir /path/to/some/output

# 单个文件
python batch_align_existing_ply.py --input_file model.ply

# 修改参数
python batch_align_existing_ply.py --threshold 0.05 --translate_to_ground

# 自定义PLY名称
python batch_align_existing_ply.py --ply_name point_cloud.ply
```

**输出示例:**
```
da3_dn_splatter_output/
├── export/
│   ├── splat.ply
│   └── splat_aligned.ply          ← 新增
├── export_step5000/
│   ├── splat.ply
│   └── splat_aligned.ply          ← 新增
├── export_step10000/
│   ├── splat.ply
│   └── splat_aligned.ply          ← 新增
...
```

---

### `auto_align_ply.py` — 独立扶正工具

对任意单个 PLY 文件进行扶正，不绑定任何 Pipeline。

```bash
python auto_align_ply.py input.ply output.ply
python auto_align_ply.py model.ply --inplace
python auto_align_ply.py model.ply --distance_threshold 0.05 --translate_to_ground
```

---

## 🔬 技术原理

### 方案 A: COLMAP model_aligner (训练前对齐)

```
DA3数据 → COLMAP格式 → 🅰️ model_aligner → 训练 → PLY
                          ↑ 旋转相机+点云
```

- **算法**: COLMAP 自带的模型对齐工具，利用 **曼哈顿世界假设**
- **假设**: 场景中存在大量垂直和水平表面（墙壁、地面、天花板）
- **动作**: 自动检测主平面，将其旋转到 X-Y 平面
- **作用范围**: 旋转 COLMAP 稀疏模型（相机位姿 + 3D 点），**训练前生效**

### 方案 B: Open3D RANSAC (训练后扶正)

```
DA3数据 → COLMAP格式 → 训练 → PLY → 🅱️ RANSAC扶正 → 扶正PLY
                                      ↑ 旋转输出点云
```

- **算法**: RANSAC (Random Sample Consensus) 平面分割
- **原理**:
  1. 随机采样 3 个点拟合平面
  2. 统计距离平面 < 阈值的内点数
  3. 重复 1000 次，保留内点最多的平面（即地面）
  4. 计算地面法向量到 Z 轴的旋转矩阵
  5. 应用旋转
- **作用范围**: 仅旋转输出 PLY 文件，**训练后生效**

### 融合方案: 双重对齐

```
DA3数据 → COLMAP → 🅰️ COLMAP对齐 → 训练 → PLY → 🅱️ Open3D扶正 → 扶正PLY
                    (粗对齐)                       (精细校正)
```

- **第一层**: COLMAP 在训练前对齐，训练受益于正确朝向
- **第二层**: Open3D 训练后精细校正
- **安全网**: 任一步骤失败不影响另一步骤
- **智能跳过**: 如果已正确朝向，Open3D 自动跳过旋转

---

## 📊 方案对比

| 特性 | 方案 A (COLMAP) | 方案 B (Open3D) | 融合方案 ⭐ |
|------|----------------|-----------------|------------|
| **依赖** | COLMAP | Open3D | 两者 |
| **对齐时机** | 训练前 | 训练后 | 训练前+后 |
| **对齐对象** | 相机+稀疏点云 | 仅输出PLY | 全部 |
| **算法** | 曼哈顿假设 | RANSAC | 双重 |
| **可控性** | 低 | 高 | 最高 |
| **适用场景** | 室内/建筑 | 任意 | 全场景 |
| **额外耗时** | ~1 秒 | ~3-5 秒 | ~5 秒 |

---

## ❓ FAQ

### Q: 哪个 Pipeline 最快？

**A**: Python 版 (`run_da3_to_3dgs_aligned.py`) 比 Shell 版快，因为:
- 不需要 `conda activate` 开销
- 不需要 `cp -r` 大批量复制
- 直接用 subprocess 调用命令

### Q: 模型还是歪的？

**A**: 尝试增大 `--open3d_threshold`（如 `0.05` 或 `0.1`），或确认场景中有可识别的地面。

### Q: 已经有训练好的 PLY，怎么扶正？

**A**: 用 `batch_align_existing_ply.py`:
```bash
python batch_align_existing_ply.py
# 或指定单个文件
python batch_align_existing_ply.py --input_file /path/to/model.ply
```

### Q: `--translate_to_ground` 有什么用？

**A**: 将地面平移到 Z=0 平面。适用于需要在同一地平面上放置多个模型的场景。

### Q: Open3D 安装失败？

**A**: 脚本会自动尝试安装。如果失败：
```bash
pip install open3d
# 或
conda install -c open3d-admin open3d
# 或跳过 Open3D: 
python run_da3_to_3dgs_aligned.py --skip_open3d
```

### Q: 双重对齐会不会"过度旋转"？

**A**: 不会。如果 COLMAP 已完美对齐，Open3D 会检测到法向量接近 Z 轴，自动跳过旋转。

---

## 🏗️ 架构图

```
┌──────────────────────────────────────────────────────────────┐
│           run_da3_to_3dgs_aligned.py (融合方案)               │
│                                                               │
│  Step 1      Step 2        Step 3       Step 4      Step 5    │
│  同步图片 → COLMAP转换 → 🅰️COLMAP对齐 → splatfacto → 导出PLY │
│                             (可跳过)     训练                  │
│                                                       │       │
│                                                       ▼       │
│                                               Step 6          │
│                                            🅱️Open3D扶正      │
│                                              (可跳过)          │
│                                                  │            │
│                                                  ▼            │
│                                           splat.ply           │
│                                           splat_aligned.ply   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│          batch_align_existing_ply.py (批量扶正)               │
│                                                               │
│  da3_dn_splatter_output/                                      │
│  ├── export/splat.ply         → splat_aligned.ply             │
│  ├── export_step5000/splat.ply  → splat_aligned.ply           │
│  ├── export_step10000/splat.ply → splat_aligned.ply           │
│  ...                                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 📝 更新日志

- **2026-02-18 v2**: 
  - 🆕 `run_da3_to_3dgs_aligned.py` — Python 高性能融合 Pipeline
  - 🆕 `batch_align_existing_ply.py` — 批量扶正已有 PLY
  - 性能优化: 基于 `run_da3_to_3dgs_direct.py` 模式重写

- **2026-02-18 v1**: 
  - Shell 脚本版本（方案A/B/融合）
  - `auto_align_ply.py` 独立扶正工具
