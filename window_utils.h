#pragma once
#include <windows.h>
#include <string>
#include <functional>

struct WindowInfo {
    HWND hwnd = nullptr;
    std::wstring title;
    std::wstring className;
};

// Find window by partial title or exact class name
WindowInfo FindWindowByTitleOrClass(const std::wstring& title, const std::wstring& className);

// Coordinate conversion
bool GetClientRelativePos(HWND hwnd, int screenX, int screenY, int& outRelX, int& outRelY);
bool GetScreenPosFromClient(HWND hwnd, int relX, int relY, int& outScreenX, int& outScreenY);

// Window picker using global mouse hook
class WindowPicker {
public:
    using Callback = std::function<void(const WindowInfo&)>;
    
    static bool Start(Callback cb);
    static void Stop();
    static bool IsRunning();
    
private:
    static LRESULT CALLBACK MouseHookProc(int nCode, WPARAM wParam, LPARAM lParam);
    static HHOOK s_hook;
    static Callback s_callback;
    static bool s_running;
};
