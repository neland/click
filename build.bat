@echo off
where cl >nul 2>nul
if errorlevel 1 (
    echo 错误: 未找到 cl.exe。请在 Visual Studio 开发者命令行中运行此脚本，或先调用 vcvarsall.bat。
    exit /b 1
)

echo 正在编译 PrecisionClicker ...
cl /EHsc /std:c++17 /O2 /W4 /MT /DUNICODE /D_UNICODE /DWIN32_LEAN_AND_MEAN /D_CRT_SECURE_NO_WARNINGS ^
   main.cpp ^
   main_window.cpp ^
   task_dialog.cpp ^
   click_engine.cpp ^
   window_utils.cpp ^
   config_manager.cpp ^
   resource.rc ^
   /Fe:PrecisionClicker.exe ^
   user32.lib gdi32.lib comctl32.lib shell32.lib kernel32.lib advapi32.lib

if errorlevel 1 (
    echo 编译失败。
    exit /b 1
)
echo 编译成功: PrecisionClicker.exe
