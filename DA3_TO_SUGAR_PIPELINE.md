# Depth Anything 3 -> SuGaR Pipeline

将Depth Anything 3的输出转换为SuGaR可以使用的COLMAP格式，用于3D重建。

## 目录

- [简介](#简介)
- [系统要求](#系统要求)
- [安装](#安装)
- [使用方法](#使用方法)
- [输出文件](#输出文件)
- [故障排除](#故障排除)

## 简介

此pipeline包含以下步骤：

1. **转换DA3输出为COLMAP格式（文本）** - 将Depth Anything 3的输出文件（camera_poses.txt、intrinsic.txt、ply点云等）转换为COLMAP文本格式
2. **转换为COLMAP二进制格式** - 将COLMAP文本格式转换为SuGaR需要的二进制格式（cameras.bin、images.bin、points3D.bin）
3. **整理SuGaR数据目录** - 将COLMAP数据和图像复制到SuGaR的数据目录
4. **SuGaR训练** - 使用SuGaR进行3D重建训练

## 系统要求

- Python 3.8+
- Conda环境
- CUDA（用于GPU加速）
- 已安装的软件：
  - Depth Anything 3
  - SuGaR
  - numpy, PIL, struct（Python库）

## 安装

1. 确保已安装Depth Anything 3和SuGaR
2. 激活SuGaR的Conda环境：

```bash
conda activate gs_linux_backup
```

3. 确保脚本有执行权限：

```bash
chmod +x /home/ltx/projects/Depth-Anything-3/da3_to_sugar_pipeline.sh
chmod +x /home/ltx/projects/Depth-Anything-3/colmap_text_to_binary.py
chmod +x /home/ltx/projects/Depth-Anything-3/convert_da3_to_colmap.py
```

## 使用方法

### 快速开始

使用默认参数运行完整pipeline：

```bash
./da3_to_sugar_pipeline.sh <DA3输出目录> <场景名称>
```

### 完整参数

```bash
./da3_to_sugar_pipeline.sh <DA3输出目录> <场景名称> [正则化方法] [精炼时间] [高精度] [快速模式]
```

#### 参数说明

- **<DA3输出目录>**: Depth Anything 3的输出目录，包含以下文件：
  - `camera_poses.txt` - 相机位姿（c2w格式）
  - `intrinsic.txt` - 相机内参（每帧fx, fy, cx, cy）
  - `pcd/combined_pcd.ply` - 点云文件
  - `extracted/` - 提取的图像目录

- **<场景名称>**: SuGaR场景名称，用于输出目录命名

- **[正则化方法]**: 正则化方法（可选，默认：dn_consistency）
  - `dn_consistency` - 深度一致性正则化（推荐，最佳网格质量）
  - `density` - 密度正则化
  - `sdf` - SDF正则化

- **[精炼时间]**: 精炼时间（可选，默认：short）
  - `short` - 短精炼（2k迭代，快速）
  - `medium` - 中等精炼（7k迭代）
  - `long` - 长精炼（15k迭代，高质量）

- **[高精度]**: 是否生成高精度网格（可选，默认：true）
  - `true` - 高精度（1M顶点）
  - `false` - 低精度（200k顶点）

- **[快速模式]**: 快速模式（可选，默认：false）
  - `true` - 跳过mesh生成和refinement，节省50%时间
  - `false` - 完整流程

#### 使用示例

**1. 快速预览（推荐用于测试）**

```bash
./da3_to_sugar_pipeline.sh \
  /home/ltx/projects/Depth-Anything-3/output/sugar_streaming \
  my_scene \
  dn_consistency \
  short \
  false \
  true
```

**2. 标准质量（推荐）**

```bash
./da3_to_sugar_pipeline.sh \
  /home/ltx/projects/Depth-Anything-3/output/sugar_streaming \
  my_scene \
  dn_consistency \
  short \
  true \
  false
```

**3. 高质量重建**

```bash
./da3_to_sugar_pipeline.sh \
  /home/ltx/projects/Depth-Anything-3/output/sugar_streaming \
  my_scene \
  dn_consistency \
  long \
  true \
  false
```

### 单独运行各个步骤

如果需要单独运行某个步骤，可以使用以下脚本：

#### 步骤1: 转换为COLMAP文本格式

```bash
python3 /home/ltx/projects/Depth-Anything-3/convert_da3_to_colmap.py \
  --base_dir /path/to/da3/output \
  --output_dir /path/to/colmap/output
```

#### 步骤2: 转换为COLMAP二进制格式

```bash
python3 /home/ltx/projects/Depth-Anything-3/colmap_text_to_binary.py \
  /path/to/colmap/output/sparse/0
```

## 输出文件

### SuGaR数据目录结构

```
/home/ltx/projects/SuGaR/data/<场景名称>/
├── images/                    # 输入图像
│   ├── 0001.jpg
│   ├── 0002.jpg
│   └── ...
└── sparse/0/                  # COLMAP二进制数据
    ├── cameras.bin            # 相机内参
    ├── images.bin            # 图像位姿
    └── points3D.bin          # 3D点云
```

### SuGaR输出目录结构

```
/home/ltx/projects/SuGaR/output/<场景名称>/
├── coarse_sugar/              # 粗糙SuGaR模型
├── refined_ply/              # 精炼的3DGS文件
│   └── <场景名称>_*.ply     # 可在3DGS viewer中查看
└── refined_mesh/             # 精炼的网格文件
    └── <场景名称>_*.obj     # 可在Blender中编辑
```

## 故障排除

### 错误：找不到输入文件

**问题**: `❌ 错误: 找不到 camera_poses.txt`

**解决**:
- 确保DA3输出目录正确
- 检查文件是否存在：`ls /path/to/da3/output/`

### 错误：位姿数量与图像数量不匹配

**问题**: `⚠️ 警告: 位姿数量 (100) 与图像数量 (99) 不匹配`

**解决**:
- 这是警告，不是错误
- pipeline会继续运行
- 如有质量问题，检查DA3输出是否完整

### 错误：SuGaR训练失败

**问题**: `❌ 错误: SuGaR训练失败`

**解决**:
1. 检查CUDA是否正常：`nvidia-smi`
2. 检查Conda环境是否正确激活
3. 检查磁盘空间是否充足
4. 查看详细错误日志

### 错误：图像数量较少

**问题**: `⚠️ 警告: 图像数量较少 (20 < 30)`

**解决**:
- 使用更长的输入视频
- 降低DA3抽帧率
- 确保视频中场景有多角度拍摄

## 时间参考

在RTX 5070上的大致时间：

| 模式 | 图像数 | 时间 |
|------|--------|------|
| 快速模式 | 50帧 | 15-30分钟 |
| 标准模式 | 50帧 | 30-60分钟 |
| 高质量 | 100帧 | 60-120分钟 |

## 下一步操作

1. **查看3DGS模型**

   使用SuGaR查看器：
   ```bash
   cd /home/ltx/projects/SuGaR
   python run_viewer.py -p /home/ltx/projects/SuGaR/output/refined_ply/<场景名称>/*.ply
   ```

2. **在Blender中编辑网格**

   - 安装Blender add-on: https://github.com/Anttwo/sugar_frosting_blender_addon
   - 导入OBJ文件到Blender

3. **在线查看**

   - SuperSplat: https://playcanvas.com/supersplat/editor

4. **渲染Blender场景**

   ```bash
   cd /home/ltx/projects/SuGaR
   python render_blender_scene.py -p <rendering_package_path>
   ```

## 技术细节

### COLMAP格式说明

- **cameras.txt/bin**: 相机内参
  - CAMERA_ID: 相机ID
  - MODEL: 相机模型（PINHOLE）
  - WIDTH, HEIGHT: 图像尺寸
  - PARAMS: fx, fy, cx, cy

- **images.txt/bin**: 图像位姿
  - IMAGE_ID: 图像ID
  - QW, QX, QY, QZ: 旋转四元数
  - TX, TY, TZ: 平移向量
  - CAMERA_ID: 相机ID
  - NAME: 图像文件名

- **points3D.txt/bin**: 3D点云
  - POINT3D_ID: 点ID
  - X, Y, Z: 3D坐标
  - R, G, B: 颜色
  - ERROR: 重投影误差
  - TRACK: 观测跟踪（图像ID, 点2D索引）

### 文件格式转换流程

1. **Depth Anything 3输出**
   ```
   camera_poses.txt (c2w 4x4矩阵)
   intrinsic.txt (fx, fy, cx, cy)
   pcd/combined_pcd.ply (二进制点云)
   extracted/*.jpg (图像)
   ```

2. **COLMAP文本格式**
   ```
   sparse/0/cameras.txt
   sparse/0/images.txt
   sparse/0/points3D.txt
   images/ (符号链接)
   ```

3. **COLMAP二进制格式**
   ```
   sparse/0/cameras.bin
   sparse/0/images.bin
   sparse/0/points3D.bin
   ```

4. **SuGaR使用**
   ```
   读取二进制COLMAP数据
   进行3D重建训练
   ```

## 相关资源

- [Depth Anything 3](https://github.com/DepthAnything/Depth-Anything-V3)
- [SuGaR](https://github.com/Anttwo/SuGaR)
- [COLMAP](https://colmap.github.io/)
- [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)

## 更新日志

### v1.0 (2026-02-18)

- 初始版本
- 支持DA3到COLMAP文本格式转换
- 支持COLMAP文本到二进制格式转换
- 支持完整SuGaR训练pipeline
- 支持快速模式和完整模式
