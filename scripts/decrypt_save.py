#!/usr/bin/env python3
"""
divo save file decryption utility v1.0
"""
import sys
import argparse
import struct
import os
from pathlib import Path

__version__ = "1.0.0"

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colorize(text, color, force_color=False):
    """colorize text if stdout is a tty or force_color is True"""
    if force_color or (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
        return f"{color}{text}{Colors.RESET}"
    return text

def log_info(msg, quiet=False, color=None):
    """log info message"""
    if not quiet:
        if color:
            msg = colorize(msg, color)
        print(msg)

def log_error(msg, color=True):
    """log error message"""
    if color:
        msg = colorize(f"error: {msg}", Colors.RED)
    else:
        msg = f"error: {msg}"
    print(msg, file=sys.stderr)

def log_warning(msg, quiet=False, color=True):
    """log warning message"""
    if not quiet:
        if color:
            msg = colorize(f"warning: {msg}", Colors.YELLOW)
        else:
            msg = f"warning: {msg}"
        print(msg, file=sys.stderr)

def log_success(msg, quiet=False, color=True):
    """log success message"""
    if not quiet:
        if color:
            msg = colorize(msg, Colors.GREEN)
        print(msg)

def hexdump(data, offset=0, width=16, show_ascii=True):
    """generate hexdump output"""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        hex_part = hex_part.ljust(width * 3 - 1)
        
        if show_ascii:
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            line = f"{offset + i:08x}  {hex_part}  |{ascii_part}|"
        else:
            line = f"{offset + i:08x}  {hex_part}"
        
        lines.append(line)
    return '\n'.join(lines)

def validate_file_exists(path, name="file"):
    """validate that file exists"""
    if not Path(path).exists():
        log_error(f"{name} '{path}' does not exist")
        return False
    if not Path(path).is_file():
        log_error(f"'{path}' is not a file")
        return False
    return True

def check_overwrite(path, force=False, quiet=False):
    """check if file can be overwritten"""
    if Path(path).exists():
        if not force:
            log_error(f"output file '{path}' exists (use --force to overwrite)")
            return False
        else:
            log_warning(f"overwriting '{path}'", quiet)
    return True

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

def validate_decrypted_data(data):
    """basic validation of decrypted data"""
    if not data:
        return False, "empty data"
    
    # check for reasonable printable content ratio
    printable_count = sum(1 for b in data if 32 <= b <= 126 or b in [9, 10, 13])
    printable_ratio = printable_count / len(data)
    
    # check for excessive null bytes (might indicate failed decryption)
    null_ratio = data.count(0) / len(data)
    
    if null_ratio > 0.9:
        return False, f"excessive null bytes ({null_ratio:.1%})"
    
    if printable_ratio < 0.1 and null_ratio < 0.3:
        return False, f"low printable content ({printable_ratio:.1%})"
    
    return True, f"ok (printable: {printable_ratio:.1%}, nulls: {null_ratio:.1%})"

def decrypt_save(file_path, output_path=None, format_type='hex', verbose=False, quiet=False, force=False, validate=True):
    """decrypt save file and optionally write to output"""
    if not validate_file_exists(file_path, "input file"):
        return False
    
    if output_path and not check_overwrite(output_path, force, quiet):
        return False
    
    try:
        with open(file_path, 'rb') as f:
            # read header and extract key
            if verbose:
                log_info("reading file header...", quiet)
            
            header = f.read(0x108)
            if len(header) != 0x108:
                log_error(f"invalid header size: {len(header)} (expected {0x108})")
                return False
            
            key = header[4:4+0x100]
            if verbose:
                log_info(f"extracted key: {len(key)} bytes", quiet)
            
            # read and decrypt data
            if verbose:
                log_info("reading encrypted data...", quiet)
            
            data = f.read(0x574)
            if not data:
                log_error("no encrypted data found")
                return False
            
            if len(data) != 0x574:
                log_warning(f"unexpected data size: {len(data)} (expected {0x574})", quiet)
            
            if verbose:
                log_info("decrypting data...", quiet)
            
            decrypted = xor_crypt(data, key)
            
            # validate decrypted data
            if validate:
                is_valid, reason = validate_decrypted_data(decrypted)
                if verbose:
                    if is_valid:
                        log_info(f"data validation: {reason}", quiet, Colors.GREEN)
                    else:
                        log_warning(f"data validation: {reason}", quiet)
            
            if output_path:
                with open(output_path, 'wb') as out_f:
                    out_f.write(decrypted)
                log_success(f"decrypted data written to '{output_path}'", quiet)
            else:
                if format_type == 'hex':
                    print(decrypted.hex())
                elif format_type == 'hexdump':
                    print(hexdump(decrypted))
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
        log_error(f"i/o error: {e}")
        return False

def dump_decrypted(file_path, output_path, verbose=False, quiet=False, force=False):
    """decrypt save file and dump to output file"""
    if not validate_file_exists(file_path, "input file"):
        return False
    
    if not check_overwrite(output_path, force, quiet):
        return False
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(0x108)
            if len(header) != 0x108:
                log_error(f"invalid header size: {len(header)} (expected {0x108})")
                return False
            
            key = header[4:4+0x100]
            data = f.read(0x574)
            
            if not data:
                log_error("no encrypted data found")
                return False
            
            if verbose:
                log_info(f"decrypting {len(data)} bytes...", quiet)
            
            decrypted = xor_crypt(data, key)
            
            with open(output_path, 'wb') as out_f:
                out_f.write(decrypted)
            
            log_success(f"decrypted {len(decrypted)} bytes to '{output_path}'", quiet)
            return True
    except OSError as e:
        log_error(f"i/o error: {e}")
        return False

def dump_key(file_path, output_path=None, format_type='hex', verbose=False, quiet=False, force=False):
    """dump xor key from save file"""
    if not validate_file_exists(file_path, "input file"):
        return False
    
    if output_path and not check_overwrite(output_path, force, quiet):
        return False
    
    key = extract_key(file_path)
    if not key:
        log_error("failed to extract key")
        return False
    
    if verbose:
        log_info(f"extracted {len(key)} byte key", quiet)
    
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(key)
        log_success(f"key written to '{output_path}'", quiet)
    else:
        if format_type == 'hex':
            print(key.hex())
        elif format_type == 'hexdump':
            print(hexdump(key))
        elif format_type == 'raw':
            sys.stdout.buffer.write(key)
    
    return True

def info_save(file_path, verbose=False, quiet=False):
    """display save file information"""
    if not validate_file_exists(file_path, "input file"):
        return False
    
    try:
        with open(file_path, 'rb') as f:
            file_size = Path(file_path).stat().st_size
            header = f.read(0x108)
            
            if len(header) != 0x108:
                log_error(f"invalid header size: {len(header)} (expected {0x108})")
                return False
            
            data = f.read()
            
            print(colorize(f"file: {file_path}", Colors.BOLD))
            print(f"size: {file_size} bytes ({file_size:,})")
            print(f"header: {len(header)} bytes")
            print(f"data: {len(data)} bytes")
            print(f"expected data size: 0x574 ({0x574:,}) bytes")
            
            if len(data) != 0x574:
                print(colorize(f"size mismatch: got {len(data)}, expected {0x574}", Colors.YELLOW))
            
            print(f"file header: {header[:4].hex()}")
            print(f"key preview: {header[4:12].hex()}...")
            
            if data:
                key = header[4:4+0x100]
                
                # analyze key
                is_null_key = all(b == 0 for b in key)
                unique_bytes = len(set(key))
                
                print(f"key analysis:")
                print(f"  null key (no encryption): {colorize('yes' if is_null_key else 'no', Colors.GREEN if is_null_key else Colors.CYAN)}")
                print(f"  unique bytes: {unique_bytes}/256")
                
                if verbose:
                    print(f"  key entropy: {unique_bytes/256:.2%}")
                    most_common = max(set(key), key=key.count)
                    print(f"  most common byte: 0x{most_common:02x} ({key.count(most_common)} times)")
                
                decrypted = xor_crypt(data, key)
                
                # analyze decrypted content
                is_valid, validation_msg = validate_decrypted_data(decrypted)
                printable_ratio = sum(32 <= b <= 126 for b in decrypted) / len(decrypted)
                null_ratio = decrypted.count(0) / len(decrypted)
                
                print(f"decrypted analysis:")
                print(f"  validation: {colorize(validation_msg, Colors.GREEN if is_valid else Colors.YELLOW)}")
                print(f"  printable ratio: {printable_ratio:.2%}")
                print(f"  null bytes ratio: {null_ratio:.2%}")
                
                if printable_ratio > 0.7:
                    content_type = "text data"
                elif null_ratio > 0.5:
                    content_type = "structured binary data"
                else:
                    content_type = "binary data"
                
                print(f"  likely content: {colorize(content_type, Colors.CYAN)}")
                
                if verbose and printable_ratio > 0.3:
                    print(f"content preview:")
                    try:
                        preview = decrypted[:200].decode('utf-8', errors='replace')
                        print(f"  {repr(preview)}")
                    except:
                        print(f"  <decode failed>")
            
            return True
    except OSError as e:
        log_error(f"i/o error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='divo save file decryption utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  {sys.argv[0]} decrypt save.bin                    # decrypt to hex output
  {sys.argv[0]} decrypt save.bin -f text            # decrypt to text
  {sys.argv[0]} decrypt save.bin -o out.dat --force # decrypt to file
  {sys.argv[0]} dump save.bin decrypted.dat         # simple decrypt to file
  {sys.argv[0]} key save.bin                        # extract key as hex
  {sys.argv[0]} info save.bin -v                    # detailed file info

version: {__version__}
        """
    )
    
    parser.add_argument('--version', action='version', version=f'divo-decrypt {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='quiet mode (errors only)')
    parser.add_argument('--no-color', action='store_true', help='disable colored output')
    
    subparsers = parser.add_subparsers(dest='command', help='available commands')
    
    # decrypt command
    decrypt_parser = subparsers.add_parser('decrypt', help='decrypt save file')
    decrypt_parser.add_argument('input', help='input save file')
    decrypt_parser.add_argument('-o', '--output', help='output file')
    decrypt_parser.add_argument('-f', '--format', choices=['hex', 'hexdump', 'text', 'raw'], 
                              default='hex', help='output format (default: hex)')
    decrypt_parser.add_argument('--force', action='store_true', help='overwrite existing files')
    decrypt_parser.add_argument('--no-validate', action='store_true', help='skip data validation')
    
    # dump command
    dump_parser = subparsers.add_parser('dump', help='decrypt save file to output file')
    dump_parser.add_argument('input', help='input save file')
    dump_parser.add_argument('output', help='output file')
    dump_parser.add_argument('--force', action='store_true', help='overwrite existing files')
    
    # key command
    key_parser = subparsers.add_parser('key', help='extract xor key')
    key_parser.add_argument('input', help='input save file')
    key_parser.add_argument('-o', '--output', help='output key file')
    key_parser.add_argument('-f', '--format', choices=['hex', 'hexdump', 'raw'], 
                          default='hex', help='output format (default: hex)')
    key_parser.add_argument('--force', action='store_true', help='overwrite existing files')
    
    # info command
    info_parser = subparsers.add_parser('info', help='display save file information')
    info_parser.add_argument('input', help='input save file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # disable colors if requested or if output is redirected
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    # validate argument combinations
    if hasattr(args, 'quiet') and hasattr(args, 'verbose') and args.quiet and args.verbose:
        log_error("cannot use both --quiet and --verbose")
        return 1
    
    success = False
    try:
        if args.command == 'decrypt':
            success = decrypt_save(
                args.input, args.output, args.format,
                args.verbose, args.quiet, 
                getattr(args, 'force', False),
                not getattr(args, 'no_validate', False)
            )
        elif args.command == 'dump':
            success = dump_decrypted(
                args.input, args.output,
                args.verbose, args.quiet,
                getattr(args, 'force', False)
            )
        elif args.command == 'key':
            success = dump_key(
                args.input, args.output, args.format,
                args.verbose, args.quiet,
                getattr(args, 'force', False)
            )
        elif args.command == 'info':
            success = info_save(args.input, args.verbose, args.quiet)
    except KeyboardInterrupt:
        log_error("interrupted by user")
        return 130
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

