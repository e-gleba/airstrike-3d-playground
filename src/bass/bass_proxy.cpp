// bass_overlay.cpp
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <GL/gl.h>
#include <cstdio>
#include <thread>
#include <atomic>
#include <cstdarg>
#include "imgui.h"
#include "backends/imgui_impl_win32.h"
#include "backends/imgui_impl_opengl2.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND, UINT, WPARAM, LPARAM);

using WglSwap_t = BOOL(WINAPI*)(HDC);
static WglSwap_t        real_wglSwap    = nullptr;
static HWND             game_window     = nullptr;
static WNDPROC          orig_wnd_proc   = nullptr;
static std::atomic<bool> imgui_ready    = false;
static std::atomic<bool> shutting_down  = false;
static BYTE             original_bytes[5] = {0};

// Console logger
static void InitConsole() {
    AllocConsole();
    freopen("CONOUT$", "w", stdout);
    SetConsoleTitleA("BASS Overlay Debug");
}
static void Log(const char* fmt, ...) {
    char buf[256];
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    printf("%s", buf);
    fflush(stdout);
}

// WndProc hook
LRESULT CALLBACK WndProcHook(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (!shutting_down.load())
        ImGui_ImplWin32_WndProcHandler(hwnd, msg, wp, lp);
    return CallWindowProc(orig_wnd_proc, hwnd, msg, wp, lp);
}

// Hooked wglSwapBuffers
BOOL WINAPI SwapBuffersHook(HDC hdc) {
    // Ensure we get the real window once a context exists
    static bool window_found = false;
    if (!window_found && wglGetCurrentContext()) {
        HDC curr_dc = wglGetCurrentDC();
        game_window = WindowFromDC(curr_dc);
        Log("Found game window HWND=%p\n", game_window);
        if (game_window) {
            orig_wnd_proc = (WNDPROC)SetWindowLongPtr(
                game_window, GWLP_WNDPROC,
                (LONG_PTR)WndProcHook);
            Log("WndProc hooked orig=%p\n", orig_wnd_proc);
            window_found = true;
        }
    }

    if (!imgui_ready.load() && window_found) {
        Log("Initializing ImGui GL2\n");
        ImGui::CreateContext();
        ImGui_ImplWin32_Init(game_window);
        ImGui_ImplOpenGL2_Init();
        ImGui::StyleColorsDark();
        imgui_ready.store(true);
    }

    if (imgui_ready.load()) {
        ImGui_ImplOpenGL2_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();
        ImGui::Begin("BASS Control");
        ImGui::Text("Bass DLL Proxy Running");
        ImGui::Separator();
        ImGui::Text("FPS: %.1f", ImGui::GetIO().Framerate);
        if (ImGui::Button("Exit")) {
            Log("Exit pressed\n");
            shutting_down.store(true);
            PostQuitMessage(0);
        }
        ImGui::End();
        ImGui::Render();
        ImGui_ImplOpenGL2_RenderDrawData(ImGui::GetDrawData());
    }

    return real_wglSwap(hdc);
}

// Install hook on wglSwapBuffers
static bool InstallHook() {
    HMODULE mod = GetModuleHandleA("opengl32.dll");
    if (!mod) { Log("opengl32.dll not loaded\n"); return false; }
    void* addr = (void*)GetProcAddress(mod, "wglSwapBuffers");
    if (!addr) { Log("wglSwapBuffers not found\n"); return false; }

    DWORD old;
    VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
    memcpy(original_bytes, addr, 5);

    intptr_t rel = (BYTE*)SwapBuffersHook - ((BYTE*)addr + 5);
    BYTE patch[5] = { 0xE9 };
    memcpy(patch+1, &rel, 4);
    memcpy(addr, patch, 5);
    VirtualProtect(addr, 5, old, &old);

    BYTE* tramp = (BYTE*)VirtualAlloc(nullptr, 16, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(tramp, original_bytes, 5);
    tramp[5] = 0xE9;
    intptr_t back = ((BYTE*)addr + 5) - (tramp + 10);
    memcpy(tramp+6, &back, 4);
    real_wglSwap = (WglSwap_t)tramp;

    Log("Hook installed on wglSwapBuffers\n");
    return true;
}

// Remove hook & cleanup
static void RemoveHook() {
    shutting_down.store(true);
    Sleep(100);
    if (orig_wnd_proc && game_window) {
        SetWindowLongPtr(game_window, GWLP_WNDPROC, (LONG_PTR)orig_wnd_proc);
    }
    HMODULE mod = GetModuleHandleA("opengl32.dll");
    if (mod) {
        void* addr = (void*)GetProcAddress(mod, "wglSwapBuffers");
        DWORD old;
        VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
        memcpy(addr, original_bytes, 5);
        VirtualProtect(addr, 5, old, &old);
    }
    if (real_wglSwap) {
        VirtualFree((LPVOID)real_wglSwap, 0, MEM_RELEASE);
    }
    if (imgui_ready.load()) {
        ImGui_ImplOpenGL2_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    Log("Cleanup done\n");
}

// Threaded initialization
static void InitThread() {
    InitConsole();
    Log("InitThread starting\n");
    if (!InstallHook()) {
        Log("InstallHook failed\n");
    }
}

extern "C" BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls((HMODULE)&DllMain);
        std::thread(InitThread).detach();
    } else if (reason == DLL_PROCESS_DETACH) {
        RemoveHook();
    }
    return TRUE;
}
