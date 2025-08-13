#!/usr/bin/env python3

import sys
import struct
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class pack_entry:
    name: str
    data: bytes
    offset: int = 0


class apk_packer:
    MAGIC_NUMBER = b"\x00\x00\x80\x3f\x99\x99\x00\x00"
    TABLE_ENTRY_SIZE = 76
    CIPHER_TABLE_SIZE = 1024
    MAX_FILENAME_SIZE = 64

    def __init__(self):
        self.entries: List[pack_entry] = []
        self.cipher_table = self._generate_cipher_table()

    def _generate_cipher_table(self) -> bytes:
        """generate 1kb cipher table - use predictable pattern for compatibility"""
        return bytes((i * 17 + 42) % 256 for i in range(self.CIPHER_TABLE_SIZE))

    def add_directory(self, dir_path: Path, base_path: Path = None) -> bool:
        """recursively add directory contents"""
        if base_path is None:
            base_path = dir_path

        try:
            for item in dir_path.iterdir():
                if item.is_file():
                    rel_path = item.relative_to(base_path)
                    # convert unix paths to windows format for compatibility
                    pak_name = str(rel_path).replace("/", "\\")

                    if (
                        len(pak_name.encode("ascii", errors="ignore"))
                        > self.MAX_FILENAME_SIZE - 1
                    ):
                        print(
                            f"warning: filename too long, skipping {pak_name}",
                            file=sys.stderr,
                        )
                        continue

                    try:
                        data = item.read_bytes()
                        self.entries.append(pack_entry(pak_name, data))
                    except (IOError, OSError) as e:
                        print(f"error reading {item}: {e}", file=sys.stderr)
                        return False

                elif item.is_dir():
                    if not self.add_directory(item, base_path):
                        return False

            return True

        except (IOError, OSError) as e:
            print(f"error scanning {dir_path}: {e}", file=sys.stderr)
            return False

    def _calculate_offsets(self) -> None:
        """calculate file data offsets"""
        # header: magic(8) + table_offset(4) + file_count(4) + cipher_table(1024)
        current_offset = 8 + 4 + 4 + self.CIPHER_TABLE_SIZE

        for entry in self.entries:
            entry.offset = current_offset
            current_offset += len(entry.data)

    def _cipher_entry(self, data: bytes, table_offset: int) -> bytes:
        """encrypt file table entry using xor cipher"""
        return bytes(
            data[i] ^ self.cipher_table[(i + table_offset) % self.CIPHER_TABLE_SIZE]
            for i in range(len(data))
        )

    def _pack_entry(self, entry: pack_entry) -> bytes:
        """pack file table entry to 76 bytes"""
        name_bytes = entry.name.encode("ascii", errors="ignore")[
            : self.MAX_FILENAME_SIZE - 1
        ]
        name_padded = name_bytes.ljust(self.MAX_FILENAME_SIZE, b"\x00")

        return struct.pack(
            "<64sIII", name_padded, entry.offset, len(entry.data), 0
        )  # unknown field, always 0

    def write_apk(self, output_path: Path) -> bool:
        """write packed apk file"""
        if not self.entries:
            print("error: no files to pack", file=sys.stderr)
            return False

        self._calculate_offsets()

        # calculate file table offset (after header + cipher + all file data)
        file_table_offset = (
            8 + 4 + 4 + self.CIPHER_TABLE_SIZE + sum(len(e.data) for e in self.entries)
        )

        try:
            with open(output_path, "wb") as f:
                # write header
                f.write(self.MAGIC_NUMBER)
                f.write(struct.pack("<II", file_table_offset, len(self.entries)))
                f.write(self.cipher_table)

                # write file data
                for entry in self.entries:
                    f.write(entry.data)

                # write encrypted file table
                for i, entry in enumerate(self.entries):
                    entry_data = self._pack_entry(entry)
                    encrypted = self._cipher_entry(
                        entry_data, i * self.TABLE_ENTRY_SIZE
                    )
                    f.write(encrypted)

            return True

        except (IOError, OSError) as e:
            print(f"error writing {output_path}: {e}", file=sys.stderr)
            return False


def main() -> int:
    if len(sys.argv) != 3:
        print(
            f"usage: {Path(sys.argv[0]).name} <input_dir> <output.apk>", file=sys.stderr
        )
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"error: {input_path} not found", file=sys.stderr)
        return 1

    if not input_path.is_dir():
        print(f"error: {input_path} is not a directory", file=sys.stderr)
        return 1

    packer = apk_packer()

    print(f"scanning {input_path}")
    if not packer.add_directory(input_path):
        return 1

    print(f"packing {len(packer.entries)} files to {output_path}")
    if not packer.write_apk(output_path):
        return 1

    file_size = output_path.stat().st_size
    print(f"created {output_path} ({file_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
