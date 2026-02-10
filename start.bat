@echo off
chcp 65001 >nul
cd /d "%~dp0"

nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo NVIDIA GPU を検出しました。GPU モードで起動します...
    uv run --extra gpu python -m ai_zunda
) else (
    echo NVIDIA GPU が見つかりません。CPU モードで起動します...
    uv run python -m ai_zunda
)
pause
