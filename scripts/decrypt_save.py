#!/usr/bin/env python3
"""
divo save file crypto utility
- decrypt payload
- extract key
- encrypt payload back into save (bit-identical with same key)
- roundtrip verification

layout:
  header (0x108):
    [0x00:4]  float32 1.0f
    [0x04:260] 256-byte xor key
    [0x104:4] uint32 le, low 16 bits = crc16 over encrypted payload
  payload (0x574):
    xor-encrypted bytes
"""
import sys
import argparse
import struct
from pathlib import Path

__version__ = "1.1.1"

SAVE_HDR_SIZE = 0x108
SAVE_DATA_SIZE = 0x574
KEY_SIZE = 256

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colorize(text, color, force_color=False):
    if force_color or (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
        return f"{color}{text}{Colors.RESET}"
    return text

def log_info(msg, quiet=False, color=None):
    if not quiet:
        print(colorize(msg, color) if color else msg)

def log_error(msg, color=True):
    s = f"error: {msg}"
    print(colorize(s, Colors.RED) if color else s, file=sys.stderr)

def log_warning(msg, quiet=False, color=True):
    if not quiet:
        s = f"warning: {msg}"
        print(colorize(s, Colors.YELLOW) if color else s, file=sys.stderr)

def log_success(msg, quiet=False, color=True):
    if not quiet:
        print(colorize(msg, Colors.GREEN) if color else msg)

def hexdump(data, offset=0, width=16, show_ascii=True):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02x}' for b in chunk).ljust(width * 3 - 1)
        if show_ascii:
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            line = f"{offset + i:08x}  {hex_part}  |{ascii_part}|"
        else:
            line = f"{offset + i:08x}  {hex_part}"
        lines.append(line)
    return '\n'.join(lines)

def validate_file_exists(path, name="file"):
    p = Path(path)
    if not p.exists():
        log_error(f"{name} '{path}' does not exist")
        return False
    if not p.is_file():
        log_error(f"'{path}' is not a file")
        return False
    return True

def check_overwrite(path, force=False, quiet=False):
    if Path(path).exists() and not force:
        log_error(f"output file '{path}' exists (use --force to overwrite)")
        return False
    if Path(path).exists() and force:
        log_warning(f"overwriting '{path}'", quiet)
    return True

def xor_crypt(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    out = bytearray(len(data))
    klen = len(key)
    for i, b in enumerate(data):
        out[i] = b ^ key[i % klen]
    return bytes(out)

def crc16_ccitt_false(data: bytes, seed: int = 0xFFFF) -> int:
    crc = seed & 0xFFFF
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def extract_key(file_path: str) -> bytes | None:
    try:
        with open(file_path, 'rb') as f:
            header = f.read(SAVE_HDR_SIZE)
            if len(header) != SAVE_HDR_SIZE:
                return None
            return header[4:4+KEY_SIZE]
    except OSError:
        return None

def build_header(key: bytes, crc16: int) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 256 bytes")
    hdr = bytearray(SAVE_HDR_SIZE)
    hdr[0:4] = struct.pack("<f", 1.0)
    hdr[4:4+KEY_SIZE] = key
    hdr[260:264] = struct.pack("<I", crc16 & 0xFFFF)
    return bytes(hdr)

def validate_decrypted_data(data: bytes) -> tuple[bool, str]:
    if not data:
        return False, "empty data"
    printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    pr = printable / len(data)
    nr = data.count(0) / len(data)
    if nr > 0.9:
        return False, f"excessive null bytes ({nr:.1%})"
    if pr < 0.1 and nr < 0.3:
        return False, f"low printable content ({pr:.1%})"
    return True, f"ok (printable: {pr:.1%}, nulls: {nr:.1%})"

def decrypt_save(file_path, output_path=None, fmt='hex', verbose=False, quiet=False, force=False, validate=True, print_key=False):
    if not validate_file_exists(file_path, "input file"):
        return False
    if output_path and not check_overwrite(output_path, force, quiet):
        return False
    try:
        with open(file_path, 'rb') as f:
            header = f.read(SAVE_HDR_SIZE)
            if len(header) != SAVE_HDR_SIZE:
                log_error(f"invalid header size: {len(header)} (expected {SAVE_HDR_SIZE})")
                return False
            magic = header[:4]
            key = header[4:4+KEY_SIZE]
            crc_stored, = struct.unpack("<I", header[260:264])
            crc_stored &= 0xFFFF
            if verbose:
                log_info(f"magic: {magic.hex()} key: {len(key)} bytes crc16: 0x{crc_stored:04x}", quiet)
            data = f.read(SAVE_DATA_SIZE)
            if not data:
                log_error("no encrypted data found")
                return False
            if len(data) != SAVE_DATA_SIZE:
                log_warning(f"unexpected data size: {len(data)} (expected {SAVE_DATA_SIZE})", quiet)
            decrypted = xor_crypt(data, key)
            if validate:
                is_valid, reason = validate_decrypted_data(decrypted)
                if verbose:
                    log_info(f"data validation: {reason}", quiet, Colors.GREEN if is_valid else Colors.YELLOW)
            if print_key:
                print(key.hex())
            if output_path:
                with open(output_path, 'wb') as out_f:
                    out_f.write(decrypted)
                log_success(f"decrypted data written to '{output_path}'", quiet)
            else:
                if fmt == 'hex':
                    print(decrypted.hex())
                elif fmt == 'hexdump':
                    print(hexdump(decrypted))
                elif fmt == 'text':
                    try:
                        print(decrypted.decode('utf-8', errors='replace'))
                    except Exception:
                        print(decrypted.decode('latin1', errors='replace'))
                elif fmt == 'raw':
                    sys.stdout.buffer.write(decrypted)
            return True
    except OSError as e:
        log_error(f"i/o error: {e}")
        return False

def dump_decrypted(file_path, output_path, verbose=False, quiet=False, force=False):
    if not validate_file_exists(file_path, "input file"):
        return False
    if not check_overwrite(output_path, force, quiet):
        return False
    try:
        with open(file_path, 'rb') as f:
            header = f.read(SAVE_HDR_SIZE)
            if len(header) != SAVE_HDR_SIZE:
                log_error(f"invalid header size: {len(header)} (expected {SAVE_HDR_SIZE})")
                return False
            key = header[4:4+KEY_SIZE]
            data = f.read(SAVE_DATA_SIZE)
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

def dump_key(file_path, output_path=None, fmt='hex', verbose=False, quiet=False, force=False):
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
        if fmt == 'hex':
            print(key.hex())
        elif fmt == 'hexdump':
            print(hexdump(key))
        elif fmt == 'raw':
            sys.stdout.buffer.write(key)
    return True

def info_save(file_path, verbose=False, quiet=False):
    if not validate_file_exists(file_path, "input file"):
        return False
    try:
        with open(file_path, 'rb') as f:
            file_size = Path(file_path).stat().st_size
            header = f.read(SAVE_HDR_SIZE)
            if len(header) != SAVE_HDR_SIZE:
                log_error(f"invalid header size: {len(header)} (expected {SAVE_HDR_SIZE})")
                return False
            data = f.read(SAVE_DATA_SIZE)
            print(colorize(f"file: {file_path}", Colors.BOLD))
            print(f"size: {file_size} bytes ({file_size:,})")
            print(f"header: {len(header)} bytes")
            print(f"data: {len(data)} bytes")
            print(f"expected data size: 0x{SAVE_DATA_SIZE:x} ({SAVE_DATA_SIZE:,}) bytes")
            if len(data) != SAVE_DATA_SIZE:
                print(colorize(f"size mismatch: got {len(data)}, expected {SAVE_DATA_SIZE}", Colors.YELLOW))
            print(f"file header: {header[:4].hex()}")
            key = header[4:4+KEY_SIZE]
            print(f"key preview: {key[:8].hex()}...")
            if data:
                is_null_key = all(b == 0 for b in key)
                unique_bytes = len(set(key))
                print("key analysis:")
                print(f"  null key (no encryption): {colorize('yes' if is_null_key else 'no', Colors.GREEN if is_null_key else Colors.CYAN)}")
                print(f"  unique bytes: {unique_bytes}/256")
                if verbose:
                    print(f"  key entropy: {unique_bytes/256:.2%}")
                decrypted = xor_crypt(data, key)
                is_valid, validation_msg = validate_decrypted_data(decrypted)
                printable_ratio = sum(32 <= b <= 126 for b in decrypted) / len(decrypted)
                null_ratio = decrypted.count(0) / len(decrypted)
                print("decrypted analysis:")
                print(f"  validation: {colorize(validation_msg, Colors.GREEN if is_valid else Colors.YELLOW)}")
                print(f"  printable ratio: {printable_ratio:.2%}")
                print(f"  null bytes ratio: {null_ratio:.2%}")
            return True
    except OSError as e:
        log_error(f"i/o error: {e}")
        return False

def encrypt_payload(plain: bytes, key: bytes) -> bytes:
    if len(plain) != SAVE_DATA_SIZE:
        raise ValueError(f"payload must be {SAVE_DATA_SIZE} bytes")
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 256 bytes")
    return xor_crypt(plain, key)

def encrypt_save(payload_path: str, out_path: str, key_path: str = None, from_save_path: str = None,
                 force: bool = False, quiet: bool = False) -> bool:
    if not validate_file_exists(payload_path, "payload file"):
        return False
    if not check_overwrite(out_path, force, quiet):
        return False
    key = None
    if key_path:
        if not validate_file_exists(key_path, "key file"):
            return False
        with open(key_path, "rb") as f:
            key = f.read()
    elif from_save_path:
        if not validate_file_exists(from_save_path, "source save"):
            return False
        key = extract_key(from_save_path)
    else:
        log_error("provide --key file or --from-save to extract key")
        return False
    if key is None or len(key) != KEY_SIZE:
        log_error(f"invalid key size: {0 if key is None else len(key)} (expected 256)")
        return False
    with open(payload_path, "rb") as f:
        plain = f.read()
    if len(plain) != SAVE_DATA_SIZE:
        log_error(f"invalid payload size: {len(plain)} (expected {SAVE_DATA_SIZE})")
        return False
    cipher = encrypt_payload(plain, key)
    crc16 = crc16_ccitt_false(cipher, 0xFFFF)
    hdr = build_header(key, crc16)
    with open(out_path, "wb") as f:
        f.write(hdr)
        f.write(cipher)
    log_success(f"wrote encrypted save to '{out_path}'", quiet)
    return True

def roundtrip_verify(save_path: str, verbose: bool = False, quiet: bool = False) -> bool:
    if not validate_file_exists(save_path, "input save"):
        return False
    with open(save_path, "rb") as f:
        orig_hdr = f.read(SAVE_HDR_SIZE)
        orig_cipher = f.read(SAVE_DATA_SIZE)
    if len(orig_hdr) != SAVE_HDR_SIZE or len(orig_cipher) != SAVE_DATA_SIZE:
        log_error("bad save layout")
        return False
    key = orig_hdr[4:4+KEY_SIZE]
    plain = xor_crypt(orig_cipher, key)
    re_cipher = xor_crypt(plain, key)
    crc16 = crc16_ccitt_false(re_cipher, 0xFFFF)
    re_hdr = build_header(key, crc16)
    rebuilt = re_hdr + re_cipher
    with open(save_path, "rb") as f:
        original = f.read()
    ok = (rebuilt == original)
    if ok:
        log_success("roundtrip: identical (ok)", quiet)
    else:
        log_warning("roundtrip: mismatch", quiet)
        if verbose:
            import binascii
            a = binascii.hexlify(original[:128]).decode()
            b = binascii.hexlify(rebuilt[:128]).decode()
            log_info(f"head(orig): {a}")
            log_info(f"head(rebl): {b}")
    return ok

def main():
    parser = argparse.ArgumentParser(
        description='divo save file crypto utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  {sys.argv} decrypt save.bin                    # decrypt to hex output
  {sys.argv} decrypt save.bin -f text            # decrypt to text
  {sys.argv} decrypt save.bin -o out.dat --force # decrypt to file
  {sys.argv} dump save.bin decrypted.dat         # simple decrypt to file
  {sys.argv} key save.bin                        # extract key as hex
  {sys.argv} info save.bin -v                    # detailed file info
  {sys.argv} encrypt decrypted.dat -o rebuilt.bin --from-save save.bin   # rebuild identical save
  {sys.argv} roundtrip save.bin                  # verify decrypt→encrypt matches original

version: {__version__}
        """
    )
    parser.add_argument('--version', action='version', version=f'divo-crypto {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='quiet mode (errors only)')
    parser.add_argument('--no-color', action='store_true', help='disable colored output')

    subparsers = parser.add_subparsers(dest='command', help='commands')

    dec_p = subparsers.add_parser('decrypt', help='decrypt save file')
    dec_p.add_argument('input', help='input save file')
    dec_p.add_argument('-o', '--output', help='output file')
    dec_p.add_argument('-f', '--format', choices=['hex', 'hexdump', 'text', 'raw'], default='hex', help='output format')
    dec_p.add_argument('--force', action='store_true', help='overwrite existing files')
    dec_p.add_argument('--no-validate', action='store_true', help='skip data validation')
    dec_p.add_argument('--print-key', action='store_true', help='print extracted key as hex to stdout')

    dump_p = subparsers.add_parser('dump', help='decrypt save file to output file')
    dump_p.add_argument('input', help='input save file')
    dump_p.add_argument('output', help='output file')
    dump_p.add_argument('--force', action='store_true', help='overwrite existing files')

    key_p = subparsers.add_parser('key', help='extract xor key')
    key_p.add_argument('input', help='input save file')
    key_p.add_argument('-o', '--output', help='output key file')
    key_p.add_argument('-f', '--format', choices=['hex', 'hexdump', 'raw'], default='hex', help='output format')
    key_p.add_argument('--force', action='store_true', help='overwrite existing files')

    info_p = subparsers.add_parser('info', help='display save file information')
    info_p.add_argument('input', help='input save file')

    enc_p = subparsers.add_parser('encrypt', help='encrypt decrypted payload into save')
    enc_p.add_argument('payload', help='input decrypted payload (0x574 bytes)')
    enc_p.add_argument('-o', '--output', required=True, help='output save file')
    src = enc_p.add_mutually_exclusive_group(required=True)
    src.add_argument('--key', help='key file (256 bytes)')
    src.add_argument('--from-save', help='extract key from existing save file')
    enc_p.add_argument('--force', action='store_true', help='overwrite existing files')

    rt_p = subparsers.add_parser('roundtrip', help='verify decrypt→encrypt reproduces original')
    rt_p.add_argument('input', help='input save file')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')

    if getattr(args, 'quiet', False) and getattr(args, 'verbose', False):
        log_error("cannot use both --quiet and --verbose")
        return 1

    try:
        if args.command == 'decrypt':
            ok = decrypt_save(
                args.input, args.output, args.format,
                args.verbose, args.quiet,
                getattr(args, 'force', False),
                not getattr(args, 'no_validate', False),
                getattr(args, 'print_key', False)
            )
        elif args.command == 'dump':
            ok = dump_decrypted(args.input, args.output, args.verbose, args.quiet, getattr(args, 'force', False))
        elif args.command == 'key':
            ok = dump_key(args.input, args.output, args.format, args.verbose, args.quiet, getattr(args, 'force', False))
        elif args.command == 'info':
            ok = info_save(args.input, args.verbose, args.quiet)
        elif args.command == 'encrypt':
            ok = encrypt_save(args.payload, args.output, getattr(args, 'key', None), getattr(args, 'from_save', None),
                              getattr(args, 'force', False), args.quiet)
        elif args.command == 'roundtrip':
            ok = roundtrip_verify(args.input, args.verbose, args.quiet)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        log_error("interrupted by user")
        return 130
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

