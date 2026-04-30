#pragma once
#include <windows.h>
#include <vector>
#include <atomic>
#include <thread>
#include "common_types.h"

// High precision timer utilities
namespace HPTimer {
    void Initialize();
    double QpcToMilliseconds(LONGLONG qpc);
    LONGLONG MillisecondsToQpc(double ms);
    LONGLONG GetCurrentQpc();
    double GetCurrentQpcMs();
    
    // Convert SYSTEMTIME to FILETIME
    FILETIME SystemTimeToFileTime(const SYSTEMTIME& st);
    
    // High precision sleep until target FILETIME (using hybrid spin)
    void SleepUntil(const FILETIME& targetFt);
}

// Click simulation
namespace Clicker {
    bool ClickBackground(HWND hwnd, int x, int y, MouseButton btn);
    bool ClickForeground(int x, int y, MouseButton btn);
    bool PerformClick(const ClickTask& task, HWND hwnd);
}

// Task scheduler
class TaskScheduler {
public:
    TaskScheduler();
    ~TaskScheduler();
    
    void SetTasks(const std::vector<ClickTask>& tasks);
    void Start();
    void Stop();
    bool IsRunning() const;
    
private:
    void WorkerThread();
    
    std::vector<ClickTask> m_tasks;
    std::atomic<bool> m_running{ false };
    std::thread m_thread;
    HANDLE m_wakeEvent = nullptr;
};
