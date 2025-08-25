#include "bass_proxy.h"

#include <thread>

#include <windows.h>

extern "C" bool APIENTRY DllMain(HMODULE, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls((HMODULE)&DllMain);
        std::thread(install_hook).detach();
    }
    else if (reason == DLL_PROCESS_DETACH)
    {
        remove_hooks();
    }
    return true;
}