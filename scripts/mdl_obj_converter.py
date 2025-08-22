#!/usr/bin/env python3

import struct
import sys
from pathlib import Path


def int_to_bytes(amount):
    return struct.pack('<I', amount)


def int_to_bytes2(amount):
    return struct.pack('<H', amount)


def float_to_hex(float_val):
    packed = struct.pack('<f', float_val)
    return packed


def hex_float(hex_bytes):
    return struct.unpack('<f', hex_bytes)[0]


def convert_to_mdl(obj_file_path):
    with open(obj_file_path, 'r') as f:
        lines = f.read().split('\n')
    
    vertices = []
    uvs = []
    faces = []
    normals = []
    tags = []
    
    lowest_point = [0.0, 0.0, 0.0]
    highest_point = [0.0, 0.0, 0.0]
    
    for line in lines:
        line = line.strip()
        if line.startswith("v "):
            vertices.append(line)
        elif line.startswith("vt "):
            uvs.append(line)
        elif line.startswith("vn "):
            normals.append(line)
        elif line.startswith("f "):
            faces.append(line)
        elif line.startswith("AS3DTAG "):
            tags.append(line)
    
    for vertex in vertices:
        parts = vertex.split()
        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        
        if x < lowest_point[0]:
            lowest_point[0] = x
        if y < lowest_point[1]:
            lowest_point[1] = y
        if z < lowest_point[2]:
            lowest_point[2] = z
        if x > highest_point[0]:
            highest_point[0] = x
        if y > highest_point[1]:
            highest_point[1] = y
        if z > highest_point[2]:
            highest_point[2] = z
    
    final_file = bytearray()
    
    # Header
    final_file.extend(b'MDL!\x02\x00\x00\x00\x01')
    final_file.extend(b'\x00' * 67)
    
    # Counts
    final_file.extend(int_to_bytes(len(vertices)))
    final_file.extend(int_to_bytes(len(uvs)))
    final_file.extend(int_to_bytes(len(faces)))
    final_file.extend(int_to_bytes(len(normals)))
    final_file.extend(int_to_bytes(len(tags)))
    
    # Add bounding box vertices at beginning
    vertices.insert(0, f"v {highest_point[0]} {highest_point[1]} {highest_point[2]}")
    vertices.insert(0, f"v {lowest_point[0]} {lowest_point[1]} {lowest_point[2]}")
    
    # Vertices
    for vertex in vertices:
        parts = vertex.split()
        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        final_file.extend(float_to_hex(x))
        final_file.extend(float_to_hex(-z))
        final_file.extend(float_to_hex(y))
    
    # UVs
    for uv in uvs:
        parts = uv.split()
        u, v = float(parts[1]), float(parts[2])
        final_file.extend(float_to_hex(u))
        final_file.extend(float_to_hex(v))
    
    # Faces
    for face in faces:
        parts = face.split()
        face_data = []
        
        for part in parts[1:]:
            face_data.append(part.split('/'))
        
        for vertex_data in face_data:
            for i in range(len(vertex_data)):
                vertex_data[i] = str(int(vertex_data[i]) - 1)
        
        # Vertex indices
        final_file.extend(int_to_bytes2(int(face_data[0][0])))
        final_file.extend(int_to_bytes2(int(face_data[1][0])))
        final_file.extend(int_to_bytes2(int(face_data[2][0])))
        
        # UV indices
        final_file.extend(int_to_bytes2(int(face_data[0][1])))
        final_file.extend(int_to_bytes2(int(face_data[1][1])))
        final_file.extend(int_to_bytes2(int(face_data[2][1])))
    
    # Normals
    for normal in normals:
        parts = normal.split()
        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        final_file.extend(float_to_hex(x))
        final_file.extend(float_to_hex(z))
        final_file.extend(float_to_hex(y))
    
    # Tags
    for tag in tags:
        parts = tag.split()
        tag_name = parts[1][:32].ljust(32, '\x00')
        
        for char in tag_name:
            final_file.extend(bytes([ord(char)]))
        
        x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
        final_file.extend(float_to_hex(x))
        final_file.extend(float_to_hex(-z))
        final_file.extend(float_to_hex(y))
        final_file.extend(b'\x00' * 12)
    
    output_path = Path(obj_file_path).with_suffix('.mdl')
    with open(output_path, 'wb') as f:
        f.write(final_file)
    
    print(f"converted {obj_file_path} -> {output_path}")


def convert_to_obj(mdl_file_path):
    with open(mdl_file_path, 'rb') as f:
        byte_file = f.read()
    
    vertices_count = struct.unpack('<I', byte_file[76:80])[0]
    uvs_count = struct.unpack('<I', byte_file[80:84])[0]
    faces_count = struct.unpack('<I', byte_file[84:88])[0]
    normals_count = struct.unpack('<I', byte_file[88:92])[0]
    
    vertices = []
    uvs = []
    faces = []
    uv_indices = []
    normals = []
    
    current_pos = 120
    
    # Read vertices
    for i in range(vertices_count):
        x = hex_float(byte_file[current_pos:current_pos+4])
        z = hex_float(byte_file[current_pos+4:current_pos+8])
        y = hex_float(byte_file[current_pos+8:current_pos+12])
        vertices.append([x, z, y])
        current_pos += 12
    
    # Read UVs
    for i in range(uvs_count):
        u = hex_float(byte_file[current_pos:current_pos+4])
        v = hex_float(byte_file[current_pos+4:current_pos+8])
        uvs.append([u, v])
        current_pos += 8
    
    # Read faces
    for i in range(faces_count):
        v1 = struct.unpack('<H', byte_file[current_pos:current_pos+2])[0]
        v2 = struct.unpack('<H', byte_file[current_pos+2:current_pos+4])[0]
        v3 = struct.unpack('<H', byte_file[current_pos+4:current_pos+6])[0]
        faces.append([v1, v2, v3])
        current_pos += 6
        
        uv1 = struct.unpack('<H', byte_file[current_pos:current_pos+2])[0]
        uv2 = struct.unpack('<H', byte_file[current_pos+2:current_pos+4])[0]
        uv3 = struct.unpack('<H', byte_file[current_pos+4:current_pos+6])[0]
        uv_indices.append([uv1, uv2, uv3])
        current_pos += 6
    
    # Read normals
    for i in range(normals_count):
        x = hex_float(byte_file[current_pos:current_pos+4])
        z = hex_float(byte_file[current_pos+4:current_pos+8])
        y = hex_float(byte_file[current_pos+8:current_pos+12])
        normals.append([x, z, y])
        current_pos += 12
    
    # Format vertices, UVs, normals
    for i in range(vertices_count):
        vertices[i] = [round(v, 4) for v in vertices[i]]
    
    for i in range(uvs_count):
        uvs[i] = [round(v, 4) for v in uvs[i]]
    
    for i in range(normals_count):
        normals[i] = [round(v, 4) for v in normals[i]]
    
    # Generate OBJ content
    final_file = f"# Vertices {vertices_count}\n"
    
    for vertex in vertices:
        final_file += f"v  {vertex[0]} {vertex[2]} {-vertex[1]}\n"
    
    final_file += f"\n# UVs {uvs_count}\n"
    
    for uv in uvs:
        final_file += f"vt  {uv[0]} {uv[1]}\n"
    
    final_file += f"\n# Normals {normals_count}\n"
    
    for normal in normals:
        final_file += f"vn  {normal[0]} {normal[2]} {normal[1]}\n"
    
    final_file += f"\n# Faces {faces_count}\n"
    
    for i in range(faces_count):
        face = faces[i]
        uv_idx = uv_indices[i]
        final_file += (f"f  {face[0]+1}/{uv_idx[0]+1}/{face[0]+1} "
                      f"{face[1]+1}/{uv_idx[1]+1}/{face[1]+1} "
                      f"{face[2]+1}/{uv_idx[2]+1}/{face[2]+1}\n")
    
    output_path = Path(mdl_file_path).with_suffix('.obj')
    with open(output_path, 'w') as f:
        f.write(final_file)
    
    print(f"converted {mdl_file_path} -> {output_path}")


def main():
    if len(sys.argv) != 2:
        print("usage: python airstrike-converter.py <file.obj|file.mdl>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"error: file {file_path} not found")
        sys.exit(1)
    
    if file_path.endswith('.mdl'):
        convert_to_obj(file_path)
    elif file_path.endswith('.obj'):
        convert_to_mdl(file_path)
    else:
        print("error: unsupported file format. use .obj or .mdl")
        sys.exit(1)


if __name__ == "__main__":
    main()
