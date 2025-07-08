@echo off
chcp 65001 >nul
title 安装截图工具依赖

echo.
echo ======================================
echo       安装截图工具依赖
echo ======================================
echo.

echo 正在升级pip...
python -m pip install --upgrade pip

echo.
echo 正在安装依赖包...
pip install -r requirements.txt

echo.
echo 安装完成！
echo.
echo 已安装的包：
pip list

pause