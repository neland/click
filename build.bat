@echo off
chcp 65001 >nul
echo ==========================================
echo   Precision Clicker 打包工具
echo ==========================================
echo.

echo [1/3] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 未安装 PyInstaller，正在自动安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo 安装失败，请检查 Python 和 pip 是否正常。
        pause
        exit /b 1
    )
) else (
    echo PyInstaller 已安装。
)

echo.
echo [2/3] 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] 生成图标...
python generate_icon.py

echo.
echo [4/4] 打包为独立可执行文件...
pyinstaller --onefile --windowed --icon "icon.ico" --name "PrecisionClicker" precision_clicker.py

if errorlevel 1 (
    echo.
    echo 打包失败。
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   打包成功！
echo ==========================================
echo 可执行文件: dist\PrecisionClicker.exe
echo.
echo 可直接复制该文件到其他 Windows 电脑运行，
echo 无需安装 Python。
echo.
pause
