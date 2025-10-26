"""
MCP Protocol Client - Communicates with MCP servers via stdio protocol.

This client implements the Model Context Protocol to communicate with
MCP servers like mcp-atlassian.
"""
import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    command: List[str]
    args: List[str]
    env: Dict[str, str]
    name: str


class MCPProtocolClient:
    """Client for communicating with MCP servers via stdio."""

    def __init__(self, server_config: MCPServerConfig):
        """Initialize the MCP protocol client.

        Args:
            server_config: Configuration for the MCP server
        """
        self.config = server_config
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the MCP server subprocess."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.env)

            # Build command
            command = self.config.command + self.config.args

            logger.info(f"Starting MCP server '{self.config.name}': {' '.join(command)}")

            # Start subprocess
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
                text=True,
            )

            logger.info(f"MCP server '{self.config.name}' started with PID {self.process.pid}")

            # Send initialize request (required by MCP protocol)
            await self._initialize()

        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.config.name}': {e}")
            raise

    async def _initialize(self) -> None:
        """Initialize MCP session."""
        async with self._lock:
            self.request_id += 1
            request_id = str(self.request_id)

            # Build initialize request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "dashboard-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }

            try:
                # Send request
                request_json = json.dumps(request) + "\n"
                logger.debug(f"Sending initialize: {request_json.strip()}")

                self.process.stdin.write(request_json)
                self.process.stdin.flush()

                # Read response
                response_line = self.process.stdout.readline()
                if not response_line:
                    raise RuntimeError("MCP server closed stdout during initialize")

                logger.debug(f"Received initialize response: {response_line.strip()}")

                response = json.loads(response_line)

                # Check for errors
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(f"Initialize error: {error.get('message', str(error))}")

                logger.info(f"MCP server '{self.config.name}' initialized successfully")

                # Send initialized notification
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                notification_json = json.dumps(notification) + "\n"
                self.process.stdin.write(notification_json)
                self.process.stdin.flush()

            except Exception as e:
                logger.error(f"Error during initialize: {e}")
                raise

    async def stop(self) -> None:
        """Stop the MCP server subprocess."""
        if self.process:
            logger.info(f"Stopping MCP server '{self.config.name}'")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"MCP server '{self.config.name}' did not terminate, killing")
                self.process.kill()
            self.process = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            String result from the tool
        """
        async with self._lock:
            if not self.process:
                raise RuntimeError("MCP server not started")

            self.request_id += 1
            request_id = str(self.request_id)

            # Build JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            try:
                # Send request
                request_json = json.dumps(request) + "\n"
                logger.debug(f"Sending to MCP server: {request_json.strip()}")

                self.process.stdin.write(request_json)
                self.process.stdin.flush()

                # Read response
                response_line = self.process.stdout.readline()
                if not response_line:
                    raise RuntimeError("MCP server closed stdout")

                logger.debug(f"Received from MCP server: {response_line.strip()}")

                response = json.loads(response_line)

                # Check for errors
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(f"MCP tool error: {error.get('message', str(error))}")

                # Extract result
                if "result" not in response:
                    raise RuntimeError("No result in MCP response")

                result = response["result"]

                # MCP tools return content in different formats
                if isinstance(result, dict):
                    if "content" in result:
                        # Extract text from content array
                        content = result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            # Return first text content
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    return item.get("text", "")
                        return str(content)
                    return json.dumps(result)

                return str(result)

            except Exception as e:
                logger.error(f"Error calling tool '{tool_name}': {e}")
                raise

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        async with self._lock:
            if not self.process:
                raise RuntimeError("MCP server not started")

            self.request_id += 1
            request_id = str(self.request_id)

            # Build JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list",
                "params": {}
            }

            try:
                # Send request
                request_json = json.dumps(request) + "\n"
                logger.debug(f"Sending to MCP server: {request_json.strip()}")

                self.process.stdin.write(request_json)
                self.process.stdin.flush()

                # Read response
                response_line = self.process.stdout.readline()
                if not response_line:
                    raise RuntimeError("MCP server closed stdout")

                logger.debug(f"Received from MCP server: {response_line.strip()}")

                response = json.loads(response_line)

                # Check for errors
                if "error" in response:
                    error = response["error"]
                    raise RuntimeError(f"MCP error: {error.get('message', str(error))}")

                # Extract result
                if "result" not in response:
                    raise RuntimeError("No result in MCP response")

                result = response["result"]

                if isinstance(result, dict) and "tools" in result:
                    return result["tools"]

                return []

            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                raise

    def __del__(self):
        """Cleanup on deletion."""
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
