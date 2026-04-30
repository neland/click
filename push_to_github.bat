@echo off
chcp 65001 >nul
cd /d "e:\mxm\code\PrecisionClicker"

echo [1/6] 初始化 Git 仓库...
"C:\Program Files\Git\bin\git.exe" init

echo [2/6] 添加文件...
"C:\Program Files\Git\bin\git.exe" add .

echo [3/6] 提交...
"C:\Program Files\Git\bin\git.exe" commit -m "init: precision clicker with ms-level timing"

echo [4/6] 设置远程仓库...
"C:\Program Files\Git\bin\git.exe" remote add origin https://github.com/neland/click.git

echo [5/6] 切换到 main 分支...
"C:\Program Files\Git\bin\git.exe" branch -M main

echo [6/6] 推送到 GitHub...
"C:\Program Files\Git\bin\git.exe" push -u origin main

echo.
echo 完成。如果 push 失败，请检查 GitHub 账号密码或 Token。
pause
