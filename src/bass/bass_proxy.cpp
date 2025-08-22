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
#include "backends/imgui_impl_opengl3.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND, UINT, WPARAM, LPARAM);

using wgl_swap_t = BOOL (WINAPI*)(HDC);
static wgl_swap_t        real_wgl_swap    = nullptr;
static HWND              game_window      = nullptr;
static WNDPROC           orig_wnd_proc    = nullptr;
static std::atomic<bool> imgui_ready      = false;
static std::atomic<bool> shutting_down    = false;
static BYTE              original_bytes[5];

static std::atomic<bool> overlay_visible{true};
static bool              show_demo        = false;
static float             fps_cap          = 0.0f;
static ImVec4            clear_color      = ImVec4(0,0,0,0);
static bool              enable_clear     = false;

static void init_console() {
    AllocConsole();
    freopen("CONOUT$", "w", stdout);
    SetConsoleTitleA("BASS Overlay Debug");
}

static void log_msg(const char* fmt, ...) {
    char buf[256];
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    printf("%s", buf);
    fflush(stdout);
}

LRESULT CALLBACK wnd_proc_hook(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (!shutting_down.load())
        ImGui_ImplWin32_WndProcHandler(hwnd, msg, wp, lp);
    return CallWindowProc(orig_wnd_proc, hwnd, msg, wp, lp);
}

BOOL WINAPI swap_buffers_hook(HDC hdc) {
    static bool window_found = false;
    if (!window_found && wglGetCurrentContext()) {
        HDC curr_dc = wglGetCurrentDC();
        game_window = WindowFromDC(curr_dc);
        log_msg("found hwnd=%p\n", game_window);
        if (game_window) {
            orig_wnd_proc = (WNDPROC)SetWindowLongPtr(
                game_window, GWLP_WNDPROC,
                (LONG_PTR)wnd_proc_hook);
            log_msg("hooked wnd_proc orig=%p\n", orig_wnd_proc);
            window_found = true;
        }
    }

    if (!imgui_ready.load() && window_found) {
        log_msg("init imgui gl3\n");
        ImGui::CreateContext();
        ImGui_ImplWin32_Init(game_window);
        ImGui_ImplOpenGL3_Init("#version 330 core");
        ImGui::StyleColorsDark();
        imgui_ready.store(true);
    }

    if (imgui_ready.load()) {
        if (GetAsyncKeyState(VK_INSERT) & 1)
            overlay_visible.store(!overlay_visible.load());

        if (fps_cap > 0.0f) {
            static double last = ImGui::GetTime();
            double now = ImGui::GetTime();
            double dt = 1.0 / fps_cap;
            if (now - last < dt)
                Sleep(UINT((dt - (now - last)) * 1000));
            last = now;
        }

        if (overlay_visible.load()) {
            ImGui_ImplOpenGL3_NewFrame();
            ImGui_ImplWin32_NewFrame();
            ImGui::NewFrame();

            ImGui::Begin("BASS Overlay", nullptr,
                         ImGuiWindowFlags_NoCollapse | ImGuiWindowFlags_AlwaysAutoResize);
            ImGui::Text("FPS: %.1f", ImGui::GetIO().Framerate);
            ImGui::SliderFloat("FPS Cap", &fps_cap, 0.0f, 240.0f, "%.0f");
            ImGui::ColorEdit3("Clear Color", (float*)&clear_color);
            ImGui::Checkbox("Clear Screen", &enable_clear);
            ImGui::Checkbox("Show Demo", &show_demo);
            ImGui::Separator();
            if (ImGui::Button("Exit")) {
                shutting_down.store(true);
                PostQuitMessage(0);
            }
            ImGui::End();

            if (show_demo)
                ImGui::ShowDemoWindow(&show_demo);

            ImGui::Render();
            glViewport(0, 0,
                       (int)ImGui::GetIO().DisplaySize.x,
                       (int)ImGui::GetIO().DisplaySize.y);
            if (enable_clear) {
                glClearColor(clear_color.x,
                             clear_color.y,
                             clear_color.z,
                             clear_color.w);
                glClear(GL_COLOR_BUFFER_BIT);
            }
            ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        }
    }

    return real_wgl_swap(hdc);
}

static bool install_hook() {
    HMODULE mod = GetModuleHandleA("opengl32.dll");
    if (!mod) { log_msg("no opengl32.dll\n"); return false; }
    void* addr = (void*)GetProcAddress(mod, "wglSwapBuffers");
    if (!addr) { log_msg("no wglSwapBuffers\n"); return false; }

    DWORD old;
    VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
    memcpy(original_bytes, addr, 5);

    intptr_t rel = (BYTE*)swap_buffers_hook - ((BYTE*)addr + 5);
    BYTE patch[5] = { 0xE9 };
    memcpy(patch+1, &rel, 4);
    memcpy(addr, patch, 5);
    VirtualProtect(addr, 5, old, &old);

    BYTE* tramp = (BYTE*)VirtualAlloc(
        nullptr, 16, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(tramp, original_bytes, 5);
    tramp[5] = 0xE9;
    intptr_t back = ((BYTE*)addr + 5) - (tramp + 10);
    memcpy(tramp+6, &back, 4);
    real_wgl_swap = (wgl_swap_t)tramp;

    log_msg("hook installed\n");
    return true;
}

static void remove_hook() {
    shutting_down.store(true);
    Sleep(100);
    if (orig_wnd_proc && game_window)
        SetWindowLongPtr(game_window, GWLP_WNDPROC, (LONG_PTR)orig_wnd_proc);
    HMODULE mod = GetModuleHandleA("opengl32.dll");
    if (mod) {
        void* addr = (void*)GetProcAddress(mod, "wglSwapBuffers");
        DWORD old;
        VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
        memcpy(addr, original_bytes, 5);
        VirtualProtect(addr, 5, old, &old);
    }
    if (real_wgl_swap)
        VirtualFree((LPVOID)real_wgl_swap, 0, MEM_RELEASE);
    if (imgui_ready.load()) {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    log_msg("cleanup done\n");
}

static void init_thread() {
    init_console();
    log_msg("init thread\n");
    if (!install_hook())
        log_msg("install failed\n");
}

extern "C" BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls((HMODULE)&DllMain);
        std::thread(init_thread).detach();
    } else if (reason == DLL_PROCESS_DETACH) {
        remove_hook();
    }
    return TRUE;
}
