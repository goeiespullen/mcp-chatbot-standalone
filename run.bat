@echo off
REM MCP ChatBot - Terminal Interface (Windows)
REM This script starts the MCP ChatBot that connects to the MCP Manager Gateway

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Python is not found or not in PATH
    echo.
    echo Please install Python 3.7+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check Python version (requires 3.7+)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Using Python %PYTHON_VERSION%

REM Check if MCP Manager is running on port 8700
netstat -an | findstr ":8700" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  WARNING: MCP Manager gateway is not running on port 8700
    echo.
    echo Please start MCP Manager first:
    echo   cd C:\path\to\mcp-manager-standalone
    echo   run.bat
    echo.
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "%CONTINUE%"=="y" (
        exit /b 1
    )
)

echo.
echo 🚀 Starting MCP ChatBot...
echo.

REM Run the chatbot
python chatbot.py %*

if errorlevel 1 (
    echo.
    echo ❌ Chatbot exited with error
    pause
)
