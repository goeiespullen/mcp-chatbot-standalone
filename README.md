# MCP Terminal ChatBot

Een eenvoudige terminal-based chatbot die via de MCP Manager Gateway connected met ChatNS LLM.

## Features

- ✅ **Direct connection** via MCP Manager Gateway (port 8700)
- ✅ **ChatNS LLM integration** via MCP protocol
- ✅ **Conversation history** - behoudt context tussen berichten
- ✅ **Clean interface** - alleen de AI response, geen JSON formatting
- ✅ **Interactive commands** - `/clear`, `/quit`, `/help`

## Vereisten

1. **MCP Manager** moet draaien met gateway op port 8700
2. **ChatNS MCP Server** moet gestart zijn in de MCP Manager
3. **Python 3.7+** met asyncio support

## Installatie

De chatbot gebruikt de bestaande `mcp_client` module, geen extra dependencies nodig.

## Gebruik

### Start de chatbot:

```bash
python3 chatbot.py
```

### Interactieve chat:

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

You: /quit
👋 Goodbye!
```

### Commando's:

- **`/clear`** - Wist de conversatie geschiedenis (start fresh conversation)
- **`/quit`** of **`/exit`** - Sluit de chatbot af
- **`/help`** - Toont help informatie

## Architectuur

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
         ↓
┌──────────────────┐
│  MCP Gateway     │  Port 8700
│  (C++ Manager)   │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  ChatNS Server   │  MCP Server
│  (Python)        │
└──────────────────┘
```

## Conversatie Flow

1. **User input** → chatbot.py
2. **Create message** → Add to conversation history
3. **Call chat_completion tool** via MCP Gateway
4. **ChatNS processes** with full conversation context
5. **Extract response** from MCP result
6. **Display to user** + add to history
7. **Repeat** - context maintained

## Technische Details

### MCP Protocol

De chatbot gebruikt het Model Context Protocol (MCP) voor communicatie:

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

### Response Parsing

ChatNS retourneert responses in het formaat:

```json
{
  "status": "success",
  "response": "AI response text here...",
  "model": "gpt-4.1-mini",
  "usage": {...}
}
```

De chatbot extraheert automatisch alleen de `"response"` field.

### Session Management

- Bij start: Maak ChatNS sessie via gateway
- Tijdens chat: Gebruik dezelfde sessie ID
- Bij afsluiten: Vernietig sessie netjes
- Credentials: Geen nodig (ChatNS gebruikt environment vars)

## Troubleshooting

### "Failed to connect to MCP Gateway"

**Oplossing:**
1. Check of MCP Manager draait: `ss -tlnp | grep 8700`
2. Start MCP Manager: `cd mcp-manager/build && ./mcp-manager`
3. Check of gateway listener op 8700 staat

### "Error sending message"

**Mogelijke oorzaken:**
1. ChatNS server niet gestart in MCP Manager GUI
2. Model naam incorrect (moet `gpt-4.1-mini` zijn)
3. Network issue tussen gateway en ChatNS server

**Debug:**
```bash
# Check ChatNS server status
# In MCP Manager GUI: verify "ChatNS" shows "Running"

# Test direct connection
python3 test_get_current_iteration.py
```

### Responses zijn JSON formatted

**Oplossing:**
Dit is gefixed in de laatste versie. De chatbot extraheert nu automatisch
de `"response"` field uit de JSON.

## Uitbreidingen

Mogelijke toekomstige features:

1. **System prompts** - Configureerbare personality
2. **Multi-turn context** - Langere conversaties
3. **Tool calling** - ChatNS kan DevOps/Confluence tools gebruiken
4. **Export chat** - Sla gesprekken op naar file
5. **Rich formatting** - Markdown rendering in terminal
6. **Streaming responses** - Real-time token output

## Voorbeeld Sessie

```bash
$ python3 chatbot.py

✅ Connected to MCP Gateway at localhost:8700
✅ Created ChatNS session: abc123...

================================================================================
🤖 MCP ChatBot - Terminal Interface
================================================================================

You: Explain the MCP protocol in simple terms

🤖 ChatNS: The Model Context Protocol (MCP) is a standardized way for AI
applications to communicate with different services and tools. Think of it
as a universal translator that allows chatbots to access databases, APIs,
and other resources through a consistent interface. Instead of writing
custom code for each integration, MCP provides a unified protocol that
makes it easy to connect AI models to various data sources and tools.

You: Can you give an example?

🤖 ChatNS: Sure! Imagine you're building a chatbot for a development team.
With MCP, your chatbot can:

1. Fetch sprint data from Azure DevOps
2. Search documentation in Confluence
3. Query knowledge bases
4. Execute custom tools

All using the same MCP protocol. The chatbot sends standard MCP messages
like "tools/call" with the tool name and parameters, and receives responses
in a consistent format. This makes it much easier to build powerful AI
assistants that can interact with multiple systems.

You: /quit
👋 Goodbye!

✅ Session destroyed: abc123...
✅ Disconnected from gateway
```

## Licentie

Onderdeel van het ChatNS Summer School project.
