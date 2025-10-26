"""
MCP Manager Client - Python client for connecting to MCP Gateway

This client connects to the C++ MCP Manager Gateway (port 8700) and provides:
- Session-based MCP server access with credential injection
- Multi-tenant support (each client gets isolated server instance)
- Tool calling through session proxy

Usage:
    client = MCPManagerClient('localhost', 8700)
    session = client.create_session('Confluence', {
        'CONFLUENCE_API_TOKEN': 'your-token-here'
    })
    result = client.call_tool(session['sessionId'], 'confluence-search', {
        'query': 'project documentation'
    })
"""

import socket
import json
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from queue import Queue, Empty

logger = logging.getLogger(__name__)


@dataclass
class MCPSession:
    """Represents an active MCP session"""
    session_id: str
    server_type: str
    created: str
    active: bool = True


class MCPManagerClient:
    """Client for MCP Manager Gateway"""

    def __init__(self, host: str = 'localhost', port: int = 8700):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.request_id = 0
        self.pending_requests: Dict[int, Queue] = {}
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> bool:
        """Connect to MCP Manager Gateway"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.running = True

            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            logger.info(f"Connected to MCP Manager Gateway at {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to gateway: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from gateway"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        logger.info("Disconnected from MCP Manager Gateway")

    def _receive_loop(self):
        """Background thread to receive responses"""
        buffer = ""

        while self.running and self.socket:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    logger.warning("Connection closed by gateway")
                    self.connected = False
                    break

                buffer += data

                # Process complete messages (line-delimited JSON)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        message = json.loads(line)
                        self._handle_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")

            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}")
                break

    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from gateway"""
        # Check if it's a response to our request
        if 'id' in message and message['id'] in self.pending_requests:
            request_id = message['id']
            self.pending_requests[request_id].put(message)
        else:
            # Notification or unsolicited message
            logger.debug(f"Received notification: {message}")

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 60.0) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response"""
        if not self.connected:
            raise RuntimeError("Not connected to gateway")

        self.request_id += 1
        request_id = self.request_id

        request = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params or {}
        }

        # Create response queue
        response_queue = Queue()
        self.pending_requests[request_id] = response_queue

        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.socket.sendall(request_json.encode('utf-8'))
            logger.debug(f"Sent request: {method} (id={request_id})")

            # Wait for response
            try:
                response = response_queue.get(timeout=timeout)
            except Empty:
                raise TimeoutError(f"Request {request_id} timed out after {timeout}s")

            # Check for error
            if 'error' in response:
                error = response['error']
                raise RuntimeError(f"Gateway error ({error['code']}): {error['message']}")

            return response.get('result', {})

        finally:
            # Clean up
            del self.pending_requests[request_id]

    def create_session(self, server_type: str, credentials: Dict[str, str]) -> MCPSession:
        """
        Create a new MCP session with credential injection

        Args:
            server_type: Type of MCP server (e.g., 'Confluence', 'AzureDevOps')
            credentials: Dictionary of environment variables to inject
                        (e.g., {'CONFLUENCE_API_TOKEN': 'token123'})

        Returns:
            MCPSession object with session details
        """
        result = self._send_request('mcp-manager/create-session', {
            'serverType': server_type,
            'credentials': credentials
        })

        session = MCPSession(
            session_id=result['sessionId'],
            server_type=result['serverType'],
            created=result['created']
        )

        logger.info(f"Created session {session.session_id} for {server_type}")
        return session

    def destroy_session(self, session_id: str) -> bool:
        """Destroy an MCP session"""
        result = self._send_request('mcp-manager/destroy-session', {
            'sessionId': session_id
        })

        logger.info(f"Destroyed session {session_id}")
        return result.get('destroyed', False)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions for this client"""
        result = self._send_request('mcp-manager/list-sessions')
        return result.get('sessions', [])

    def list_servers(self) -> Dict[str, Any]:
        """
        List all MCP servers and their status from the gateway

        Returns:
            Dictionary with 'servers' array and 'count' of servers
        """
        result = self._send_request('mcp-manager/list-servers')
        return result

    def call_tool(self, session_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool through a session

        Args:
            session_id: Active session ID
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result
        """
        result = self._send_request('tools/call', {
            'sessionId': session_id,
            'name': tool_name,
            'arguments': arguments
        })

        logger.debug(f"Tool call {tool_name} in session {session_id} completed")
        return result

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Example usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Example 1: Basic connection test
    print("Testing MCP Manager Client...")

    with MCPManagerClient() as client:
        # Create Confluence session with credentials
        session = client.create_session('Confluence', {
            'CONFLUENCE_API_TOKEN': 'your-token-here',
            'CONFLUENCE_USERNAME': 'your-email@example.com'
        })

        print(f"Created session: {session.session_id}")

        # List active sessions
        sessions = client.list_sessions()
        print(f"Active sessions: {len(sessions)}")

        # Call a tool (example)
        try:
            result = client.call_tool(
                session.session_id,
                'confluence-search',
                {'query': 'test'}
            )
            print(f"Tool result: {result}")
        except Exception as e:
            print(f"Tool call failed: {e}")

        # Destroy session
        client.destroy_session(session.session_id)
        print("Session destroyed")
