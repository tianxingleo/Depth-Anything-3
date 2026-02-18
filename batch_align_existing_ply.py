#!/home/ltx/my_envs/gs_linux_backup/bin/python
"""
批量扶正已有 PLY 文件 (3DGS/SuGaR 深度对齐版)
专门针对书桌、桌面物体环绕扫描优化。
通过 Splat 法向共识和局部密度分层算法，解决室内场景“正反不分”的问题。
"""

import argparse
import sys
import time
from pathlib import Path
import numpy as np

def install_package(package):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from plyfile import PlyData, PlyElement
except ImportError:
    install_package("plyfile")
    from plyfile import PlyData, PlyElement

try:
    import open3d as o3d
except ImportError:
    install_package("open3d")
    import open3d as o3d

try:
    from scipy.spatial.transform import Rotation
except ImportError:
    install_package("scipy")
    from scipy.spatial.transform import Rotation

def get_rotation_to_z(normal):
    """计算旋转矩阵将 normal 旋转到 Z+ [0,0,1]"""
    n = normal / np.linalg.norm(normal)
    # 先强制法线朝向正半球
    if n[2] < 0: n = -n
    target = np.array([0, 0, 1])
    axis = np.cross(n, target)
    if np.linalg.norm(axis) < 1e-8:
        return np.eye(3)
    angle = np.arccos(np.clip(np.dot(n, target), -1.0, 1.0))
    return o3d.geometry.get_rotation_matrix_from_axis_angle(axis/np.linalg.norm(axis) * angle)

def align_single_ply_robust(ply_path, output_path, distance_threshold=0.03, num_iterations=10000):
    t0 = time.time()
    print(f"  📂 {ply_path.name}")

    try:
        plydata = PlyData.read(str(ply_path))
    except Exception as e:
        print(f"     ❌ 读取失败: {e}")
        return False

    vertex = plydata['vertex']
    points = np.stack([vertex['x'], vertex['y'], vertex['z']], axis=-1)
    
    # 提取法线 (如果有)
    has_normals = 'nx' in vertex.data.dtype.names
    normals = np.stack([vertex['nx'], vertex['ny'], vertex['nz']], axis=-1) if has_normals else None
    
    if len(points) < 500: return False
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # 1. RANSAC 寻找主平面
    cloud = pcd
    candidates = []
    print(f"     🔍 执行智能场特征分析 (多因子对齐模型)...")
    
    for i in range(5):
        if len(cloud.points) < 100: break
        plane_model, inliers = cloud.segment_plane(distance_threshold, 3, num_iterations)
        [a, b, c, d] = plane_model
        
        # --- 决策逻辑 A: 旋转测试 ---
        R_test = get_rotation_to_z(np.array([a, b, c]))
        sample_idx = np.random.choice(len(points), min(len(points), 20000), replace=False)
        pts_test = points[sample_idx] @ R_test.T
        
        # --- 决策逻辑 B: 局部密度分层 (解决书桌问题) ---
        # 考察平面上下 0.3m 范围，避开远端地面的干扰
        z_plane_rotated = (points[inliers[0]] @ R_test.T)[2] if len(inliers)>0 else 0
        local_above = np.sum((pts_test[:, 2] > z_plane_rotated) & (pts_test[:, 2] < z_plane_rotated + 0.3))
        local_below = np.sum((pts_test[:, 2] < z_plane_rotated) & (pts_test[:, 2] > z_plane_rotated - 0.3))
        
        # --- 决策逻辑 C: 法向共识 (GS 数据最强判定) ---
        normal_consensus = 1.0
        if has_normals:
            # 统计平面内点的平均法向与 [0,0,1] 的一致性
            plane_normals = (normals[inliers] @ R_test.T)
            avg_n = np.mean(plane_normals, axis=0)
            normal_consensus = avg_n[2] # 正值代表朝向正确(相机侧)
            
        # 综合评分：纵横比 * 法向一致性 * 点数
        p_min, p_max = np.min(pts_test, axis=0), np.max(pts_test, axis=0)
        aspect = (p_max[0]-p_min[0] + p_max[1]-p_min[1]) / (p_max[2]-p_min[2] + 1e-6)
        score = aspect * np.log10(len(inliers))
        
        # 判定是否倒置：优先看全局中位数，但如果局部密度显示相反，则修正
        z_median = np.median(pts_test[:, 2])
        is_upside_down = z_median < z_plane_rotated
        
        # 如果法向共识极强，以法向为准
        if has_normals and abs(normal_consensus) > 0.2:
            is_upside_down = normal_consensus < 0
        
        candidates.append({
            'model': plane_model, 'score': score, 
            'is_ceiling': is_upside_down, 'consensus': normal_consensus,
            'local_ratio': local_above / (local_below + 1.0)
        })
        cloud = cloud.select_by_index(inliers, invert=True)

    if not candidates: return False

    # 2. 选取
    best = max(candidates, key=lambda x: x['score'])
    print(f"     📊 选定面分析:")
    print(f"        中心高度对比: {'⬇️ 偏下 (可能转反)' if best['is_ceiling'] else '⬆️ 正常'}")
    if has_normals:
        print(f"        法向共识度: {best['consensus']:.3f} ({'✅ 匹配' if best['consensus'] > 0 else '❌ 冲突'})")
    print(f"        空间离散比率: {best['local_ratio']:.2f} ({'💎 顶部有集中重物' if best['local_ratio'] > 1.2 else '🈳 顶部开阔'})")

    # 3. 旋转
    R = get_rotation_to_z(best['model'][:3])
    
    # 执行翻转逻辑
    # 如果重心判定和局部密度一致认为倒了，或者法向判定强力认为倒置
    should_flip = best['is_ceiling']
    if best['local_ratio'] > 2.0: should_flip = False # 即使重心偏下，但如果台面上全是重物，认定为书桌
    
    if should_flip:
        print("     ⚠️ 判定为倒置状态，执行 180° 正位翻转补正...")
        R = o3d.geometry.get_rotation_matrix_from_axis_angle(np.array([1, 0, 0]) * np.pi) @ R

    # 4. 应用
    points_rot = points @ R.T
    z_floor = np.percentile(points_rot[:, 2], 2)
    points_rot[:, 2] -= z_floor

    vertex['x'], vertex['y'], vertex['z'] = points_rot[:, 0], points_rot[:, 1], points_rot[:, 2]
    
    if has_normals:
        n_rot = normals @ R.T
        vertex['nx'], vertex['ny'], vertex['nz'] = n_rot[:, 0], n_rot[:, 1], n_rot[:, 2]
    
    if 'rot_0' in vertex.data.dtype.names:
        q = np.stack([vertex['rot_1'], vertex['rot_2'], vertex['rot_3'], vertex['rot_0']], axis=-1)
        r_new = Rotation.from_matrix(R) * Rotation.from_quat(q)
        q_new = r_new.as_quat()
        vertex['rot_0'], vertex['rot_1'], vertex['rot_2'], vertex['rot_3'] = q_new[:, 3], q_new[:, 0], q_new[:, 1], q_new[:, 2]

    # 5. 保存
    PlyData([vertex], text=False, byte_order='<').write(str(output_path))
    print(f"     ✅ 处理完成！已保存至 {output_path.name} (耗时 {time.time()-t0:.1f}s)")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", required=True)
    parser.add_argument("--threshold", type=float, default=0.03)
    args = parser.parse_args()
    p = Path(args.input_file)
    if not p.exists(): return
    out = p.parent / f"{p.stem}_aligned{p.suffix}"
    align_single_ply_robust(p, out, args.threshold)

if __name__ == "__main__":
    main()
