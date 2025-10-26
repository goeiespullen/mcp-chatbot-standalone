# MCP Terminal ChatBot

A simple terminal-based chatbot that connects to MCP Manager Gateway and uses ChatNS LLM for interactive conversations.

**Cross-Platform Support:** Linux, Windows, macOS

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Linux](#linux)
  - [Windows](#windows)
  - [macOS](#macos)
- [Usage](#usage)
- [Commands](#commands)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Features

- ✅ **Direct connection** via MCP Manager Gateway (port 8700)
- ✅ **ChatNS LLM integration** via MCP protocol
- ✅ **Conversation history** - maintains context between messages
- ✅ **Clean interface** - only AI responses, no JSON formatting
- ✅ **Interactive commands** - `/clear`, `/quit`, `/help`
- ✅ **Cross-platform** - Works on Linux, Windows, and macOS
- ✅ **Zero dependencies** - Uses only Python standard library

---

## Prerequisites

### All Platforms

1. **Python 3.7 or higher** with asyncio support
2. **MCP Manager** running with gateway on port 8700
3. **ChatNS MCP Server** configured in MCP Manager

### Check Python Version

**Linux/macOS:**
```bash
python3 --version
```

**Windows:**
```cmd
python --version
```

If Python is not installed, see [Installation](#installation) section below.

---

## Installation

### Linux

#### 1. Install Python (if needed)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**Fedora/RHEL:**
```bash
sudo dnf install python3 python3-pip
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip
```

#### 2. Download MCP ChatBot

```bash
# Clone from GitHub
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone

# Or download and extract ZIP
wget https://github.com/goeiespullen/mcp-chatbot-standalone/archive/refs/heads/main.zip
unzip main.zip
cd mcp-chatbot-standalone-main
```

#### 3. Make script executable

```bash
chmod +x run.sh chatbot.py
```

#### 4. Start the chatbot

```bash
./run.sh
# Or directly:
python3 chatbot.py
```

---

### Windows

#### 1. Install Python

1. Download Python from [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **IMPORTANT:** Check "Add Python to PATH" during installation
4. Click "Install Now"

**Verify installation:**
```cmd
python --version
```

#### 2. Download MCP ChatBot

**Option A: Using Git (if installed)**
```cmd
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone
```

**Option B: Download ZIP**
1. Go to https://github.com/goeiespullen/mcp-chatbot-standalone
2. Click "Code" → "Download ZIP"
3. Extract ZIP to a folder (e.g., `C:\mcp-chatbot-standalone`)
4. Open Command Prompt and navigate to folder:
   ```cmd
   cd C:\mcp-chatbot-standalone
   ```

#### 3. Start the chatbot

**Option A: Using batch script**
```cmd
run.bat
```

**Option B: Direct Python**
```cmd
python chatbot.py
```

---

### macOS

#### 1. Install Python (if needed)

**Option A: Using Homebrew (recommended)**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python3
```

**Option B: Download from python.org**
1. Download Python from [python.org/downloads/macos](https://www.python.org/downloads/macos/)
2. Run the installer package (.pkg file)
3. Follow installation wizard

**Verify installation:**
```bash
python3 --version
```

#### 2. Download MCP ChatBot

```bash
# Clone from GitHub
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone

# Or download ZIP
curl -L -o chatbot.zip https://github.com/goeiespullen/mcp-chatbot-standalone/archive/refs/heads/main.zip
unzip chatbot.zip
cd mcp-chatbot-standalone-main
```

#### 3. Make script executable

```bash
chmod +x run.sh chatbot.py
```

#### 4. Start the chatbot

```bash
./run.sh
# Or directly:
python3 chatbot.py
```

---

## Usage

### Starting the Chatbot

**Before starting the chatbot**, ensure MCP Manager is running:

**Linux/macOS:**
```bash
# In another terminal window
cd /path/to/mcp-manager-standalone
./run.sh
```

**Windows:**
```cmd
REM In another Command Prompt window
cd C:\path\to\mcp-manager-standalone
run.bat
```

**Then start the chatbot:**

**Linux/macOS:**
```bash
cd /path/to/mcp-chatbot-standalone
./run.sh
```

**Windows:**
```cmd
cd C:\path\to\mcp-chatbot-standalone
run.bat
```

### Interactive Chat Session

```
================================================================================
🤖 MCP ChatBot - Terminal Interface
================================================================================

Commands:
  /clear  - Clear conversation history
  /quit   - Exit chatbot
  /help   - Show this help

Type your message and press Enter to chat.

================================================================================

You: Hello! How are you?

🤖 ChatNS: Hello! I'm doing well, thank you for asking. How can I assist you today?

You: What can you help me with?

🤖 ChatNS: I can help you with various tasks including answering questions,
explaining concepts, writing code, and more. What would you like to know?

You: /quit
👋 Goodbye!
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation history (start fresh) |
| `/quit` or `/exit` | Exit the chatbot |
| `/help` | Show available commands |

---

## Architecture

```
┌──────────────────┐
│  chatbot.py      │  Terminal Interface
│  (User Input)    │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ MCPManagerClient │  Gateway Client
│ (mcp_client/)    │
└────────┬─────────┘
         │
         ↓ JSON-RPC 2.0
┌──────────────────┐
│  MCP Gateway     │  Port 8700
│  (C++ Manager)   │
└────────┬─────────┘
         │
         ↓ MCP Protocol
┌──────────────────┐
│  ChatNS Server   │  MCP Server
│  (Python)        │
└──────────────────┘
```

### How it Works

1. **User input** → chatbot.py receives message
2. **Create message** → Add to conversation history
3. **Call chat_completion** via MCP Gateway (port 8700)
4. **ChatNS processes** with full conversation context
5. **Extract response** from MCP result
6. **Display to user** + add to history
7. **Repeat** - context maintained across messages

---

## Troubleshooting

### "Failed to connect to MCP Gateway"

**Cause:** MCP Manager is not running or gateway is not listening on port 8700.

**Solution:**

**Linux/macOS:**
```bash
# Check if port 8700 is open
nc -zv localhost 8700
# Or:
lsof -i :8700

# Start MCP Manager
cd /path/to/mcp-manager-standalone
./run.sh
```

**Windows:**
```cmd
REM Check if port 8700 is listening
netstat -an | findstr 8700

REM Start MCP Manager
cd C:\path\to\mcp-manager-standalone
run.bat
```

---

### "Error sending message"

**Possible causes:**

1. **ChatNS server not started** in MCP Manager GUI
   - Open MCP Manager
   - Check "ChatNS" status → should show "Running"
   - If not, click "Start" button

2. **Wrong model name** in chatbot configuration
   - Edit `chatbot.py` line 105
   - Ensure model is set to `"gpt-4.1-mini"`

3. **Network issue** between gateway and ChatNS server
   - Check MCP Manager logs
   - Verify ChatNS server is listening on configured port

---

### Python Not Found

**Linux:**
```bash
# Install Python 3
sudo apt install python3

# Or use full path
/usr/bin/python3 chatbot.py
```

**Windows:**
```cmd
REM Make sure Python is in PATH
REM Re-run Python installer and check "Add Python to PATH"

REM Or use full path
C:\Python39\python.exe chatbot.py
```

**macOS:**
```bash
# Install Python via Homebrew
brew install python3

# Or use macOS system Python
/usr/bin/python3 chatbot.py
```

---

### Permission Denied (Linux/macOS)

```bash
# Make scripts executable
chmod +x run.sh chatbot.py

# Then run
./run.sh
```

---

### Port Already in Use

If port 8700 is already in use by another application:

**Linux/macOS:**
```bash
# Find process using port 8700
lsof -i :8700

# Kill the process (replace PID with actual process ID)
kill -9 PID
```

**Windows:**
```cmd
REM Find process using port 8700
netstat -ano | findstr 8700

REM Kill the process (replace PID with actual process ID)
taskkill /PID PID /F
```

---

## Advanced Configuration

### Changing Gateway Host/Port

Edit `chatbot.py` line 238:

```python
# Default: localhost:8700
chatbot = MCPChatBot()

# Custom host/port:
chatbot = MCPChatBot(gateway_host='192.168.1.100', gateway_port=8700)
```

---

### Changing Model Settings

Edit `chatbot.py` lines 103-108:

```python
result = self.client.call_tool(
    session_id=self.session_id,
    tool_name="chat_completion",
    arguments={
        "messages": self.conversation_history,
        "model": "gpt-4.1-mini",      # Change model here
        "temperature": 0.7,            # 0.0-2.0 (creativity)
        "max_tokens": 1000             # Response length
    }
)
```

---

### Running on Remote MCP Manager

If MCP Manager is running on a remote machine:

**Linux/macOS:**
```bash
# Edit chatbot.py or use environment variable
export MCP_GATEWAY_HOST=192.168.1.100
export MCP_GATEWAY_PORT=8700
python3 chatbot.py
```

**Windows:**
```cmd
REM Set environment variables
set MCP_GATEWAY_HOST=192.168.1.100
set MCP_GATEWAY_PORT=8700
python chatbot.py
```

---

## MCP Protocol Details

The chatbot uses the Model Context Protocol (MCP) for communication:

```python
# Create session
session = client.create_session('ChatNS', credentials={})

# Call tool
result = client.call_tool(
    session_id=session.session_id,
    tool_name="chat_completion",
    arguments={
        "messages": conversation_history,
        "model": "gpt-4.1-mini",
        "temperature": 0.7,
        "max_tokens": 1000
    }
)
```

### Response Format

ChatNS returns responses in this format:

```json
{
  "status": "success",
  "response": "AI response text here...",
  "model": "gpt-4.1-mini",
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}
```

The chatbot automatically extracts only the `"response"` field for display.

---

## Future Enhancements

Possible future features:

1. **System prompts** - Configurable personality
2. **Multi-turn context** - Longer conversations
3. **Tool calling** - ChatNS can use DevOps/Confluence tools
4. **Export chat** - Save conversations to file
5. **Rich formatting** - Markdown rendering in terminal
6. **Streaming responses** - Real-time token output
7. **Voice input** - Speech-to-text integration
8. **Chat history** - Search and replay past conversations

---

## License

Part of the ChatNS Summer School project.

---

## Support

- **Issues:** https://github.com/goeiespullen/mcp-chatbot-standalone/issues
- **MCP Manager:** https://github.com/goeiespullen/mcp-manager-standalone

---

## Related Projects

- **MCP Manager Standalone** - C++/Qt GUI for managing MCP servers
  - https://github.com/goeiespullen/mcp-manager-standalone

- **Model Context Protocol** - Official MCP specification
  - https://modelcontextprotocol.io/

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
