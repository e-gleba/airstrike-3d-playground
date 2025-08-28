#include "bass_proxy.hpp"

#include <format>
#include <thread>

#include <windows.h>

extern "C" bool APIENTRY DllMain(HMODULE hmodule, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        std::thread(install_hook).detach();
    }
    else if (reason == DLL_PROCESS_DETACH)
    {
        remove_hooks();
    }
    return true;
}
