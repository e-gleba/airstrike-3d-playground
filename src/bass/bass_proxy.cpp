// bass_proxy.cpp – zero-logic forwarder for vintage BASS.DLL
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string_view>

#include <SDL3/SDL.h>
#include <cstdlib>

int main_loop()
{
    if (!SDL_Init(SDL_INIT_EVENTS | SDL_INIT_VIDEO))
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,
                     "SDL_Init failed: %s",
                     SDL_GetError());
        return EXIT_FAILURE;
    }

    struct SDLGuard
    {
        ~SDLGuard() { SDL_Quit(); }
    } sdl_guard;

    if (!SDL_ShowSimpleMessageBox(
            SDL_MESSAGEBOX_INFORMATION,
            "Hello World",
            "!! Your SDL project successfully runs!!",
            nullptr)) // Prefer nullptr over NULL
    {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,
                     "Message box failed: %s",
                     SDL_GetError());
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}

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
    	main_loop();
    return TRUE;
}

