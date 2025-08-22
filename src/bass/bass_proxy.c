/* bass_proxy.c  –  zero-logic proxy: DllMain just loads bass_real.dll */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static HMODULE real;

BOOL APIENTRY DllMain(HINSTANCE, DWORD rc, LPVOID)
{
    if (rc == DLL_PROCESS_ATTACH)
        real = LoadLibraryA("bass_real.dll");   /* original DLL renamed */
    return TRUE;
}

