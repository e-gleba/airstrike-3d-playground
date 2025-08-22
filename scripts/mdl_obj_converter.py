#!/usr/bin/env python3
"""
Airstrike 3D model format converter.

Converts between Wavefront OBJ and Airstrike 3D MDL formats with bidirectional
support and format validation. Replicates original JavaScript logic exactly.
"""

import argparse
import struct
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import logging

__version__ = "1.0.2"

# MDL format constants
MDL_SIGNATURE = b'MDL!\x02\x00\x00\x00\x01'
MDL_HEADER_PADDING = 67
MDL_DATA_OFFSET = 120


def setup_logging(verbose: bool):
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(levelname)s: %(message)s" if not verbose else "%(asctime)s %(levelname)s: %(message)s"
    logging.basicConfig(level=level, format=format_str)


def detect_format(path: Path) -> Optional[str]:
    """Detect file format from extension."""
    suffix = path.suffix.lower()
    if suffix == '.obj':
        return 'obj'
    elif suffix == '.mdl':
        return 'mdl'
    return None


def convert_to_mdl(input_path: Path, output_path: Path) -> bool:
    """Convert OBJ to MDL - exact replication of original JS logic."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
        
        vertices = []
        uvs = []
        faces = []
        normals = []
        tags = []
        
        lowest_point = [0, 0, 0]
        highest_point = [0, 0, 0]
        
        # Parse lines exactly like JS
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
        for vertex_line in vertices:
            temp = vertex_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            # Replicate JS parseInt bug on floats
            x_int = int(float(temp2[1]))  # parseInt behavior
            y_int = int(float(temp2[2]))
            z_int = int(float(temp2[3]))
            
            if x_int < lowest_point[0]: lowest_point[0] = x_int
            if y_int < lowest_point[1]: lowest_point[1] = y_int
            if z_int < lowest_point[2]: lowest_point[2] = z_int
            if x_int > highest_point[0]: highest_point[0] = x_int
            if y_int > highest_point[1]: highest_point[1] = y_int
            if z_int > highest_point[2]: highest_point[2] = z_int
        
        # Build final file
        final_file = bytearray()
        
        # Header exactly like JS
        final_file.extend([0x4d, 0x44, 0x4c, 0x21, 0x02, 0x00, 0x00, 0x00, 0x01])
        final_file.extend([0x00] * 67)
        
        # Add bounding box vertices like JS (unshift = insert at beginning)
        vertices.insert(0, f"v {highest_point[0]} {highest_point[1]} {highest_point[2]}")
        vertices.insert(0, f"v {lowest_point[0]} {lowest_point[1]} {lowest_point[2]}")
        
        # Counts
        final_file.extend(struct.pack('<I', len(vertices)))
        final_file.extend(struct.pack('<I', len(uvs)))
        final_file.extend(struct.pack('<I', len(faces)))
        final_file.extend(struct.pack('<I', len(normals)))
        final_file.extend(struct.pack('<I', len(tags)))
        
        # Vertices - exact JS transformation: X, -Z, Y
        for vertex_line in vertices:
            temp = vertex_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            x, y, z = float(temp2[1]), float(temp2[2]), float(temp2[3])
            final_file.extend(struct.pack('<f', x))      # temp2[1]
            final_file.extend(struct.pack('<f', -z))     # -temp2[3]
            final_file.extend(struct.pack('<f', y))      # temp2[2]
        
        # UVs
        for uv_line in uvs:
            temp = uv_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            u, v = float(temp2[1]), float(temp2[2])
            final_file.extend(struct.pack('<f', u))
            final_file.extend(struct.pack('<f', v))
        
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
            
            # Store vertex indices first, then UV indices
            final_file.extend(struct.pack('<H', int(temp3[0][0])))  # v1
            final_file.extend(struct.pack('<H', int(temp3[1][0])))  # v2
            final_file.extend(struct.pack('<H', int(temp3[2][0])))  # v3
            final_file.extend(struct.pack('<H', int(temp3[0][1])))  # uv1
            final_file.extend(struct.pack('<H', int(temp3[1][1])))  # uv2
            final_file.extend(struct.pack('<H', int(temp3[2][1])))  # uv3
        
        # Normals - exact JS transformation: X, Z, Y
        for normal_line in normals:
            temp = normal_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            x, y, z = float(temp2[1]), float(temp2[2]), float(temp2[3])
            final_file.extend(struct.pack('<f', x))      # temp2[1]
            final_file.extend(struct.pack('<f', z))      # temp2[3]
            final_file.extend(struct.pack('<f', y))      # temp2[2]
        
        # Tags
        for tag_line in tags:
            temp = tag_line.split(' ')
            temp2 = [part for part in temp if part != ' ' and part != '']
            
            tag_name = temp2[1]
            if len(tag_name) > 32:
                tag_name = tag_name[:32]
            
            # Tag name (32 bytes)
            for char in tag_name:
                final_file.extend([ord(char)])
            for _ in range(len(tag_name), 32):
                final_file.extend([0x00])
            
            # Tag position: X, -Z, Y
            x, y, z = float(temp2[2]), float(temp2[3]), float(temp2[4])
            final_file.extend(struct.pack('<f', x))
            final_file.extend(struct.pack('<f', -z))
            final_file.extend(struct.pack('<f', y))
            
            # Reserved 12 bytes
            final_file.extend([0x00] * 12)
        
        # Write file
        with open(output_path, 'wb') as f:
            f.write(final_file)
        
        logging.info(f"converted {input_path} -> {output_path}")
        return True
        
    except (IOError, ValueError, IndexError) as e:
        logging.error(f"conversion failed: {e}")
        return False


def convert_to_obj(input_path: Path, output_path: Path) -> bool:
    """Convert MDL to OBJ - exact replication of original JS logic."""
    try:
        with open(input_path, 'rb') as f:
            byte_file = f.read()
        
        if len(byte_file) < MDL_DATA_OFFSET or byte_file[:9] != MDL_SIGNATURE:
            logging.error("invalid MDL file format")
            return False
        
        # Read counts exactly like JS
        vertices_count = (byte_file[79] * 256**3 + byte_file[78] * 256**2 + 
                         byte_file[77] * 256 + byte_file[76])
        uvs_count = (byte_file[83] * 256**3 + byte_file[82] * 256**2 + 
                    byte_file[81] * 256 + byte_file[80])
        faces_count = (byte_file[87] * 256**3 + byte_file[86] * 256**2 + 
                      byte_file[85] * 256 + byte_file[84])
        normals_count = (byte_file[91] * 256**3 + byte_file[90] * 256**2 + 
                        byte_file[89] * 256 + byte_file[88])
        
        vertices = []
        uvs = []
        faces = []
        uv_indices = []
        normals = []
        
        current_pos = 120
        
        # Read vertices exactly like JS
        for i in range(vertices_count):
            # Read as little-endian bytes and reconstruct like JS
            temp1 = [byte_file[current_pos + 3], byte_file[current_pos + 2], 
                     byte_file[current_pos + 1], byte_file[current_pos]]
            temp2 = [byte_file[current_pos + 7], byte_file[current_pos + 6], 
                     byte_file[current_pos + 5], byte_file[current_pos + 4]]
            temp3 = [byte_file[current_pos + 11], byte_file[current_pos + 10], 
                     byte_file[current_pos + 9], byte_file[current_pos + 8]]
            
            x = struct.unpack('<f', bytes([temp1[3], temp1[2], temp1[1], temp1[0]]))[0]
            z = struct.unpack('<f', bytes([temp2[3], temp2[2], temp2[1], temp2[0]]))[0]
            y = struct.unpack('<f', bytes([temp3[3], temp3[2], temp3[1], temp3[0]]))[0]
            
            vertices.append([x, z, y])
            current_pos += 12
        
        # Read UVs
        for i in range(uvs_count):
            temp1 = [byte_file[current_pos + 3], byte_file[current_pos + 2], 
                     byte_file[current_pos + 1], byte_file[current_pos]]
            temp2 = [byte_file[current_pos + 7], byte_file[current_pos + 6], 
                     byte_file[current_pos + 5], byte_file[current_pos + 4]]
            
            u = struct.unpack('<f', bytes([temp1[3], temp1[2], temp1[1], temp1[0]]))[0]
            v = struct.unpack('<f', bytes([temp2[3], temp2[2], temp2[1], temp2[0]]))[0]
            
            uvs.append([u, v])
            current_pos += 8
        
        # Read faces exactly like JS
        for i in range(faces_count):
            v1 = byte_file[current_pos] + byte_file[current_pos + 1] * 256
            v2 = byte_file[current_pos + 2] + byte_file[current_pos + 3] * 256
            v3 = byte_file[current_pos + 4] + byte_file[current_pos + 5] * 256
            faces.append([v1, v2, v3])
            current_pos += 6
            
            uv1 = byte_file[current_pos] + byte_file[current_pos + 1] * 256
            uv2 = byte_file[current_pos + 2] + byte_file[current_pos + 3] * 256
            uv3 = byte_file[current_pos + 4] + byte_file[current_pos + 5] * 256
            uv_indices.append([uv1, uv2, uv3])
            current_pos += 6
        
        # Read normals
        for i in range(normals_count):
            temp1 = [byte_file[current_pos + 3], byte_file[current_pos + 2], 
                     byte_file[current_pos + 1], byte_file[current_pos]]
            temp2 = [byte_file[current_pos + 7], byte_file[current_pos + 6], 
                     byte_file[current_pos + 5], byte_file[current_pos + 4]]
            temp3 = [byte_file[current_pos + 11], byte_file[current_pos + 10], 
                     byte_file[current_pos + 9], byte_file[current_pos + 8]]
            
            x = struct.unpack('<f', bytes([temp1[3], temp1[2], temp1[1], temp1[0]]))[0]
            z = struct.unpack('<f', bytes([temp2[3], temp2[2], temp2[1], temp2[0]]))[0]
            y = struct.unpack('<f', bytes([temp3[3], temp3[2], temp3[1], temp3[0]]))[0]
            
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
        final_file = f"# Vertices {vertices_count}"
        
        for i in range(vertices_count):
            # JS: vertices[i][0] + " " + vertices[i][2] + " " + (-vertices[i][1])
            final_file += f"\nv  {vertices[i][0]} {vertices[i][2]} {-vertices[i][1]}"
        
        final_file += f"\n\n# UVs {uvs_count}"
        
        for i in range(uvs_count):
            final_file += f"\nvt  {uvs[i][0]} {uvs[i][1]}"
        
        final_file += f"\n\n# Normals {normals_count}"
        
        for i in range(normals_count):
            # JS: normals[i][0] + " " + normals[i][2] + " " + normals[i][1]
            final_file += f"\nvn  {normals[i][0]} {normals[i][2]} {normals[i][1]}"
        
        final_file += f"\n\n# Faces {faces_count}"
        
        for i in range(faces_count):
            # JS: (faces[i][0] + 1) + "/" + (uvIndices[i][0] + 1) + "/" + (faces[i][0] + 1)
            v1, v2, v3 = faces[i][0] + 1, faces[i][1] + 1, faces[i][2] + 1
            uv1, uv2, uv3 = uv_indices[i][0] + 1, uv_indices[i][1] + 1, uv_indices[i][2] + 1
            
            final_file += f"\nf  {v1}/{uv1}/{v1} {v2}/{uv2}/{v2} {v3}/{uv3}/{v3}"
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_file)
        
        logging.info(f"converted {input_path} -> {output_path}")
        return True
        
    except (IOError, struct.error, IndexError) as e:
        logging.error(f"conversion failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert between Wavefront OBJ and Airstrike 3D MDL formats",
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
        logging.error(f"input file not found: {args.input}")
        return 1
    
    # Determine conversion direction
    input_format = detect_format(args.input)
    if not input_format:
        logging.error(f"unsupported input format: {args.input.suffix}")
        return 1
    
    if args.format:
        output_format = args.format
    else:
        output_format = 'mdl' if input_format == 'obj' else 'obj'
    
    if input_format == output_format:
        logging.error("input and output formats are the same")
        return 1
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.input.with_suffix(f'.{output_format}')
    
    # Convert
    if output_format == 'mdl':
        success = convert_to_mdl(args.input, output_path)
    else:
        success = convert_to_obj(args.input, output_path)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
