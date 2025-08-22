# AirStrike3D Source Code (`src/`)

This directory contains the C++ implementation of a **bass.dll proxy** for AirStrike 3D game modification and runtime analysis.

## What is a DLL Proxy?

A DLL proxy replaces the game's original `bass.dll` (BASS audio library) while forwarding all legitimate audio API calls to the renamed original library. This technique allows code injection without modifying the game executable directly.

## Architecture

```
Game Process
    ↓ loads bass.dll
Your Proxy DLL
    ↓ forwards BASS_* calls to
bass_real.dll (original BASS library)
    ↓ meanwhile injects
OpenGL hooks + ImGui overlay
```

## Prerequisites

1. **Original BASS Library**  
   - Obtain the original `bass.dll` from the AirStrike 3D installation  
   - Rename it to `bass_real.dll`  
   - Place in `src/bass/bass_real.dll`  

2. **Build Environment**  
   - Windows SDK  
   - MinGW-w64 or Visual Studio  
   - CMake 3.15+  

## Building

From repository root:

```bash
# Follow the main README build instructions
mkdir build && cd build
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
make bass
```

Output:
- `build/bass/bass.dll` - Your proxy DLL  
- Automatically copies `bass_real.dll` for deployment  

## Installation

1. Backup original `bass.dll` in AirStrike 3D directory  
2. Copy your `bass.dll` and `bass_real.dll` to game directory  
3. Launch game - overlay activates automatically  

## Features

- **Runtime Performance Monitoring**: FPS, memory usage, system stats  
- **Visual Effects**: Post-processing shaders (vignette, sepia, scanlines, invert)  
- **Hook Analysis**: Real-time display of active function intercepts  
- **Debug Controls**: Wireframe toggle, clear color, ImGui theming  

## Technical Implementation

- **DLL Export Forwarding**: All BASS audio APIs transparently forwarded  
- **OpenGL Interception**: Hooks `wglSwapBuffers` for frame capture  
- **Framebuffer Objects**: Renders game to texture for post-processing  
- **GLSL Shaders**: Hardware-accelerated visual effects  
- **ImGui Integration**: Immediate-mode GUI overlay system  

## Security Warnings

⚠️ **This is a code injection technique**:
- May trigger antivirus/anti-cheat detection  
- Modifies system DLL behavior at runtime  
- Can cause game instability if incorrectly implemented  
- Educational/research use only  

***

**Note**: This proxy requires the legitimate BASS audio library. Ensure you have proper licensing for any redistributed BASS components.

### fedora linux build using ready toolchain

```bash
cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchains/mingw32.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

