#!/usr/bin/env python3
"""
Airstrike 3D model format converter - Performance optimized edition.

High-performance converter between Wavefront OBJ and Airstrike 3D MDL formats
using Python 3.12+ features and optimizations. EXACT replication of JS logic.
"""

import argparse
import struct
import sys
from pathlib import Path
from typing import Final, Optional
import logging
from contextlib import suppress
import mmap

__version__: Final = "2.0.2"

# MDL format constants
MDL_SIGNATURE: Final = b'MDL!\x02\x00\x00\x00\x01'
MDL_DATA_OFFSET: Final = 120

# Struct formatters for performance
U32_PACK: Final = struct.Struct('<I').pack
U16_PACK: Final = struct.Struct('<H').pack
F32_PACK: Final = struct.Struct('<f').pack
U32_UNPACK: Final = struct.Struct('<I').unpack_from
F32x3_UNPACK: Final = struct.Struct('<3f').unpack_from
F32x2_UNPACK: Final = struct.Struct('<2f').unpack_from

# Pre-compiled byte patterns
HEADER_BYTES: Final = bytes([0x4d, 0x44, 0x4c, 0x21, 0x02, 0x00, 0x00, 0x00, 0x01])


def setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = ("%(levelname)s: %(message)s" if not verbose 
                  else "%(asctime)s %(levelname)s: %(message)s")
    logging.basicConfig(level=level, format=format_str, force=True)


def detect_format(path: Path) -> Optional[str]:
    """Detect file format from extension."""
    return {'obj': 'obj', 'mdl': 'mdl'}.get(path.suffix.lower().removeprefix('.'))


def convert_to_mdl_exact(input_path: Path, output_path: Path) -> bool:
    """Convert OBJ to MDL - EXACT replication of original JS logic."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
        
        # Parse exactly like JS
        vertices = []
        uvs = []
        faces = []
        normals = []
        tags = []
        
        for line in lines:
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
        
        # Calculate bounds exactly like JS (with parseInt bug)
        lowest_point = [0, 0, 0]
        highest_point = [0, 0, 0]
        
        for vertex_line in vertices:
            temp = vertex_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            # Replicate JS parseInt() bug on floats
            x_int = int(float(temp2[1]))
            y_int = int(float(temp2[2]))
            z_int = int(float(temp2[3]))
            
            if x_int < lowest_point[0]: lowest_point[0] = x_int
            if y_int < lowest_point[1]: lowest_point[1] = y_int
            if z_int < lowest_point[2]: lowest_point[2] = z_int
            if x_int > highest_point[0]: highest_point[0] = x_int
            if y_int > highest_point[1]: highest_point[1] = y_int
            if z_int > highest_point[2]: highest_point[2] = z_int
        
        # Add bounding box vertices EXACTLY like JS
        # JS: vertices.unshift("v " + highestPoint[0] + " " + highestPoint[1] + " " + highestPoint[2]);
        # JS: vertices.unshift("v " + lowestPoint[0] + " " + lowestPoint[1] + " " + lowestPoint[2]);
        vertices.insert(0, f"v {highest_point[0]} {highest_point[1]} {highest_point[2]}")
        vertices.insert(0, f"v {lowest_point[0]} {lowest_point[1]} {lowest_point[2]}")
        
        # Build MDL data
        buffer = bytearray()
        
        # Header exactly like JS
        buffer.extend(HEADER_BYTES)
        buffer.extend(bytes(67))  # 67 null bytes
        
        # Counts (vertices now includes bounding box vertices)
        buffer.extend(U32_PACK(len(vertices)))
        buffer.extend(U32_PACK(len(uvs)))
        buffer.extend(U32_PACK(len(faces)))
        buffer.extend(U32_PACK(len(normals)))
        buffer.extend(U32_PACK(len(tags)))
        
        # Process ALL vertices (including bounding box ones at start)
        for vertex_line in vertices:
            temp = vertex_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            x, y, z = float(temp2[1]), float(temp2[2]), float(temp2[3])
            # JS transformation: X, -Z, Y
            buffer.extend(F32_PACK(x))
            buffer.extend(F32_PACK(-z))
            buffer.extend(F32_PACK(y))
        
        # UVs
        for uv_line in uvs:
            temp = uv_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            u, v = float(temp2[1]), float(temp2[2])
            buffer.extend(F32_PACK(u))
            buffer.extend(F32_PACK(v))
        
        # Faces - exact JS logic
        for face_line in faces:
            temp = face_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            temp3 = []
            for element in temp2:
                if element != 'f':
                    temp3.append(element.split('/'))
            
            # Convert to 0-based indices like JS
            for j in range(len(temp3)):
                for h in range(len(temp3[j])):
                    temp3[j][h] = str(int(temp3[j][h]) - 1)
            
            # Store vertex indices first, then UV indices (JS order)
            buffer.extend(U16_PACK(int(temp3[0][0])))  # v1
            buffer.extend(U16_PACK(int(temp3[1][0])))  # v2
            buffer.extend(U16_PACK(int(temp3[2][0])))  # v3
            buffer.extend(U16_PACK(int(temp3[0][1])))  # uv1
            buffer.extend(U16_PACK(int(temp3[1][1])))  # uv2
            buffer.extend(U16_PACK(int(temp3[2][1])))  # uv3
        
        # Normals - exact JS transformation: X, Z, Y
        for normal_line in normals:
            temp = normal_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            x, y, z = float(temp2[1]), float(temp2[2]), float(temp2[3])
            buffer.extend(F32_PACK(x))   # temp2[1]
            buffer.extend(F32_PACK(z))   # temp2[3]
            buffer.extend(F32_PACK(y))   # temp2[2]
        
        # Tags
        for tag_line in tags:
            temp = tag_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            tag_name = temp2[1]
            if len(tag_name) > 32:
                tag_name = tag_name[:32]
            
            # Tag name (32 bytes)
            for char in tag_name:
                buffer.append(ord(char))
            for _ in range(len(tag_name), 32):
                buffer.append(0x00)
            
            # Tag position: X, -Z, Y (same as vertices)
            x, y, z = float(temp2[2]), float(temp2[3]), float(temp2[4])
            buffer.extend(F32_PACK(x))
            buffer.extend(F32_PACK(-z))
            buffer.extend(F32_PACK(y))
            
            # Reserved 12 bytes
            buffer.extend(bytes(12))
        
        # Write file
        with open(output_path, 'wb') as f:
            f.write(buffer)
        
        logging.info("converted %s -> %s", input_path, output_path)
        return True
        
    except (OSError, ValueError, IndexError) as e:
        logging.error("conversion failed: %s", e)
        return False


def convert_to_obj_exact(input_path: Path, output_path: Path) -> bool:
    """Convert MDL to OBJ - EXACT replication of original JS logic."""
    try:
        with open(input_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                if len(mm) < MDL_DATA_OFFSET or mm[:9] != MDL_SIGNATURE:
                    logging.error("invalid MDL file format")
                    return False
                
                # Read counts exactly like JS
                vertices_count = (mm[79] * 256**3 + mm[78] * 256**2 + 
                                mm[77] * 256 + mm[76])
                uvs_count = (mm[83] * 256**3 + mm[82] * 256**2 + 
                           mm[81] * 256 + mm[80])
                faces_count = (mm[87] * 256**3 + mm[86] * 256**2 + 
                             mm[85] * 256 + mm[84])
                normals_count = (mm[91] * 256**3 + mm[90] * 256**2 + 
                               mm[89] * 256 + mm[88])
                
                vertices = []
                uvs = []
                faces = []
                uv_indices = []
                normals = []
                
                current_pos = 120
                
                # Read vertices exactly like JS
                for i in range(vertices_count):
                    x, z, y = F32x3_UNPACK(mm, current_pos)
                    vertices.append([x, z, y])
                    current_pos += 12
                
                # Read UVs
                for i in range(uvs_count):
                    u, v = F32x2_UNPACK(mm, current_pos)
                    uvs.append([u, v])
                    current_pos += 8
                
                # Read faces exactly like JS
                for i in range(faces_count):
                    v1 = mm[current_pos] + mm[current_pos + 1] * 256
                    v2 = mm[current_pos + 2] + mm[current_pos + 3] * 256
                    v3 = mm[current_pos + 4] + mm[current_pos + 5] * 256
                    faces.append([v1, v2, v3])
                    current_pos += 6
                    
                    uv1 = mm[current_pos] + mm[current_pos + 1] * 256
                    uv2 = mm[current_pos + 2] + mm[current_pos + 3] * 256
                    uv3 = mm[current_pos + 4] + mm[current_pos + 5] * 256
                    uv_indices.append([uv1, uv2, uv3])
                    current_pos += 6
                
                # Read normals
                for i in range(normals_count):
                    x, z, y = F32x3_UNPACK(mm, current_pos)
                    normals.append([x, z, y])
                    current_pos += 12
                
                # Format precision exactly like JS
                for i in range(vertices_count):
                    vertices[i][0] = round(vertices[i][0], 4)
                    vertices[i][1] = round(vertices[i][1], 4)
                    vertices[i][2] = round(vertices[i][2], 4)
                
                for i in range(uvs_count):
                    uvs[i][0] = round(uvs[i][0], 4)
                    uvs[i][1] = round(uvs[i][1], 4)
                
                for i in range(normals_count):
                    normals[i][0] = round(normals[i][0], 4)
                    normals[i][1] = round(normals[i][1], 4)
                    normals[i][2] = round(normals[i][2], 4)
                
                # Build OBJ exactly like JS
                output_lines = [f"# Vertices {vertices_count}"]
                
                for i in range(vertices_count):
                    # JS: vertices[i][0] + " " + vertices[i][2] + " " + (-vertices[i][1])
                    output_lines.append(f"v  {vertices[i][0]} {vertices[i][2]} {-vertices[i][1]}")
                
                output_lines.append(f"\n# UVs {uvs_count}")
                
                for i in range(uvs_count):
                    output_lines.append(f"vt  {uvs[i][0]} {uvs[i][1]}")
                
                output_lines.append(f"\n# Normals {normals_count}")
                
                for i in range(normals_count):
                    # JS: normals[i][0] + " " + normals[i][2] + " " + normals[i][1]
                    output_lines.append(f"vn  {normals[i][0]} {normals[i][2]} {normals[i][1]}")
                
                output_lines.append(f"\n# Faces {faces_count}")
                
                for i in range(faces_count):
                    # JS: (faces[i][0] + 1) + "/" + (uvIndices[i][0] + 1) + "/" + (faces[i][0] + 1)
                    v1, v2, v3 = faces[i][0] + 1, faces[i][1] + 1, faces[i][2] + 1
                    uv1, uv2, uv3 = uv_indices[i][0] + 1, uv_indices[i][1] + 1, uv_indices[i][2] + 1
                    
                    output_lines.append(f"f  {v1}/{uv1}/{v1} {v2}/{uv2}/{v2} {v3}/{uv3}/{v3}")
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        logging.info("converted %s -> %s", input_path, output_path)
        return True
        
    except (OSError, struct.error, IndexError) as e:
        logging.error("conversion failed: %s", e)
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Airstrike 3D model format converter - exact JS replication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s model.obj                    # convert to MDL
  %(prog)s model.mdl                    # convert to OBJ
  %(prog)s -o output.mdl input.obj      # specify output file
  %(prog)s --format=obj input.mdl       # force output format
        """)
    
    parser.add_argument('input', type=Path, help="input file")
    parser.add_argument('-o', '--output', type=Path, help="output file")
    parser.add_argument('--format', choices=['obj', 'mdl'], help="force output format")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if not args.input.exists():
        logging.error("input file not found: %s", args.input)
        return 1
    
    input_format = detect_format(args.input)
    if not input_format:
        logging.error("unsupported input format: %s", args.input.suffix)
        return 1
    
    output_format = args.format or ('mdl' if input_format == 'obj' else 'obj')
    
    if input_format == output_format:
        logging.error("input and output formats are the same")
        return 1
    
    output_path = args.output or args.input.with_suffix(f'.{output_format}')
    
    converter = (convert_to_mdl_exact if output_format == 'mdl' 
                 else convert_to_obj_exact)
    
    return 0 if converter(args.input, output_path) else 1


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        sys.exit(main())
