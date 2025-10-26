# Quick Installation Guide

Choose your platform:

---

## 🐧 Linux

```bash
# Install Python (if needed)
sudo apt install python3 python3-pip

# Download chatbot
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone

# Make executable
chmod +x run.sh

# Run
./run.sh
```

---

## 🪟 Windows

### Step 1: Install Python

1. Download: https://www.python.org/downloads/
2. Run installer
3. ✅ **Check "Add Python to PATH"**
4. Click "Install Now"

### Step 2: Download Chatbot

**Option A - With Git:**
```cmd
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone
```

**Option B - Download ZIP:**
1. Go to: https://github.com/goeiespullen/mcp-chatbot-standalone
2. Click "Code" → "Download ZIP"
3. Extract to folder (e.g., `C:\mcp-chatbot-standalone`)
4. Open Command Prompt:
   ```cmd
   cd C:\mcp-chatbot-standalone
   ```

### Step 3: Run

```cmd
run.bat
```

---

## 🍎 macOS

```bash
# Install Python via Homebrew
brew install python3

# Or download from: https://www.python.org/downloads/macos/

# Download chatbot
git clone https://github.com/goeiespullen/mcp-chatbot-standalone.git
cd mcp-chatbot-standalone

# Make executable
chmod +x run.sh

# Run
./run.sh
```

---

## Prerequisites

Before running the chatbot:

1. **MCP Manager must be running**
   - Download: https://github.com/goeiespullen/mcp-manager-standalone
   - Start the gateway on port 8700

2. **ChatNS MCP Server configured**
   - Open MCP Manager GUI
   - Start "ChatNS" server

---

## Troubleshooting

**"Failed to connect to MCP Gateway"**
- Start MCP Manager first
- Verify gateway is on port 8700

**"Python not found"**
- Reinstall Python with "Add to PATH" checked
- Or use full path: `C:\Python39\python.exe chatbot.py`

**More help:** See [README.md](README.md)

---

## Quick Start

```bash
# Terminal 1: Start MCP Manager
cd /path/to/mcp-manager-standalone
./run.sh  # Linux/macOS
run.bat   # Windows

# Terminal 2: Start Chatbot
cd /path/to/mcp-chatbot-standalone
./run.sh  # Linux/macOS
run.bat   # Windows
```

**Chat Commands:**
- `/clear` - Clear conversation history
- `/quit` - Exit chatbot
- `/help` - Show help

---

## Support

- Full documentation: [README.md](README.md)
- Issues: https://github.com/goeiespullen/mcp-chatbot-standalone/issues
- MCP Manager: https://github.com/goeiespullen/mcp-manager-standalone
