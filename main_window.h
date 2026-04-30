#pragma once
#include <windows.h>
#include <vector>
#include "common_types.h"
#include "click_engine.h"

class MainWindow {
public:
    static bool RegisterClass(HINSTANCE hInst);
    static bool Create(HINSTANCE hInst);
    static HWND GetHwnd();
    
    static void RefreshList();
    static void AddTask(const ClickTask& task);
    static void UpdateTask(int id, const ClickTask& task);
    static void DeleteSelectedTask();
    static ClickTask* GetSelectedTask();
    static const std::vector<ClickTask>& GetTasks();
    
    static void StartScheduler();
    static void StopScheduler();
    
private:
    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
    static void OnCreate(HWND hwnd);
    static void OnSize(HWND hwnd, int w, int h);
    static void OnCommand(HWND hwnd, int id);
    static void InitListView(HWND hwnd);
    static void UpdateStatusBar(HWND hwnd);
    
    static HWND s_hwnd;
    static HWND s_hwndList;
    static HWND s_hwndStatus;
    static HINSTANCE s_hInst;
    static std::vector<ClickTask> s_tasks;
    static TaskScheduler s_scheduler;
    static int s_nextId;
};
