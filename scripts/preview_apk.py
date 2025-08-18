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
        """load pak file, return success"""
        try:
            magic = file_obj.read(len(self.MAGIC_NUMBER))
            if magic != self.MAGIC_NUMBER:
                print(
                    f"error: invalid magic number, got {magic.hex()}", file=sys.stderr
                )
                return False

            # read header
            header_data = file_obj.read(8)
            if len(header_data) != 8:
                print("error: truncated header", file=sys.stderr)
                return False

            file_table_offset, self.file_count = struct.unpack("<II", header_data)

            if self.file_count > 10000:  # sanity check
                print(
                    f"error: suspicious file count {self.file_count}", file=sys.stderr
                )
                return False

            # read cipher table
            self.cipher_table = file_obj.read(self.CIPHER_TABLE_SIZE)
            if len(self.cipher_table) != self.CIPHER_TABLE_SIZE:
                print("error: truncated cipher table", file=sys.stderr)
                return False

            # read file table
            file_obj.seek(file_table_offset, 0)

            for i in range(self.file_count):
                entry_data = file_obj.read(self.TABLE_ENTRY_SIZE)
                if len(entry_data) != self.TABLE_ENTRY_SIZE:
                    print(f"error: truncated entry {i}", file=sys.stderr)
                    return False

                decrypted = self._decipher(entry_data, i * self.TABLE_ENTRY_SIZE)
                filename, offset, size = self._unpack_table_entry(decrypted)

                if filename and offset > 0 and size > 0:
                    self.file_table[filename] = pak_entry(offset, size)

            return True

        except (struct.error, IOError, OSError) as e:
            print(f"error loading pak: {e}", file=sys.stderr)
            return False

    def _decipher(self, chunk: bytes, offset: int) -> bytes:
        """decrypt chunk using xor cipher"""
        return bytes(
            chunk[i] ^ self.cipher_table[(i + offset) % self.CIPHER_TABLE_SIZE]
            for i in range(len(chunk))
        )

    def _unpack_table_entry(self, entry: bytes) -> Tuple[str, int, int]:
        """unpack file table entry"""
        filename_bytes, offset, size, _ = struct.unpack("<64sIII", entry)
        filename = filename_bytes.rstrip(b"\x00").decode("ascii", errors="ignore")
        return filename, offset, size

    def extract_file(self, file_obj, file_name: str) -> Optional[bytes]:
        """extract file by name, return data or None"""
        if file_name not in self.file_table:
            print(f"error: file '{file_name}' not found", file=sys.stderr)
            return None

        entry = self.file_table[file_name]
        try:
            file_obj.seek(entry.offset, 0)
            data = file_obj.read(entry.size)
            if len(data) != entry.size:
                print(f"error: truncated read for '{file_name}'", file=sys.stderr)
                return None
            return data
        except (IOError, OSError) as e:
            print(f"error reading '{file_name}': {e}", file=sys.stderr)
            return None

    def list_files(self) -> Dict[str, pak_entry]:
        """return file table"""
        return self.file_table.copy()


def main() -> int:
    if len(sys.argv) < 2:
        print(
            f"usage: {Path(sys.argv[0]).name} <pak_file> [file_name]", file=sys.stderr
        )
        return 1

    pak_path = Path(sys.argv[1])
    if not pak_path.exists():
        print(f"error: {pak_path} not found", file=sys.stderr)
        return 1

    try:
        with open(pak_path, "rb") as fin:
            pak = pak_parser()
            if not pak.load(fin):
                return 1

            if len(sys.argv) == 2:
                # list files
                files = pak.list_files()
                print(f"found {len(files)} files:")
                for name, entry in files.items():
                    print(f"  {name:<40} {entry.offset:>8x} {entry.size:>8}")
            else:
                # extract specific file
                file_name = sys.argv[2]
                data = pak.extract_file(fin, file_name)
                if data is None:
                    return 1
                sys.stdout.buffer.write(data)

            return 0

    except (IOError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
