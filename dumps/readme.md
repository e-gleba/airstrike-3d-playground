# Minimal README: EXE Dumping via GDB

## Purpose

Direct, professional workflow for reverse engineering and binary analysis.  
Covers dump extraction, offset quirks, and memory watch usage.

***

## Steps

### 1. Dumping EXE Memory with GDB

- Attach to the process.
- Break or set a hardware watchpoint:
  ```
  rwatch (int)0x004369f8
  ```
- Dump binary memory:
  ```
  dump binary memory extracted_exe.bin 0x400000 0x404000
  ```

***

### 2. Info Files Extraction

- In GDB, dump the target memory regions that contain the mapped PE/EXE sections.
- Extract structurally important regions (e.g., `.text`, `.data`).  
  Use the `info files` command to see memory mappings and symbol addresses:
  ```
  info files
  ```

- Dump using GDB:
  ```
  dump binary memory section_name.bin  
  ```

***

### 3. Why is 0x400000 Dumped, Not 0x4010000?

- PE (Windows EXE) default ImageBase is **0x400000**.  
- Linux-mapped PE files via Wine/remapping tools or memory loaders often use the same base.
- GDB shows and dumps region starting at **0x400000**, matching the PE image layout.
- If **0x4010000** appears, that’s usually a typo or a misread (PE rarely mapped there).

***

## Turbo Tutorial

```bash
gdb ./target_binary
(gdb) run
(gdb) rwatch (int)0x004369f8
(gdb) info files
(gdb) dump binary memory extracted_exe.bin 0x400000 0x404000
```


