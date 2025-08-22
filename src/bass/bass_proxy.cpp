// bass_overlay.cpp
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <psapi.h>
#include <GL/gl.h>
#include <cmath>
#include <cstdio>
#include <thread>
#include <atomic>
#include <vector>
#include "imgui.h"
#include "backends/imgui_impl_win32.h"
#include "backends/imgui_impl_opengl3.h"

// ImGui Win32 handler
extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND, UINT, WPARAM, LPARAM);

using wgl_swap_t = BOOL (WINAPI*)(HDC);
static wgl_swap_t        real_wgl_swap    = nullptr;
static HWND              game_window      = nullptr;
static WNDPROC           orig_wnd_proc    = nullptr;
static std::atomic<bool> imgui_ready      = false;
static std::atomic<bool> shutting_down    = false;
static BYTE              original_bytes[5];

// Overlay state
static std::atomic<bool> overlay_visible{ true };
static bool              dark_theme      = true;
static ImVec4            clear_color     = ImVec4(0, 0, 0, 0);
static bool              enable_clear    = false;
static bool              wireframe       = false;
static bool              invert_colors   = false;
static float             brightness      = 1.0f;

// Logging
static std::vector<const char*> log_lines;
static void log_msg(const char* fmt, ...) {
    static char buf[128];
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, 128, fmt, ap);
    va_end(ap);
    log_lines.push_back(_strdup(buf));
    if (log_lines.size() > 8) { free((void*)log_lines.front()); log_lines.erase(log_lines.begin()); }
}

// Forward
static void draw_overlay();
static void init_console();
static bool install_hook();
static void remove_hooks();

// Init console
static void init_console() {
    AllocConsole();
    freopen("CONOUT$", "w", stdout);
    SetConsoleTitleA("Overlay Debug");
}

// WndProc hook
LRESULT CALLBACK wnd_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (!shutting_down.load())
        ImGui_ImplWin32_WndProcHandler(h, m, w, l);
    return CallWindowProc(orig_wnd_proc, h, m, w, l);
}

// SwapBuffers hook
BOOL WINAPI hook_swap(HDC dc) {
    static bool initialized = false;
    if (!initialized && wglGetCurrentContext()) {
        game_window = WindowFromDC(wglGetCurrentDC());
        orig_wnd_proc = (WNDPROC)SetWindowLongPtr(game_window, GWLP_WNDPROC, (LONG_PTR)wnd_proc);
        initialized = true;
    }
    if (initialized && !imgui_ready.load()) {
        ImGui::CreateContext();
        ImGui_ImplWin32_Init(game_window);
        ImGui_ImplOpenGL3_Init("#version 330 core");
        imgui_ready.store(true);
    }
    if (imgui_ready.load()) {
        if (GetAsyncKeyState(VK_INSERT) & 1) overlay_visible = !overlay_visible;
        if (overlay_visible.load()) draw_overlay();
    }
    return real_wgl_swap(dc);
}

// Install hook
static bool install_hook() {
    HMODULE m = GetModuleHandleA("opengl32.dll");
    if (!m) return false;
    BYTE* addr = (BYTE*)GetProcAddress(m, "wglSwapBuffers");
    if (!addr) return false;
    DWORD old; VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
    memcpy(original_bytes, addr, 5);
    intptr_t rel = (BYTE*)hook_swap - (addr + 5);
    addr[0] = 0xE9; memcpy(addr + 1, &rel, 4);
    VirtualProtect(addr, 5, old, &old);
    BYTE* tramp = (BYTE*)VirtualAlloc(nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(tramp, original_bytes, 5);
    tramp[5] = 0xE9; intptr_t back = (addr + 5) - (tramp + 10);
    memcpy(tramp + 6, &back, 4);
    real_wgl_swap = (wgl_swap_t)tramp;
    log_msg("hook installed");
    return true;
}

// Remove hook
static void remove_hooks() {
    shutting_down = true;
    Sleep(100);
    if (orig_wnd_proc)
        SetWindowLongPtr(game_window, GWLP_WNDPROC, (LONG_PTR)orig_wnd_proc);
    HMODULE m = GetModuleHandleA("opengl32.dll");
    if (m) {
        BYTE* addr = (BYTE*)GetProcAddress(m, "wglSwapBuffers");
        DWORD old; VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
        memcpy(addr, original_bytes, 5);
        VirtualProtect(addr, 5, old, &old);
    }
    if (real_wgl_swap) VirtualFree((LPVOID)real_wgl_swap, 0, MEM_RELEASE);
    if (imgui_ready.load()) {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    log_msg("cleanup done");
}

// Init thread
static void init_thread() {
    init_console();
    install_hook();
}

// DllMain
extern "C" BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls((HMODULE)&DllMain);
        std::thread(init_thread).detach();
    } else if (reason == DLL_PROCESS_DETACH) {
        remove_hooks();
    }
    return TRUE;
}

// Draw overlay
static void draw_overlay() {
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplWin32_NewFrame();
    ImGui::NewFrame();

    if (dark_theme) ImGui::StyleColorsDark();
    else           ImGui::StyleColorsLight();

    ImGui::Begin("Overlay", nullptr, ImGuiWindowFlags_AlwaysAutoResize);

    ImGui::Checkbox("Clear Screen", &enable_clear);
    ImGui::SameLine(); ImGui::ColorEdit3("Clear Color", (float*)&clear_color);

    ImGui::Checkbox("Wireframe", &wireframe);
    glPolygonMode(GL_FRONT_AND_BACK, wireframe ? GL_LINE : GL_FILL);

    ImGui::Checkbox("Invert Colors", &invert_colors);
    if (invert_colors) { glEnable(GL_COLOR_LOGIC_OP); glLogicOp(GL_COPY_INVERTED); }
    else glDisable(GL_COLOR_LOGIC_OP);

    ImGui::SliderFloat("Brightness", &brightness, 0.5f, 2.0f, "%.2f");

    ImGui::Checkbox("Dark Theme", &dark_theme);

    ImGui::Separator();
    ImGui::Text("Log:");
    for (auto s : log_lines)
        ImGui::BulletText("%s", s);

    if (ImGui::Button("Exit"))
        PostQuitMessage(0);

    ImGui::End();
    ImGui::Render();

    if (enable_clear) {
        glClearColor(clear_color.x * brightness,
                     clear_color.y * brightness,
                     clear_color.z * brightness,
                     clear_color.w);
        glClear(GL_COLOR_BUFFER_BIT);
    }

    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}
