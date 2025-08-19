#!/usr/bin/env python3
"""
divo save file decryption utility
"""
import sys
import argparse
import struct
from pathlib import Path

def xor_crypt(data, key):
    """xor encrypt/decrypt data with key"""
    result = bytearray()
    key_len = len(key)
    
    for i, byte in enumerate(data):
        key_index = i % key_len
        result.append(byte ^ key[key_index])
    
    return bytes(result)

def extract_key(file_path):
    """extract xor key from save file"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(0x108)
            if len(header) != 0x108:
                return None
            return header[4:4+0x100]
    except OSError:
        return None

def decrypt_save(file_path, output_path=None, format_type='hex'):
    """decrypt save file and optionally write to output"""
    try:
        with open(file_path, 'rb') as f:
            # read header and extract key
            header = f.read(0x108)
            if len(header) != 0x108:
                print(f"error: invalid header size", file=sys.stderr)
                return False
            
            key = header[4:4+0x100]
            
            # read and decrypt data
            data = f.read(0x574)
            if not data:
                print(f"error: no data found", file=sys.stderr)
                return False
            
            decrypted = xor_crypt(data, key)
            
            if output_path:
                with open(output_path, 'wb') as out_f:
                    out_f.write(decrypted)
                print(f"decrypted data written to {output_path}")
            else:
                if format_type == 'hex':
                    print(decrypted.hex())
                elif format_type == 'text':
                    try:
                        text = decrypted.decode('utf-8', errors='replace')
                        print(text)
                    except:
                        for encoding in ['latin1', 'cp1252']:
                            try:
                                text = decrypted.decode(encoding, errors='replace')
                                print(text)
                                break
                            except:
                                continue
                        else:
                            print("<binary data>")
                elif format_type == 'raw':
                    sys.stdout.buffer.write(decrypted)
            
            return True
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return False

def dump_decrypted(file_path, output_path):
    """decrypt save file and dump to output file"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(0x108)
            if len(header) != 0x108:
                print(f"error: invalid header size", file=sys.stderr)
                return False
            
            key = header[4:4+0x100]
            data = f.read(0x574)
            
            if not data:
                print(f"error: no data found", file=sys.stderr)
                return False
            
            decrypted = xor_crypt(data, key)
            
            with open(output_path, 'wb') as out_f:
                out_f.write(decrypted)
            
            print(f"decrypted {len(decrypted)} bytes to {output_path}")
            return True
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return False

def dump_key(file_path, output_path=None, format_type='hex'):
    """dump xor key from save file"""
    key = extract_key(file_path)
    if not key:
        print(f"error: failed to extract key", file=sys.stderr)
        return False
    
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(key)
        print(f"key written to {output_path}")
    else:
        if format_type == 'hex':
            print(key.hex())
        elif format_type == 'raw':
            sys.stdout.buffer.write(key)
    
    return True

def info_save(file_path):
    """display save file information"""
    try:
        with open(file_path, 'rb') as f:
            file_size = Path(file_path).stat().st_size
            header = f.read(0x108)
            
            if len(header) != 0x108:
                print(f"error: invalid header size", file=sys.stderr)
                return False
            
            data = f.read()
            
            print(f"file: {file_path}")
            print(f"size: {file_size} bytes")
            print(f"header: {len(header)} bytes")
            print(f"data: {len(data)} bytes")
            print(f"expected data size: 0x574 ({0x574}) bytes")
            print(f"file header: {header[:4].hex()}")
            print(f"key preview: {header[4:12].hex()}...")
            
            if data:
                key = header[4:4+0x100]
                decrypted = xor_crypt(data, key)
                
                # check if key is null (all zeros)
                is_null_key = all(b == 0 for b in key)
                print(f"null key (no encryption): {is_null_key}")
                
                # try to identify content type
                printable_ratio = sum(32 <= b <= 126 for b in decrypted) / len(decrypted)
                null_ratio = decrypted.count(0) / len(decrypted)
                
                print(f"decrypted printable ratio: {printable_ratio:.2%}")
                print(f"decrypted null bytes ratio: {null_ratio:.2%}")
                
                if printable_ratio > 0.7:
                    print("likely content: text data")
                elif null_ratio > 0.5:
                    print("likely content: structured binary data")
                else:
                    print("likely content: binary data")
            
            return True
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='divo save file decryption utility',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='available commands')
    
    # decrypt command
    decrypt_parser = subparsers.add_parser('decrypt', help='decrypt save file')
    decrypt_parser.add_argument('input', help='input save file')
    decrypt_parser.add_argument('-o', '--output', help='output file')
    decrypt_parser.add_argument('-f', '--format', choices=['hex', 'text', 'raw'], 
                              default='hex', help='output format (default: hex)')
    
    # dump command
    dump_parser = subparsers.add_parser('dump', help='decrypt save file to output file')
    dump_parser.add_argument('input', help='input save file')
    dump_parser.add_argument('output', help='output file')
    
    # key command
    key_parser = subparsers.add_parser('key', help='extract xor key')
    key_parser.add_argument('input', help='input save file')
    key_parser.add_argument('-o', '--output', help='output key file')
    key_parser.add_argument('-f', '--format', choices=['hex', 'raw'], 
                          default='hex', help='output format (default: hex)')
    
    # info command
    info_parser = subparsers.add_parser('info', help='display save file information')
    info_parser.add_argument('input', help='input save file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    success = False
    if args.command == 'decrypt':
        success = decrypt_save(args.input, args.output, args.format)
    elif args.command == 'dump':
        success = dump_decrypted(args.input, args.output)
    elif args.command == 'key':
        success = dump_key(args.input, args.output, args.format)
    elif args.command == 'info':
        success = info_save(args.input)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

