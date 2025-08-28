#define WIN32_LEAN_AND_MEAN
#include "bass_proxy.hpp"
#include <GL/gl.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <imgui.h>
#include <imgui_impl_opengl3.h>
#include <imgui_impl_win32.h>
#include <string>
#include <vector>
#include <windows.h>

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND,
                                                             UINT,
                                                             WPARAM,
                                                             LPARAM);

using wgl_swap_t = BOOL(WINAPI*)(HDC);

static wgl_swap_t        real_wgl_swap = nullptr;
static HWND              game_window   = nullptr;
static WNDPROC           orig_wnd_proc = nullptr;
static std::atomic<bool> imgui_ready   = false;
static std::atomic<bool> shutting_down = false;
static BYTE              original_bytes[5];
static bool              dark_theme   = true;
static ImVec4            clear_color  = ImVec4(0, 0, 0, 0);
static bool              enable_clear = false;
static bool              wireframe    = false;

struct hook_entry final
{
    std::string module, function;
    void *      original_addr, *hook_addr;
    bool        active;
};

static std::vector<hook_entry> g_hooks;

// minimalist log buffer - based on imgui console example
struct console_buffer
{
    ImGuiTextBuffer buf;
    ImGuiTextFilter filter;
    ImVector<int>   line_offsets;
    bool            auto_scroll = true;

    void clear()
    {
        buf.clear();
        line_offsets.clear();
        line_offsets.push_back(0);
    }

    void add_log(const char* fmt, ...) IM_FMTARGS(2)
    {
        int     old_size = buf.size();
        va_list args;
        va_start(args, fmt);
        buf.appendfv(fmt, args);
        va_end(args);
        for (int new_size = buf.size(); old_size < new_size; old_size++)
        {
            if (buf[old_size] == '\n')
            {
                line_offsets.push_back(old_size + 1);
            }
        }
    }

    void draw()
    {
        if (ImGui::BeginPopup("options"))
        {
            ImGui::Checkbox("auto-scroll", &auto_scroll);
            ImGui::EndPopup();
        }

        if (ImGui::Button("options"))
        {
            ImGui::OpenPopup("options");
        }
        ImGui::SameLine();

        bool clear_pressed = ImGui::Button("clear");
        ImGui::SameLine();

        bool copy = ImGui::Button("copy");
        ImGui::SameLine();

        filter.Draw("filter", -100.0f);

        ImGui::Separator();

        if (ImGui::BeginChild("scrolling",
                              ImVec2(0, 0),
                              false,
                              ImGuiWindowFlags_HorizontalScrollbar))
        {
            if (clear_pressed)
            {
                clear();
            }
            if (copy)
            {
                ImGui::LogToClipboard();
            }

            ImGui::PushStyleVar(ImGuiStyleVar_ItemSpacing, ImVec2(0, 0));
            const char* buf_begin = buf.begin();
            const char* buf_end   = buf.end();

            if (filter.IsActive())
            {
                for (int line_no = 0; line_no < line_offsets.Size; line_no++)
                {
                    const char* line_start = buf_begin + line_offsets[line_no];
                    const char* line_end =
                        (line_no + 1 < line_offsets.Size)
                            ? (buf_begin + line_offsets[line_no + 1] - 1)
                            : buf_end;
                    if (filter.PassFilter(line_start, line_end))
                    {
                        ImGui::TextUnformatted(line_start, line_end);
                    }
                }
            }
            else
            {
                ImGuiListClipper clipper;
                clipper.Begin(line_offsets.Size);
                while (clipper.Step())
                {
                    for (int line_no = clipper.DisplayStart;
                         line_no < clipper.DisplayEnd;
                         line_no++)
                    {
                        const char* line_start =
                            buf_begin + line_offsets[line_no];
                        const char* line_end =
                            (line_no + 1 < line_offsets.Size)
                                ? (buf_begin + line_offsets[line_no + 1] - 1)
                                : buf_end;
                        ImGui::TextUnformatted(line_start, line_end);
                    }
                }
                clipper.End();
            }

            ImGui::PopStyleVar();

            if (auto_scroll && ImGui::GetScrollY() >= ImGui::GetScrollMaxY())
            {
                ImGui::SetScrollHereY(1.0f);
            }
        }
        ImGui::EndChild();
    }
};

static console_buffer console;

static void log_msg(const char* fmt, ...)
{
    const auto now    = std::chrono::system_clock::now();
    const auto time_t = std::chrono::system_clock::to_time_t(now);
    const auto tm     = *std::localtime(&time_t);

    char timestamp[32];
    std::snprintf(timestamp,
                  sizeof(timestamp),
                  "[%02d:%02d:%02d] ",
                  tm.tm_hour,
                  tm.tm_min,
                  tm.tm_sec);

    char    buffer[1024];
    va_list args;
    va_start(args, fmt);
    std::vsnprintf(buffer, sizeof(buffer), fmt, args);
    va_end(args);

    console.add_log("%s%s\n", timestamp, buffer);
}

static void report_winapi_error(const char* operation, DWORD error_code)
{
    LPSTR message_buffer = nullptr;

    const DWORD format_result = FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
            FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr,
        error_code,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        reinterpret_cast<LPSTR>(&message_buffer),
        0,
        nullptr);

    if (format_result && message_buffer)
    {
        log_msg("error: %s: %s (%lu)", operation, message_buffer, error_code);
        LocalFree(message_buffer);
    }
    else
    {
        log_msg(
            "error: %s: error code %lu (format failed)", operation, error_code);
    }
}

struct system_info final
{
    std::string cpu_arch, os_version;
    uint64_t    total_ram;
} g_sysinfo;

static void init_system_info()
{
    SYSTEM_INFO si;
    GetSystemInfo(&si);

    switch (si.wProcessorArchitecture)
    {
        case PROCESSOR_ARCHITECTURE_AMD64:
            g_sysinfo.cpu_arch = "x64";
            break;
        case PROCESSOR_ARCHITECTURE_INTEL:
            g_sysinfo.cpu_arch = "x86";
            break;
        case PROCESSOR_ARCHITECTURE_ARM64:
            g_sysinfo.cpu_arch = "arm64";
            break;
        default:
            g_sysinfo.cpu_arch = "unknown";
    }

    MEMORYSTATUSEX ms{ sizeof(ms) };
    if (GlobalMemoryStatusEx(&ms))
    {
        g_sysinfo.total_ram = ms.ullTotalPhys / (1024 * 1024);
    }
    else
    {
        report_winapi_error("GlobalMemoryStatusEx", GetLastError());
        g_sysinfo.total_ram = 0;
    }

    g_sysinfo.os_version = "Windows";

    log_msg("system: %s, %s, %lluMB ram",
            g_sysinfo.cpu_arch.c_str(),
            g_sysinfo.os_version.c_str(),
            g_sysinfo.total_ram);
}

static LRESULT CALLBACK wnd_proc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!shutting_down.load())
    {
        ImGui_ImplWin32_WndProcHandler(h, m, w, l);
    }
    return CallWindowProc(orig_wnd_proc, h, m, w, l);
}

static void draw_overlay();

[[nodiscard]] static bool WINAPI hook_swap(HDC dc)
{
    static bool init = false;

    if (!init && wglGetCurrentContext())
    {
        game_window = WindowFromDC(wglGetCurrentDC());
        if (!game_window)
        {
            log_msg("error: WindowFromDC failed");
            return real_wgl_swap(dc);
        }

        orig_wnd_proc = reinterpret_cast<WNDPROC>(SetWindowLongPtrA(
            game_window, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wnd_proc)));

        if (!orig_wnd_proc)
        {
            report_winapi_error("SetWindowLongPtrA", GetLastError());
        }
        else
        {
            log_msg("hooked window procedure");
        }

        init = true;
    }

    if (init && !imgui_ready.load())
    {
        ImGui::CreateContext();
        ImGuiIO& io        = ImGui::GetIO();
        io.FontGlobalScale = 1.2f;

        if (!ImGui_ImplWin32_Init(game_window))
        {
            log_msg("error: ImGui_ImplWin32_Init failed");
        }
        else if (!ImGui_ImplOpenGL3_Init("#version 330 core"))
        {
            log_msg("error: ImGui_ImplOpenGL3_Init failed");
        }
        else
        {
            imgui_ready = true;
            log_msg("imgui initialized");

            init_system_info();

            const FARPROC orig = GetProcAddress(
                GetModuleHandleA("opengl32.dll"), "wglSwapBuffers");
            if (orig)
            {
                g_hooks.push_back({ "opengl32.dll",
                                    "wglSwapBuffers",
                                    reinterpret_cast<void*>(orig),
                                    reinterpret_cast<void*>(hook_swap),
                                    true });
                log_msg("registered hook: wglSwapBuffers");
            }
        }
    }

    if (imgui_ready.load())
    {
        draw_overlay();
    }

    return real_wgl_swap(dc);
}

[[nodiscard]] bool install_hook()
{
    log_msg("installing hook...");

    const HMODULE opengl_module = GetModuleHandleA("opengl32.dll");
    if (!opengl_module)
    {
        report_winapi_error("GetModuleHandleA(opengl32.dll)", GetLastError());
        return false;
    }

    auto target_addr = reinterpret_cast<BYTE*>(
        GetProcAddress(opengl_module, "wglSwapBuffers"));
    if (!target_addr)
    {
        report_winapi_error("GetProcAddress(wglSwapBuffers)", GetLastError());
        return false;
    }

    log_msg("target address: %p", target_addr);

    DWORD old_protect;
    if (!VirtualProtect(target_addr, 5, PAGE_EXECUTE_READWRITE, &old_protect))
    {
        report_winapi_error("VirtualProtect", GetLastError());
        return false;
    }

    std::memcpy(original_bytes, target_addr, 5);

    const intptr_t rel_offset =
        reinterpret_cast<BYTE*>(hook_swap) - (target_addr + 5);
    target_addr[0] = 0xE9;
    std::memcpy(target_addr + 1, &rel_offset, 4);

    DWORD dummy;
    if (!VirtualProtect(target_addr, 5, old_protect, &dummy))
    {
        report_winapi_error("VirtualProtect restore", GetLastError());
    }

    auto trampoline = reinterpret_cast<BYTE*>(VirtualAlloc(
        nullptr, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));

    if (!trampoline)
    {
        report_winapi_error("VirtualAlloc", GetLastError());
        return false;
    }

    std::memcpy(trampoline, original_bytes, 5);
    trampoline[5] = 0xE9;

    const intptr_t back_offset = (target_addr + 5) - (trampoline + 10);
    std::memcpy(trampoline + 6, &back_offset, 4);

    real_wgl_swap = reinterpret_cast<wgl_swap_t>(trampoline);

    log_msg("hook installed successfully, trampoline: %p", trampoline);
    return true;
}

void remove_hooks()
{
    log_msg("removing hooks...");
    shutting_down = true;

    if (orig_wnd_proc && game_window)
    {
        SetWindowLongPtrA(game_window,
                          GWLP_WNDPROC,
                          reinterpret_cast<LONG_PTR>(orig_wnd_proc));
        log_msg("restored window procedure");
    }

    const HMODULE opengl_module = GetModuleHandleA("opengl32.dll");
    if (opengl_module)
    {
        auto target_addr = reinterpret_cast<BYTE*>(
            GetProcAddress(opengl_module, "wglSwapBuffers"));
        if (target_addr)
        {
            DWORD old_protect, dummy;
            if (VirtualProtect(
                    target_addr, 5, PAGE_EXECUTE_READWRITE, &old_protect))
            {
                std::memcpy(target_addr, original_bytes, 5);
                VirtualProtect(target_addr, 5, old_protect, &dummy);
                log_msg("restored original bytes");
            }
        }
    }

    if (real_wgl_swap)
    {
        if (!VirtualFree(
                reinterpret_cast<LPVOID>(real_wgl_swap), 0, MEM_RELEASE))
        {
            report_winapi_error("VirtualFree", GetLastError());
        }
        else
        {
            log_msg("freed trampoline");
        }
    }

    if (imgui_ready.load())
    {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
        log_msg("imgui shutdown");
    }
}

static void draw_overlay()
{
    if (!ImGui::GetCurrentContext())
        return;

    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplWin32_NewFrame();
    ImGui::NewFrame();

    // minimal dark theme
    static bool style_init = false;
    if (!style_init)
    {
        ImGui::StyleColorsDark();
        auto& style          = ImGui::GetStyle();
        style.WindowRounding = 6.0f;
        style.FrameRounding  = 4.0f;
        style.WindowPadding  = ImVec2(8, 8);
        style.FramePadding   = ImVec2(6, 4);
        style.ItemSpacing    = ImVec2(6, 4);
        style_init           = true;
    }

    ImGui::SetNextWindowBgAlpha(0.9f);
    ImGui::SetNextWindowPos(ImVec2(10, 10), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(500, 400), ImGuiCond_FirstUseEver);

    if (ImGui::Begin("overlay", nullptr))
    {
        if (ImGui::BeginTabBar("main_tabs"))
        {
            if (ImGui::BeginTabItem("console"))
            {
                console.draw();
                ImGui::EndTabItem();
            }

            if (ImGui::BeginTabItem("render"))
            {
                static bool prev_wireframe = wireframe;

                ImGui::Checkbox("clear screen", &enable_clear);

                ImGui::SameLine();

                ImGui::ColorEdit3("clear color",
                                  reinterpret_cast<float*>(&clear_color),
                                  ImGuiColorEditFlags_NoInputs |
                                      ImGuiColorEditFlags_DisplayRGB);

                if (ImGui::Checkbox("wireframe", &wireframe))
                {
                    if (wireframe != prev_wireframe)
                    {
                        glPolygonMode(GL_FRONT_AND_BACK,
                                      wireframe ? GL_LINE : GL_FILL);
                        prev_wireframe = wireframe;
                        log_msg("wireframe: %s",
                                wireframe ? "enabled" : "disabled");
                    }
                }

                ImGui::EndTabItem();
            }

            if (ImGui::BeginTabItem("hooks"))
            {
                static ImGuiTextFilter filter;
                filter.Draw("filter", -100.0f);

                if (ImGui::BeginTable("hooks_table",
                                      4,
                                      ImGuiTableFlags_Borders |
                                          ImGuiTableFlags_RowBg |
                                          ImGuiTableFlags_ScrollY))
                {

                    ImGui::TableSetupColumn("module");
                    ImGui::TableSetupColumn("function");
                    ImGui::TableSetupColumn("original");
                    ImGui::TableSetupColumn("active");
                    ImGui::TableHeadersRow();

                    for (const auto& hook : g_hooks)
                    {
                        if (!filter.PassFilter(hook.module.c_str()) &&
                            !filter.PassFilter(hook.function.c_str()))
                        {
                            continue;
                        }

                        ImGui::TableNextRow();
                        ImGui::TableNextColumn();
                        ImGui::TextUnformatted(hook.module.c_str());
                        ImGui::TableNextColumn();
                        ImGui::TextUnformatted(hook.function.c_str());
                        ImGui::TableNextColumn();
                        ImGui::Text("%p", hook.original_addr);
                        ImGui::TableNextColumn();

                        if (hook.active)
                        {
                            ImGui::TextColored(ImVec4(0.2f, 0.8f, 0.3f, 1.0f),
                                               "active");
                        }
                        else
                        {
                            ImGui::TextColored(ImVec4(0.8f, 0.2f, 0.2f, 1.0f),
                                               "inactive");
                        }
                    }

                    ImGui::EndTable();
                }
                ImGui::EndTabItem();
            }

            ImGui::EndTabBar();
        }

        // exit button
        ImGui::Separator();
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.8f, 0.2f, 0.2f, 0.8f));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered,
                              ImVec4(0.9f, 0.3f, 0.3f, 0.9f));
        if (ImGui::Button("exit"))
        {
            PostQuitMessage(0);
        }
        ImGui::PopStyleColor(2);
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
