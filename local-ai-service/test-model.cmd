@echo off
setlocal
cd /d "%~dp0"

set "MODEL=%OLLAMA_MODEL%"
if not defined MODEL set "MODEL=qwen3:8b"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"OLLAMA_MODEL=" ".env" 2^>nul`) do (
        if not "%%B"=="" set "MODEL=%%B"
    )
)

where ollama.exe >nul 2>&1
if errorlevel 1 (
    echo Khong tim thay Ollama trong PATH.
    echo Hay cai Ollama va mo lai Windows Terminal.
    exit /b 1
)

ollama show "%MODEL%" >nul 2>&1
if errorlevel 1 (
    echo Model "%MODEL%" chua duoc cai.
    echo Chay lenh sau de tai model:
    echo     ollama pull %MODEL%
    exit /b 1
)

echo Dang dung model: %MODEL%

if "%~1"=="" (
    echo Nhap /bye de thoat khoi phien chat.
    echo.
    ollama run "%MODEL%"
) else (
    ollama run "%MODEL%" %*
)

exit /b %ERRORLEVEL%
