#!/usr/bin/env python3
"""
ChatNSbot - Terminal-based chatbot powered by ChatNS LLM.

Connects to MCP Manager Gateway to provide an interactive
chat experience using the ChatNS MCP server.
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add mcp_client to path
sys.path.insert(0, str(Path(__file__).parent / "mcp_client"))

from mcp_client.mcp_manager_client import MCPManagerClient

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ChatNSBot:
    """ChatNSbot - Terminal interface using MCP Gateway and ChatNS LLM."""

    def __init__(self, gateway_host: str = 'localhost', gateway_port: int = 8700):
        """
        Initialize ChatNSbot.

        Args:
            gateway_host: MCP Gateway hostname
            gateway_port: MCP Gateway port (default 8700)
        """
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.client: MCPManagerClient = None
        self.session_id: str = None
        self.conversation_history: List[Dict[str, str]] = []

    def connect(self) -> bool:
        """Connect to MCP Gateway and create ChatNS session."""
        try:
            # Connect to gateway
            self.client = MCPManagerClient(self.gateway_host, self.gateway_port)
            if not self.client.connect():
                print("❌ Failed to connect to MCP Gateway")
                return False

            print(f"✅ Connected to MCP Gateway at {self.gateway_host}:{self.gateway_port}")

            # Create session for ChatNS
            # No credentials needed for ChatNS (uses environment variables)
            session = self.client.create_session('ChatNS', {})
            self.session_id = session.session_id

            print(f"✅ Created ChatNS session: {self.session_id}")
            return True

        except Exception as e:
            print(f"❌ Connection error: {e}")
            logger.error(f"Connection failed: {e}", exc_info=True)
            return False

    def disconnect(self):
        """Disconnect from gateway and clean up session."""
        if self.client and self.session_id:
            try:
                self.client.destroy_session(self.session_id)
                print(f"\n✅ Session destroyed: {self.session_id}")
            except Exception as e:
                logger.warning(f"Failed to destroy session: {e}")

            self.client.disconnect()
            print("✅ Disconnected from gateway")

    async def send_message(self, user_message: str) -> str:
        """
        Send a message to ChatNS and get response.

        Args:
            user_message: User's message

        Returns:
            ChatNS response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        try:
            # Call chat_completion tool via gateway
            result = self.client.call_tool(
                session_id=self.session_id,
                tool_name="chat_completion",
                arguments={
                    "messages": self.conversation_history,
                    "model": "gpt-4.1-mini",  # Use the correct model name
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )

            # Extract response from result
            response_text = self._extract_response(result)

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            return response_text

        except Exception as e:
            error_msg = f"Error sending message: {e}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"

    def _extract_response(self, result: Dict[str, Any]) -> str:
        """
        Extract assistant response from MCP tool result.

        Args:
            result: MCP tool call result

        Returns:
            Extracted response text
        """
        # MCP format: {"content": [{"type": "text", "text": "..."}], "isError": false}
        if isinstance(result, dict):
            if result.get("isError", False):
                # Error response
                content = result.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "Error occurred")
                return "Error occurred"

            # Success response
            content = result.get("content", [])
            if content and isinstance(content, list):
                # Extract text from first content item
                text = content[0].get("text", "")

                # ChatNS returns JSON with different formats
                try:
                    import json
                    response_json = json.loads(text)

                    # Format 1: {"status": "success", "response": "...", "model": "..."}
                    if "response" in response_json:
                        return response_json["response"]

                    # Format 2: OpenAI format with 'choices' array
                    if "choices" in response_json:
                        choices = response_json["choices"]
                        if choices and len(choices) > 0:
                            message = choices[0].get("message", {})
                            return message.get("content", text)

                except (json.JSONDecodeError, KeyError):
                    # If not JSON, return as-is
                    pass

                return text

        return str(result)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print("🗑️  Conversation history cleared")

    async def run(self):
        """Run the interactive chat loop."""
        print("\n" + "="*80)
        print("🤖 ChatNSbot - Powered by ChatNS LLM")
        print("="*80)
        print("\nCommands:")
        print("  /clear  - Clear conversation history")
        print("  /quit   - Exit ChatNSbot")
        print("  /help   - Show this help")
        print("\nType your message and press Enter to chat.\n")
        print("="*80 + "\n")

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    command = user_input[1:].lower()

                    if command == "quit" or command == "exit":
                        print("\n👋 Goodbye!")
                        break
                    elif command == "clear":
                        self.clear_history()
                        continue
                    elif command == "help":
                        print("\nCommands:")
                        print("  /clear  - Clear conversation history")
                        print("  /quit   - Exit ChatNSbot")
                        print("  /help   - Show this help\n")
                        continue
                    else:
                        print(f"❓ Unknown command: /{command}")
                        print("Type /help for available commands\n")
                        continue

                # Send message to ChatNS
                print("\n🤖 ChatNS: ", end="", flush=True)
                response = await self.send_message(user_input)
                print(response)
                print()  # Empty line for readability

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                logger.error(f"Chat loop error: {e}", exc_info=True)


async def main():
    """Main entry point."""
    chatbot = ChatNSBot()

    # Connect to gateway
    if not chatbot.connect():
        print("\n❌ Failed to start ChatNSbot")
        print("Make sure MCP Manager is running with gateway on port 8700")
        sys.exit(1)

    try:
        # Run chat loop
        await chatbot.run()
    finally:
        # Clean up
        chatbot.disconnect()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
