// bass_proxy.cpp – zero-logic forwarder for vintage BASS.DLL
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string_view>

namespace {
    constexpr std::wstring_view kRealName  = L"bass_real.dll";   // original DLL renamed
    HMODULE                      g_real{};
}

static void ensure_real_loaded() noexcept
{
    if (!g_real)
        g_real = LoadLibraryW(kRealName.data());
}

extern "C"
BOOL APIENTRY DllMain(HINSTANCE /*hMod*/,
                      DWORD      reason,
                      LPVOID     /*reserved*/) noexcept
{
    if (reason == DLL_PROCESS_ATTACH)
        ensure_real_loaded();
    return TRUE;
}

