/*  bass_stub.cpp  ───────────────────────────────────────────────
    Drop-in “no-audio” replacement for vintage (≤2005) bass.dll.

    - Exports every symbol your game requests (see .def file).
    - Implements them as fast one-liners that always “succeed”.
    - Build with MinGW-w64 (32- or 64-bit) and 100 % static link:

       i686-w64-mingw32-g++ -std=c++17 -static -s -shared \
           -o bass.dll bass_stub.cpp bass_stub.def
----------------------------------------------------------------*/
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

/* Old BASS uses these typedefs */
typedef unsigned __int64 QWORD;
typedef DWORD            HCHANNEL;

/* Dummy return helpers */
static constexpr BOOL   OK            = TRUE;
static constexpr DWORD  ZERO_DWORD    = 0;
static constexpr DWORD  DUMMY_HANDLE  = 1;
static constexpr float  ONE_FLOAT     = 1.0f;
static constexpr DWORD  BASS_VERSION  = 0x02020300;   // 2.2.3.0 hex

/* ── Declaration macros – every fn is __stdcall + exported ── */
#define EXP_BOOL(fn)      extern "C" __declspec(dllexport) BOOL   __stdcall fn (...) { return OK; }
#define EXP_DWORD(fn)     extern "C" __declspec(dllexport) DWORD  __stdcall fn (...) { return ZERO_DWORD; }
#define EXP_HANDLE(fn)    extern "C" __declspec(dllexport) DWORD  __stdcall fn (...) { return DUMMY_HANDLE; }
#define EXP_PTR(fn)       extern "C" __declspec(dllexport) void * __stdcall fn (...) { return nullptr; }

/* ── Core functions (custom bodies) ── */
extern "C" {
__declspec(dllexport) DWORD __stdcall BASS_GetVersion()                           { return BASS_VERSION; }
__declspec(dllexport) BOOL  __stdcall BASS_Init        (...)                      { return OK; }
__declspec(dllexport) BOOL  __stdcall BASS_Free        (...)                      { return OK; }
__declspec(dllexport) int   __stdcall BASS_ErrorGetCode(...)                      { return 0; }
__declspec(dllexport) DWORD __stdcall BASS_MusicLoad   (...)                      { return DUMMY_HANDLE; }
}

/* ── Bulk one-line stubs ── */
EXP_BOOL (BASS_Apply3D)
EXP_BOOL (BASS_CDDoor)                   EXP_BOOL (BASS_CDFree)
EXP_PTR  (BASS_CDGetID)                  EXP_DWORD(BASS_CDGetTrackLength)
EXP_DWORD(BASS_CDGetTracks)              EXP_BOOL (BASS_CDInDrive)
EXP_BOOL (BASS_CDInit)                   EXP_BOOL (BASS_CDPlay)

EXP_DWORD(BASS_ChannelBytes2Seconds)     EXP_BOOL (BASS_ChannelGet3DAttributes)
EXP_BOOL (BASS_ChannelGet3DPosition)     EXP_DWORD(BASS_ChannelGetAttributes)
EXP_DWORD(BASS_ChannelGetData)           EXP_DWORD(BASS_ChannelGetEAXMix)
EXP_DWORD(BASS_ChannelGetFlags)          EXP_DWORD(BASS_ChannelGetLevel)
EXP_DWORD(BASS_ChannelGetPosition)       EXP_BOOL (BASS_ChannelIsActive)
EXP_BOOL (BASS_ChannelIsSliding)         EXP_BOOL (BASS_ChannelPause)
EXP_BOOL (BASS_ChannelRemoveDSP)         EXP_BOOL (BASS_ChannelRemoveFX)
EXP_BOOL (BASS_ChannelRemoveLink)        EXP_BOOL (BASS_ChannelRemoveSync)
EXP_BOOL (BASS_ChannelResume)            EXP_DWORD(BASS_ChannelSeconds2Bytes)
EXP_BOOL (BASS_ChannelSet3DAttributes)   EXP_BOOL (BASS_ChannelSet3DPosition)
EXP_BOOL (BASS_ChannelSetAttributes)     EXP_BOOL (BASS_ChannelSetDSP)
EXP_BOOL (BASS_ChannelSetEAXMix)         EXP_BOOL (BASS_ChannelSetFX)
EXP_BOOL (BASS_ChannelSetLink)           EXP_BOOL (BASS_ChannelSetPosition)
EXP_BOOL (BASS_ChannelSetSync)           EXP_BOOL (BASS_ChannelSlideAttributes)
EXP_BOOL (BASS_ChannelStop)

EXP_BOOL (BASS_FXGetParameters)          EXP_BOOL (BASS_FXSetParameters)
EXP_BOOL (BASS_Get3DFactors)             EXP_BOOL (BASS_Get3DPosition)
EXP_DWORD(BASS_GetCPU)                   EXP_PTR  (BASS_GetDSoundObject)
EXP_PTR  (BASS_GetDeviceDescription)     EXP_BOOL (BASS_GetEAXParameters)
EXP_BOOL (BASS_GetGlobalVolumes)         EXP_PTR  (BASS_GetInfo)
EXP_DWORD(BASS_GetVolume)

EXP_BOOL (BASS_MusicFree)                EXP_DWORD(BASS_MusicGetChannelVol)
EXP_DWORD(BASS_MusicGetLength)           EXP_PTR  (BASS_MusicGetName)
EXP_BOOL (BASS_MusicPlay)                EXP_BOOL (BASS_MusicPlayEx)
EXP_BOOL (BASS_MusicPreBuf)              EXP_BOOL (BASS_MusicSetAmplify)
EXP_BOOL (BASS_MusicSetChannelVol)       EXP_BOOL (BASS_MusicSetPanSep)
EXP_BOOL (BASS_MusicSetPositionScaler)

EXP_BOOL (BASS_Pause)

EXP_BOOL (BASS_RecordFree)               EXP_PTR  (BASS_RecordGetDeviceDescription)
EXP_PTR  (BASS_RecordGetInfo)            EXP_DWORD(BASS_RecordGetInput)
EXP_PTR  (BASS_RecordGetInputName)       EXP_BOOL (BASS_RecordInit)
EXP_BOOL (BASS_RecordSetInput)           EXP_HANDLE(BASS_RecordStart)

EXP_HANDLE(BASS_SampleCreate)            EXP_BOOL (BASS_SampleCreateDone)
EXP_BOOL (BASS_SampleFree)               EXP_BOOL (BASS_SampleGetInfo)
EXP_HANDLE(BASS_SampleLoad)              EXP_HANDLE(BASS_SamplePlay)
EXP_HANDLE(BASS_SamplePlay3D)            EXP_HANDLE(BASS_SamplePlay3DEx)
EXP_HANDLE(BASS_SamplePlayEx)            EXP_BOOL (BASS_SampleSetInfo)
EXP_BOOL (BASS_SampleStop)

EXP_BOOL (BASS_Set3DAlgorithm)           EXP_BOOL (BASS_Set3DFactors)
EXP_BOOL (BASS_Set3DPosition)            EXP_BOOL (BASS_SetBufferLength)
EXP_BOOL (BASS_SetCLSID)                 EXP_BOOL (BASS_SetEAXParameters)
EXP_BOOL (BASS_SetGlobalVolumes)         EXP_BOOL (BASS_SetLogCurves)
EXP_BOOL (BASS_SetNetConfig)
extern "C" __declspec(dllexport) BOOL __stdcall BASS_SetVolume(...) { return OK; }

EXP_BOOL (BASS_Start)                    EXP_BOOL (BASS_Stop)

EXP_HANDLE(BASS_StreamCreate)            EXP_HANDLE(BASS_StreamCreateFile)
EXP_HANDLE(BASS_StreamCreateURL)         EXP_BOOL (BASS_StreamFree)
EXP_DWORD (BASS_StreamGetFilePosition)   EXP_DWORD(BASS_StreamGetLength)
EXP_PTR  (BASS_StreamGetTags)            EXP_BOOL (BASS_StreamPlay)
EXP_BOOL (BASS_StreamPreBuf)

EXP_BOOL (BASS_Update)

/* Trivial DllMain */
BOOL APIENTRY DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }

