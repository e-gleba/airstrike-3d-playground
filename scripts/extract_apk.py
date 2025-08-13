#!/usr/bin/env python3

import sys
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class pak_entry:
    offset: int
    size: int


class pak_parser:
    MAGIC_NUMBER = b"\x00\x00\x80\x3f\x99\x99\x00\x00"
    TABLE_ENTRY_SIZE = 76
    CIPHER_TABLE_SIZE = 1024

    def __init__(self):
        self.file_count = 0
        self.cipher_table = b""
        self.file_table: Dict[str, pak_entry] = {}

    def load(self, file_obj) -> bool:
        try:
            magic = file_obj.read(len(self.MAGIC_NUMBER))
            if magic != self.MAGIC_NUMBER:
                print(f"error: invalid magic number", file=sys.stderr)
                return False

            header_data = file_obj.read(8)
            if len(header_data) != 8:
                print("error: truncated header", file=sys.stderr)
                return False

            file_table_offset, self.file_count = struct.unpack("<II", header_data)
            self.cipher_table = file_obj.read(self.CIPHER_TABLE_SIZE)

            file_obj.seek(file_table_offset, 0)

            for i in range(self.file_count):
                entry_data = file_obj.read(self.TABLE_ENTRY_SIZE)
                if len(entry_data) != self.TABLE_ENTRY_SIZE:
                    return False

                decrypted = self._decipher(entry_data, i * self.TABLE_ENTRY_SIZE)
                filename, offset, size = self._unpack_table_entry(decrypted)

                if filename and offset > 0 and size > 0:
                    # normalize path separators
                    filename = filename.replace("\\", "/")
                    self.file_table[filename] = pak_entry(offset, size)

            return True
        except Exception as e:
            print(f"error loading pak: {e}", file=sys.stderr)
            return False

    def _decipher(self, chunk: bytes, offset: int) -> bytes:
        return bytes(
            chunk[i] ^ self.cipher_table[(i + offset) % self.CIPHER_TABLE_SIZE]
            for i in range(len(chunk))
        )

    def _unpack_table_entry(self, entry: bytes) -> Tuple[str, int, int]:
        filename_bytes, offset, size, _ = struct.unpack("<64sIII", entry)
        filename = filename_bytes.rstrip(b"\x00").decode("ascii", errors="ignore")
        return filename, offset, size

    def extract_all(self, file_obj, output_dir: Path) -> int:
        """extract all files to output directory"""
        extracted = 0
        failed = 0

        for filename, entry in self.file_table.items():
            output_path = output_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_obj.seek(entry.offset, 0)
                data = file_obj.read(entry.size)

                if len(data) != entry.size:
                    print(f"warning: truncated read for {filename}", file=sys.stderr)
                    failed += 1
                    continue

                output_path.write_bytes(data)
                extracted += 1

                if extracted % 100 == 0:
                    print(f"extracted {extracted}/{len(self.file_table)} files")

            except (IOError, OSError) as e:
                print(f"error extracting {filename}: {e}", file=sys.stderr)
                failed += 1

        return failed


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <pak_file>", file=sys.stderr)
        return 1

    pak_path = Path(sys.argv[1])
    if not pak_path.exists():
        print(f"error: {pak_path} not found", file=sys.stderr)
        return 1

    output_dir = Path.cwd() / pak_path.stem
    output_dir.mkdir(exist_ok=True)

    try:
        with open(pak_path, "rb") as fin:
            pak = pak_parser()
            if not pak.load(fin):
                return 1

            print(f"extracting {len(pak.file_table)} files to {output_dir}/")
            failed = pak.extract_all(fin, output_dir)

            if failed:
                print(f"extraction completed with {failed} failures", file=sys.stderr)
                return 1
            else:
                print("extraction completed successfully")
                return 0

    except (IOError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
