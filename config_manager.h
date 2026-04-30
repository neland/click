#pragma once
#include <vector>
#include <string>
#include "common_types.h"

class ConfigManager {
public:
    static bool Load(const std::wstring& path, std::vector<ClickTask>& outTasks);
    static bool Save(const std::wstring& path, const std::vector<ClickTask>& tasks);
};
