#define WIN32_LEAN_AND_MEAN

#include "backends/imgui_impl_opengl3.h"
#include "backends/imgui_impl_win32.h"
#include "imgui.h"

#include <GL/gl.h>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cpuid.h>
#include <psapi.h>
#include <string>
#include <thread>
#include <vector>
#include <windows.h>

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND,
                                                             UINT,
                                                             WPARAM,
                                                             LPARAM);

using wgl_swap_t                       = BOOL(WINAPI*)(HDC);
static wgl_swap_t        real_wgl_swap = nullptr;
static HWND              game_window   = nullptr;
static WNDPROC           orig_wnd_proc = nullptr;
static std::atomic<bool> imgui_ready   = false;
static std::atomic<bool> shutting_down = false;
static BYTE              original_bytes[5];

// Overlay settings
static bool   dark_theme    = true;
static ImVec4 clear_color   = ImVec4(0, 0, 0, 0);
static bool   enable_clear  = false;
static bool   wireframe     = false;

// Hook info
struct hook_entry
{
    std::string module, function;
    void *      original_addr, *hook_addr;
    bool        active;
};
static std::vector<hook_entry> g_hooks;

// System info
struct system_info
{
    std::string cpu_name, os_version;
    uint64_t    total_ram;
} g_sysinfo;

// Logging
static std::vector<std::string> log_lines;
static void                     log_msg(const char* fmt, ...)
{
    char    buf[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, 256, fmt, ap);
    va_end(ap);
    auto t =
        std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    char ts[16];
    strftime(ts, 16, "%H:%M:%S", localtime(&t));
    log_lines.emplace_back(ts + std::string(" ") + buf);
    if (log_lines.size() > 50)
        log_lines.erase(log_lines.begin());
}

// Forwards
static void draw_overlay();

// Init system info
static void init_system_info()
{
    char     brand[49] = { 0 };
    unsigned regs[4];
    for (unsigned i = 0; i < 3; ++i)
    {
        __get_cpuid(0x80000002 + i, regs, regs + 1, regs + 2, regs + 3);
        memcpy(brand + 16 * i, regs, 16);
    }
    g_sysinfo.cpu_name = brand;
    MEMORYSTATUSEX ms{ sizeof(ms) };
    GlobalMemoryStatusEx(&ms);
    g_sysinfo.total_ram = ms.ullTotalPhys / (1024 * 1024);
    OSVERSIONINFOA osv{ sizeof(osv) };
    GetVersionExA(&osv);
    g_sysinfo.os_version = "Windows " + std::to_string(osv.dwMajorVersion) +
                           "." + std::to_string(osv.dwMinorVersion);
    log_msg("sysinfo: %s, ram %lluMB",
            g_sysinfo.cpu_name.c_str(),
            g_sysinfo.total_ram);
}

// WndProc hook
static LRESULT CALLBACK wnd_proc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!shutting_down.load())
        ImGui_ImplWin32_WndProcHandler(h, m, w, l);
    return CallWindowProc(orig_wnd_proc, h, m, w, l);
}

// SwapBuffers hook
static BOOL WINAPI hook_swap(HDC dc)
{
    static bool init = false;
    if (!init && wglGetCurrentContext())
    {
        game_window   = WindowFromDC(wglGetCurrentDC());
        orig_wnd_proc = (WNDPROC)SetWindowLongPtr(
            game_window, GWLP_WNDPROC, (LONG_PTR)wnd_proc);
        init = true;
    }
    if (init && !imgui_ready.load())
    {
        ImGui::CreateContext();
        ImGuiIO& io        = ImGui::GetIO();
        io.FontGlobalScale = 1.5f;
        ImGui_ImplWin32_Init(game_window);
        ImGui_ImplOpenGL3_Init("#version 330 core");
        imgui_ready = true;
        init_system_info();
        FARPROC orig =
            GetProcAddress(GetModuleHandleA("opengl32.dll"), "wglSwapBuffers");
        g_hooks.push_back({ "opengl32.dll",
                            "wglSwapBuffers",
                            (void*)orig,
                            (void*)hook_swap,
                            true });
    }
    if (imgui_ready.load())
    {
        draw_overlay();
    }
    return real_wgl_swap(dc);
}

// Install hook
static bool install_hook()
{
    HMODULE m = GetModuleHandleA("opengl32.dll");
    if (!m)
        return false;
    auto addr = (BYTE*)GetProcAddress(m, "wglSwapBuffers");
    if (!addr)
        return false;
    DWORD old;
    VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
    memcpy(original_bytes, addr, 5);
    intptr_t rel = (BYTE*)hook_swap - (addr + 5);
    addr[0]      = 0xE9;
    memcpy(addr + 1, &rel, 4);
    VirtualProtect(addr, 5, old, &old);
    auto tramp = (BYTE*)VirtualAlloc(
        nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(tramp, original_bytes, 5);
    tramp[5]      = 0xE9;
    intptr_t back = (addr + 5) - (tramp + 10);
    memcpy(tramp + 6, &back, 4);
    real_wgl_swap = (wgl_swap_t)tramp;
    return true;
}

// Remove hook
static void remove_hooks()
{
    shutting_down = true;
    Sleep(100);
    if (orig_wnd_proc)
        SetWindowLongPtr(game_window, GWLP_WNDPROC, (LONG_PTR)orig_wnd_proc);
    HMODULE m = GetModuleHandleA("opengl32.dll");
    if (m)
    {
        auto  addr = (BYTE*)GetProcAddress(m, "wglSwapBuffers");
        DWORD old;
        VirtualProtect(addr, 5, PAGE_EXECUTE_READWRITE, &old);
        memcpy(addr, original_bytes, 5);
        VirtualProtect(addr, 5, old, &old);
    }
    if (real_wgl_swap)
        VirtualFree((LPVOID)real_wgl_swap, 0, MEM_RELEASE);
    if (imgui_ready.load())
    {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
}



// Draw overlay
static void draw_overlay()
{
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplWin32_NewFrame();
    ImGui::NewFrame();
    if (dark_theme)
        ImGui::StyleColorsDark();
    else
        ImGui::StyleColorsLight();

    ImGui::Begin(
        "opengl interceptor overlay", nullptr, ImGuiWindowFlags_AlwaysAutoResize);
    if (ImGui::BeginTabBar("tabs"))
    {
        if (ImGui::BeginTabItem("main"))
        {
            ImGui::Checkbox("clear screen", &enable_clear);
            ImGui::SameLine();
            ImGui::ColorEdit3("clear color", (float*)&clear_color);
            ImGui::Checkbox("wireframe", &wireframe);
            glPolygonMode(GL_FRONT_AND_BACK, wireframe ? GL_LINE : GL_FILL);
            ImGui::Separator();
            ImGui::Text("log (%zu)", log_lines.size());
            if (ImGui::BeginChild("log", ImVec2(0, 100), true))
            {
                for (auto& l : log_lines)
                    ImGui::TextUnformatted(l.c_str());
                if (ImGui::GetScrollY() >= ImGui::GetScrollMaxY())
                    ImGui::SetScrollHereY(1.0f);
            }
            ImGui::EndChild();
            if (ImGui::Button("clear log"))
                log_lines.clear();
            ImGui::SameLine();
            if (ImGui::Button("exit"))
                PostQuitMessage(0);
            ImGui::EndTabItem();
        }
        if (ImGui::BeginTabItem("hooks"))
        {
            if (ImGui::BeginTable("hooks",
                                  5,
                                  ImGuiTableFlags_Borders |
                                      ImGuiTableFlags_Resizable))
            {
                ImGui::TableSetupColumn("module");
                ImGui::TableSetupColumn("function");
                ImGui::TableSetupColumn("orig");
                ImGui::TableSetupColumn("hook");
                ImGui::TableSetupColumn("active");
                ImGui::TableHeadersRow();
                for (auto& h : g_hooks)
                {
                    ImGui::TableNextRow();
                    ImGui::TableNextColumn();
                    ImGui::Text("%s", h.module.c_str());
                    ImGui::TableNextColumn();
                    ImGui::Text("%s", h.function.c_str());
                    ImGui::TableNextColumn();
                    ImGui::Text("%p", h.original_addr);
                    ImGui::TableNextColumn();
                    ImGui::Text("%p", h.hook_addr);
                    ImGui::TableNextColumn();
                    ImGui::Text(h.active ? "yes" : "no");
                }
                ImGui::EndTable();
            }
            ImGui::EndTabItem();
        }
        ImGui::EndTabBar();
    }
    ImGui::End();

    ImGui::Render();
    if (enable_clear)
    {
        glClearColor(
            clear_color.x, clear_color.y, clear_color.z, clear_color.w);
        glClear(GL_COLOR_BUFFER_BIT);
    }
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}


// DllMain
extern "C" BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID)
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
    return TRUE;
}