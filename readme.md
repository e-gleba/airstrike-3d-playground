# AirStrike 3D Reverse Engineering

**Reverse engineering the AirStrike 3D game series**

[PCGamingWiki](https://www.pcgamingwiki.com/wiki/AirStrike_2) -  [Original Game](https://en.wikipedia.org/wiki/AirStrike_3D)

## 🎮 About

My nostalgic journey into reverse engineering AirStrike 3D - the first PC game that captured my imagination as a kid. This repository contains tools and research for understanding the game's internals.

## 🔧 Tools

### APK Archive Extraction

```bash
# Extract game assets from encrypted .apk archives
python extract_apk.py pak0.apk        # Extracts all files
python pack_apk.py extracted_dir/ new.apk  # Repack modified assets
```

### Audio Conversion

```bash
# Convert MO3 tracker modules to standard audio
sudo dnf install libopenmpt openmpt123
openmpt123 --render file.mo3 --output file.wav
```

### Graphics Viewing

```bash
# Best TGA texture viewer for Linux
# https://github.com/bluescan/tacentview
tacentview texture.tga
```

## 🐧 Linux Compatibility

### Running via Steam Proton (Fedora + AMD GPU)

```bash
# Fix OpenGL extension issues for old games
MESA_EXTENSION_MAX_YEAR=2003 %command%
```

Add this to the game's launch options in Steam.

## 📋 Technical Notes

- **Archive Format:** Custom encrypted APK containers (not Android APK)
- **Executable:** ASProtect v1.0 packed (detected via YARA rules)
- **Assets:** TGA textures, MDL 3D models, MO3 audio modules
- **Encryption:** XOR cipher with 1024-byte key table

## 🚀 Quick Start

1. Clone this repository
2. Extract game assets: `python extract_pak.py /path/to/pak0.apk`
3. Browse extracted files in the created directory
4. Convert audio files as needed

## Ghidra project
as project uses asprotect ive decided on linux usin simple debugger just walk until get somekind of loop. The game seems to be unpack itself creating some thread, so even the debugger deataches at some moment in ntdll magic, so we need just to pause at any moment and get the address of the desired function. The next stem is usin xbg with dumpex pluging dump with the addres of main loop function. And thats all, the game weights 31.2 mbs, in ghidra project ive marked some of the interesting places like loading models, working with saves, so u will need just to clone and open with ghidra the project and explore yourself! Maybe some time someone will rever it xD

## ⚖️ Legal

Educational and preservation purposes only. Respect original copyrights.

## 📄 License

MIT - Because knowledge should be free, just like the joy of playing games.

## 🙏 Acknowledgments

To that old PC that could barely run the game but somehow made it magical anyway.
