# airstrike-re

https://www.pcgamingwiki.com/wiki/AirStrike_2

<div align="center">
   
![image](https://github.com/user-attachments/assets/770024d0-cebb-4497-b0af-4ee7d84ffeff)

![image](https://github.com/user-attachments/assets/8a3a1a78-8d3a-4f00-ab3d-cdb11c06cab4)
</div>


My nostalgic journey into reverse engineering Airstrike 3D - the first PC game that captured my imagination as a kid. This repository contains tools and research for understanding the game's internals.

## Overview

This is a personal project aimed at reverse engineering Airstrike 3D, with the ultimate goal of either recreating it in modern C++/Vulkan/SDL or reimagining it in Godot. Because sometimes you need to understand the past to build the future.

## Tools

| Tool | Purpose |
|------|---------|
| PEiD | Binary analysis and packer detection |
| GAUP Plugin | Archive extraction and resource analysis |

## Structure

```
.
├── tools/                    # RE toolchain
│   ├── PEiD-0.95/           # For binary analysis
│   │   ├── plugins/         # Analysis plugins
│   │   └── pluginsdk/      # Development kit
│   └── wcx_gaup/           # Archive extractor
└── docs/                    # Research notes (TBD)
```

## Planned Stages

1. **Binary Analysis**
   - Identify packers/protections
   - Locate entry points
   - Map basic code structure

2. **Resource Extraction**
   - Extract game assets
   - Analyze file formats
   - Document resource structure

3. **Modern Recreation**
   - Either C++/SDL/Vulkan implementation
   - Or Godot Engine reimagining
   - Focus on core gameplay mechanics

## Development Notes

This is a long-term research project. The goal isn't just to recreate the game, but to understand how games were built in that era. All findings will be documented for educational purposes.

## License

MIT - Because knowledge should be free, just like the joy of playing games.

## Acknowledgments

To that old PC that could barely run the game but somehow made it magical anyway.
