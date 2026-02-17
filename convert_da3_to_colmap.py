
import os
import numpy as np
from PIL import Image
import struct

def rotmat_to_quat(R):
    tr = np.trace(R)
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2
        qw = 0.25 * S
        qx = (R[2, 1] - R[1, 2]) / S
        qy = (R[0, 2] - R[2, 0]) / S
        qz = (R[1, 0] - R[0, 1]) / S
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        qw = (R[2, 1] - R[1, 2]) / S
        qx = 0.25 * S
        qy = (R[0, 1] + R[1, 0]) / S
        qz = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        qw = (R[0, 2] - R[2, 0]) / S
        qx = (R[0, 1] + R[1, 0]) / S
        qy = 0.25 * S
        qz = (R[1, 2] + R[2, 1]) / S
    else:
        S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        qw = (R[1, 0] - R[0, 1]) / S
        qx = (R[0, 2] + R[2, 0]) / S
        qy = (R[1, 2] + R[2, 1]) / S
        qz = 0.25 * S
    return np.array([qw, qx, qy, qz])

def read_binary_ply(ply_path):
    with open(ply_path, 'rb') as f:
        header = ""
        while True:
            line = f.readline().decode('ascii')
            header += line
            if line.startswith("end_header"):
                break
        
        # Parse header to find vertex count
        num_vertices = 0
        for line in header.split('\n'):
            if line.startswith("element vertex"):
                num_vertices = int(line.split()[-1])
        
        # Read the binary data
        # Combined format: float x, y, z, uchar r, g, b
        data = f.read()
        
    # struct format: 3 floats (4 bytes each) and 3 uchars (1 byte each)
    # Total 15 bytes per vertex
    vertices = []
    colors = []
    
    # Check if it's 15 bytes or more (might have other properties)
    struct_fmt = "fffBBB"
    struct_size = struct.calcsize(struct_fmt)
    
    # Some DA3 versions might have 15 bytes per point or more.
    # Let's adjust based on total read size vs num_vertices.
    actual_struct_size = len(data) // num_vertices
    
    for i in range(num_vertices):
        offset = i * actual_struct_size
        v = struct.unpack_from(struct_fmt, data, offset)
        vertices.append(v[:3])
        colors.append(v[3:])
    
    return np.array(vertices), np.array(colors)

def convert_to_colmap(base_dir, output_dir):
    intrinsic_file = os.path.join(base_dir, "intrinsic.txt")
    pose_file = os.path.join(base_dir, "camera_poses.txt")
    ply_file = os.path.join(base_dir, "pcd/combined_pcd.ply")
    img_dir = os.path.join(base_dir, "extracted")
    
    sparse_dir = os.path.join(output_dir, "sparse/0")
    os.makedirs(sparse_dir, exist_ok=True)
    
    # 1. Load data
    print("Loading camera data...")
    all_intrinsics = np.loadtxt(intrinsic_file) # N x 4 (fx, fy, cx, cy)
    all_poses_c2w = np.loadtxt(pose_file).reshape(-1, 4, 4)
    img_names = sorted(os.listdir(img_dir))
    
    num_frames = len(all_poses_c2w)
    
    # Check image size
    first_img_path = os.path.join(img_dir, img_names[0])
    with Image.open(first_img_path) as img:
        orig_w, orig_h = img.size
    
    print(f"Original image size: {orig_w}x{orig_h}")
    
    # 2. Write cameras.txt
    # We'll treat each frame as having the same camera for simplicity in 3DGS, 
    # but strictly speaking DA3 predicts per-frame intrinsics.
    # To keep 3DGS training stable, we'll write separate camera entries if they differ significantly,
    # or just one for each frame.
    with open(os.path.join(sparse_dir, "cameras.txt"), "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        
        # Scaling factor:
        # Assuming intrinsics are for some internal resolution, we scale to match orig_w/orig_h
        # CX should be near W/2
        proc_w = all_intrinsics[0][2] * 2
        proc_h = all_intrinsics[0][3] * 2
        
        scale_x = orig_w / proc_w
        scale_y = orig_h / proc_h
        
        for i in range(num_frames):
            intri = all_intrinsics[i]
            fx, fy, cx, cy = intri[0] * scale_x, intri[1] * scale_y, intri[2] * scale_x, intri[3] * scale_y
            # CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
            # MODEL 1 is PINHOLE: fx, fy, cx, cy
            f.write(f"{i+1} PINHOLE {orig_w} {orig_h} {fx} {fy} {cx} {cy}\n")

    # 3. Write images.txt
    print("Writing images.txt...")
    with open(os.path.join(sparse_dir, "images.txt"), "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        
        for i in range(num_frames):
            c2w = all_poses_c2w[i]
            w2c = np.linalg.inv(c2w)
            
            R = w2c[:3, :3]
            t = w2c[:3, 3]
            q = rotmat_to_quat(R)
            
            # IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
            f.write(f"{i+1} {q[0]} {q[1]} {q[2]} {q[3]} {t[0]} {t[1]} {t[2]} {i+1} {img_names[i]}\n")
            f.write("\n") # No points2D for now

    # 4. Write points3D.txt
    print("Loading point cloud...")
    points, colors = read_binary_ply(ply_file)
    print(f"Loaded {len(points)} points. Writing points3D.txt...")
    
    with open(os.path.join(sparse_dir, "points3D.txt"), "w") as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        
        for i in range(len(points)):
            p = points[i]
            c = colors[i]
            # ID, X, Y, Z, R, G, B, ERROR, TRACK...
            # We use dummy error 0 and no track
            f.write(f"{i+1} {p[0]} {p[1]} {p[2]} {c[0]} {c[1]} {c[2]} 0\n")

    # 5. Create images directory (symlink)
    colmap_img_dir = os.path.join(output_dir, "images")
    if os.path.exists(colmap_img_dir):
        if os.path.islink(colmap_img_dir):
            os.unlink(colmap_img_dir)
        else:
            shutil.rmtree(colmap_img_dir)
    
    # Try to symlink, if fails (e.g. windows), copy
    try:
        os.symlink(img_dir, colmap_img_dir)
        print(f"Created symlink for images: {colmap_img_dir} -> {img_dir}")
    except OSError:
        print("Symlink failed, copying images...")
        shutil.copytree(img_dir, colmap_img_dir)

    print(f"\nConversion complete! COLMAP data saved in: {output_dir}")
    print("You can now use this directory for 3DGS training.")

if __name__ == "__main__":
    base = "/home/ltx/projects/Depth-Anything-3/output/sugar_streaming"
    output = "/home/ltx/projects/Depth-Anything-3/output/sugar_streaming/colmap_data"
    convert_to_colmap(base, output)
