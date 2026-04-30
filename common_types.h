#pragma once
#include <string>
#include <cstdint>

enum class ClickMode {
    Background,
    Foreground
};

enum class MouseButton {
    Left,
    Right
};

struct ClickTask {
    int id = 0;
    std::wstring windowTitle;
    std::wstring windowClass;
    int relativeX = 0;
    int relativeY = 0;

    int year = 0, month = 0, day = 0;
    int hour = 0, minute = 0, second = 0, millisecond = 0;

    int offsetMs = 0;
    int intervalMs = 0;
    int repeatCount = 1;
    MouseButton button = MouseButton::Left;
    ClickMode mode = ClickMode::Background;

    bool enabled = true;
    std::wstring status; // runtime status
};
