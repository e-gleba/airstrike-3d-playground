#define WIN32_LEAN_AND_MEAN

#include <imgui_impl_opengl3.h>
#include <imgui_impl_win32.h>
#include <imgui.h>

#include <GL/gl.h>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cpuid.h>
#include <psapi.h>
#include <string>
#include <vector>
#include <algorithm>

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

static bool   dark_theme   = true;
static ImVec4 clear_color  = ImVec4(0, 0, 0, 0);
static bool   enable_clear = false;
static bool   wireframe    = false;

struct hook_entry final
{
    std::string module, function;
    void *      original_addr, *hook_addr;
    bool        active;
};
static std::vector<hook_entry> g_hooks;

struct system_info final
{
    std::string cpu_name, os_version;
    uint64_t    total_ram;
} g_sysinfo;

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

static void init_system_info()
{
    char brand[49] = {};
    unsigned regs[4];

    for (unsigned i = 0; i < 3; ++i) {
        if (!__get_cpuid(0x80000002 + i, regs, regs + 1, regs + 2, regs + 3)) {
            std::strcpy(brand, "unknown cpu");
            break;
        }
        std::memcpy(brand + 16 * i, regs, 16);
    }
    g_sysinfo.cpu_name = brand;

    MEMORYSTATUSEX ms{sizeof(ms)};
    g_sysinfo.total_ram = GlobalMemoryStatusEx(&ms) ? ms.ullTotalPhys / (1024 * 1024) : 0;

    OSVERSIONINFOA osv{sizeof(osv)};
    g_sysinfo.os_version = GetVersionExA(&osv)
        ? "Windows " + std::to_string(osv.dwMajorVersion) + "." + std::to_string(osv.dwMinorVersion)
        : "unknown windows";

    log_msg("sysinfo: %s, ram %lluMB",
            g_sysinfo.cpu_name.c_str(),
            g_sysinfo.total_ram);
}


static LRESULT CALLBACK wnd_proc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!shutting_down.load())
        ImGui_ImplWin32_WndProcHandler(h, m, w, l);
    return CallWindowProc(orig_wnd_proc, h, m, w, l);
}

// Forwards
static void draw_overlay();

[[nodiscard]] static bool WINAPI hook_swap(HDC dc)
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

[[nodiscard]] bool install_hook()
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

void remove_hooks()
{
    shutting_down = true;
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

static void draw_overlay()
{
    if (!ImGui::GetCurrentContext()) return;

    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplWin32_NewFrame();
    ImGui::NewFrame();

    static bool style_init = false;
    static bool last_dark = false;
    if (!style_init || last_dark != dark_theme)
    {
        last_dark = dark_theme;
        if (dark_theme) ImGui::StyleColorsDark(); else ImGui::StyleColorsLight();

        auto& s = ImGui::GetStyle();
        s.WindowRounding = 8.0f;
        s.FrameRounding = 6.0f;
        s.GrabRounding = 6.0f;
        s.WindowBorderSize = 0.0f;
        s.FrameBorderSize = 0.0f;
        s.PopupBorderSize = 0.0f;
        s.WindowPadding = ImVec2(12, 10);
        s.FramePadding  = ImVec2(8, 6);
        s.ItemSpacing   = ImVec2(8, 6);
        s.ScrollbarSize = 12.0f;

        ImVec4 accent = dark_theme ? ImVec4(0.23f, 0.52f, 0.96f, 1.0f)
                                   : ImVec4(0.16f, 0.47f, 0.96f, 1.0f);
        auto& c = s.Colors;
        c[ImGuiCol_TitleBgActive]   = ImVec4(0,0,0,0);
        c[ImGuiCol_Button]          = ImVec4(accent.x, accent.y, accent.z, 0.12f);
        c[ImGuiCol_ButtonHovered]   = ImVec4(accent.x, accent.y, accent.z, 0.20f);
        c[ImGuiCol_ButtonActive]    = ImVec4(accent.x, accent.y, accent.z, 0.30f);
        c[ImGuiCol_CheckMark]       = accent;
        c[ImGuiCol_SliderGrab]      = accent;
        c[ImGuiCol_SliderGrabActive]= accent;
        c[ImGuiCol_Header]          = ImVec4(accent.x, accent.y, accent.z, 0.12f);
        c[ImGuiCol_HeaderHovered]   = ImVec4(accent.x, accent.y, accent.z, 0.18f);
        c[ImGuiCol_HeaderActive]    = ImVec4(accent.x, accent.y, accent.z, 0.24f);

        style_init = true;
    }

    ImGui::SetNextWindowBgAlpha(0.94f);
    ImGui::SetNextWindowPos(ImVec2(12, 12), ImGuiCond_FirstUseEver);
    ImGuiWindowFlags wflags = ImGuiWindowFlags_NoTitleBar |
                              ImGuiWindowFlags_NoCollapse |
                              ImGuiWindowFlags_AlwaysAutoResize |
                              ImGuiWindowFlags_NoSavedSettings;

    if (!ImGui::Begin("overlay", nullptr, wflags))
    {
        ImGui::End();
        ImGui::Render();
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        return;
    }

    if (ImGui::BeginTabBar("tabs", ImGuiTabBarFlags_NoCloseWithMiddleMouseButton))
    {
        if (ImGui::BeginTabItem("main"))
        {
            static bool auto_scroll = true;
            static bool prev_wireframe = wireframe;

            ImGui::BeginGroup();
            ImGui::Checkbox("clear screen", &enable_clear);
            if (ImGui::Checkbox("wireframe", &wireframe))
            {
                if (wireframe != prev_wireframe)
                {
                    glPolygonMode(GL_FRONT_AND_BACK, wireframe ? GL_LINE : GL_FILL);
                    prev_wireframe = wireframe;
                }
            }
            ImGui::EndGroup();

            ImGui::SameLine();

            ImGui::BeginGroup();
            ImGui::ColorEdit3("clear color",
                              (float*)&clear_color,
                              ImGuiColorEditFlags_NoAlpha |
                              ImGuiColorEditFlags_NoInputs |
                              ImGuiColorEditFlags_DisplayRGB);
            ImGui::EndGroup();

            ImGui::SeparatorText("log");

            const float log_h = 140.0f;
            if (ImGui::BeginChild("log", ImVec2(0, log_h), true, ImGuiWindowFlags_AlwaysVerticalScrollbar | ImGuiWindowFlags_HorizontalScrollbar))
            {
                ImGuiListClipper clipper;
                clipper.Begin((int)log_lines.size());
                while (clipper.Step())
                    for (int i = clipper.DisplayStart; i < clipper.DisplayEnd; ++i)
                        ImGui::TextUnformatted(log_lines[(size_t)i].c_str());

                if (auto_scroll && ImGui::GetScrollY() >= ImGui::GetScrollMaxY())
                    ImGui::SetScrollHereY(1.0f);
            }
            ImGui::EndChild();

            if (ImGui::SmallButton("clear log")) log_lines.clear();
            ImGui::SameLine();
            ImGui::Checkbox("auto-scroll", &auto_scroll);
            ImGui::SameLine();
            ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.85f, 0.20f, 0.20f, 0.80f));
            ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.90f, 0.25f, 0.25f, 0.90f));
            ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.80f, 0.15f, 0.15f, 1.00f));
            if (ImGui::SmallButton("exit")) PostQuitMessage(0);
            ImGui::PopStyleColor(3);

            ImGui::EndTabItem();
        }

        if (ImGui::BeginTabItem("hooks"))
        {
            static ImGuiTextFilter filter;
            filter.Draw("filter", 180.0f);

            ImGuiTableFlags tflags = ImGuiTableFlags_Borders |
                                     ImGuiTableFlags_Resizable |
                                     ImGuiTableFlags_RowBg |
                                     ImGuiTableFlags_ScrollY |
                                     ImGuiTableFlags_Sortable |
                                     ImGuiTableFlags_SizingStretchProp;
            const float table_h = ImGui::GetTextLineHeightWithSpacing() * 10.0f +
                                  ImGui::GetStyle().CellPadding.y * 2.0f;

            if (ImGui::BeginTable("hooks_table", 5, tflags, ImVec2(0, table_h)))
            {
                ImGui::TableSetupColumn("module", ImGuiTableColumnFlags_DefaultSort);
                ImGui::TableSetupColumn("function");
                ImGui::TableSetupColumn("orig");
                ImGui::TableSetupColumn("hook");
                ImGui::TableSetupColumn("active", ImGuiTableColumnFlags_PreferSortDescending);
                ImGui::TableHeadersRow();

                ImGuiTableSortSpecs* sort = ImGui::TableGetSortSpecs();
                static std::vector<int> order;
                order.resize((int)g_hooks.size());
                for (int i = 0; i < (int)g_hooks.size(); ++i) order[i] = i;

                if (sort && sort->SpecsCount > 0)
                {
                    auto cmp = [&](int a, int b) {
                        const auto& ha = g_hooks[(size_t)a];
                        const auto& hb = g_hooks[(size_t)b];
                        const ImGuiTableColumnSortSpecs& s = sort->Specs[0];
                        const bool asc = (s.SortDirection == ImGuiSortDirection_Ascending);
                        switch (s.ColumnIndex)
                        {
                            case 0: { int r = ha.module.compare(hb.module);   return asc ? r < 0 : r > 0; }
                            case 1: { int r = ha.function.compare(hb.function); return asc ? r < 0 : r > 0; }
                            case 2: { auto ra = (uintptr_t)ha.original_addr; auto rb = (uintptr_t)hb.original_addr; return asc ? (ra < rb) : (ra > rb); }
                            case 3: { auto ra = (uintptr_t)ha.hook_addr;     auto rb = (uintptr_t)hb.hook_addr;     return asc ? (ra < rb) : (ra > rb); }
                            case 4: { bool ra = ha.active, rb = hb.active; return asc ? (ra < rb) : (ra > rb); }
                        }
                        return false;
                    };
                    std::stable_sort(order.begin(), order.end(), cmp);
                }

                for (int idx : order)
                {
                    const auto& h = g_hooks[(size_t)idx];
                    if (!filter.PassFilter(h.module.c_str()) &&
                        !filter.PassFilter(h.function.c_str()))
                        continue;

                    ImGui::TableNextRow();
                    ImGui::TableNextColumn(); ImGui::TextUnformatted(h.module.c_str());
                    ImGui::TableNextColumn(); ImGui::TextUnformatted(h.function.c_str());
                    ImGui::TableNextColumn(); ImGui::Text("%p", h.original_addr);
                    ImGui::TableNextColumn(); ImGui::Text("%p", h.hook_addr);
                    ImGui::TableNextColumn();
                    if (h.active) ImGui::TextColored(ImVec4(0.20f,0.70f,0.30f,1.0f), "yes");
                    else          ImGui::TextColored(ImVec4(0.70f,0.20f,0.20f,1.0f), "no");
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
        glClearColor(clear_color.x, clear_color.y, clear_color.z, clear_color.w);
        glClear(GL_COLOR_BUFFER_BIT);
    }

    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}

