"""
Gateway-enabled MCP Client for Dashboard

This client uses the MCP Manager Gateway for session-based access to MCP servers.
Credentials are injected per session, enabling multi-tenant architecture.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import from same directory
try:
    from mcp_manager_client import MCPManagerClient, MCPSession
except ImportError:
    # Try package import as fallback
    from mcp_client.mcp_manager_client import MCPManagerClient, MCPSession

logger = logging.getLogger(__name__)


class GatewayDashboardClient:
    """Dashboard MCP client that uses the gateway for session-based access."""

    # Server name mapping - maps lowercase dashboard names to MCP Manager server names
    SERVER_TYPE_MAP = {
        'devops': 'Azure DevOps',
        'azure devops': 'Azure DevOps',
        'azuredevops': 'Azure DevOps',
        'confluence': 'Confluence',
        'confluence_old': 'Confluence',
        'chatns': 'ChatNS',
        'demo': 'Demo MCP',
    }

    def __init__(self, gateway_host: str = 'localhost', gateway_port: int = 8700):
        """
        Initialize gateway client.

        Args:
            gateway_host: Gateway hostname
            gateway_port: Gateway port (default 8700)
        """
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.client: Optional[MCPManagerClient] = None
        self.sessions: Dict[str, MCPSession] = {}  # server_type -> session
        self._connected = False

    def connect(self) -> bool:
        """Connect to gateway."""
        try:
            self.client = MCPManagerClient(self.gateway_host, self.gateway_port)
            if self.client.connect():
                self._connected = True
                logger.info("Connected to MCP Gateway")
                return True
            else:
                logger.error("Failed to connect to gateway")
                return False
        except Exception as e:
            logger.error(f"Gateway connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from gateway and clean up sessions."""
        if self.client:
            # Destroy all sessions
            for server_type, session in self.sessions.items():
                try:
                    self.client.destroy_session(session.session_id)
                    logger.info(f"Destroyed session for {server_type}")
                except Exception as e:
                    logger.warning(f"Failed to destroy session for {server_type}: {e}")

            self.sessions.clear()
            self.client.disconnect()
            self._connected = False
            logger.info("Disconnected from gateway")

    def is_server_available(self, server_name: str) -> bool:
        """Check if a server is available via gateway."""
        # For gateway mode, we assume all configured servers are available
        # The gateway manages the server availability
        return server_name.lower() in self.SERVER_TYPE_MAP

    def list_available_servers(self) -> List[str]:
        """List all available server names."""
        return ['devops', 'confluence', 'chatns', 'demo']

    async def list_servers(self) -> Dict[str, Any]:
        """
        Get real-time server status from gateway.

        Returns:
            Dict with 'servers' array containing server info:
            - name: Server name
            - type: Server type
            - port: Server port
            - status: Server status string
            - isRunning: Boolean indicating if server is running
            - autoStart: Boolean indicating if server auto-starts
        """
        if not self._connected or not self.client:
            raise RuntimeError("Not connected to gateway")

        try:
            # Call gateway's list-servers method
            result = self.client.list_servers()
            return result

        except Exception as e:
            logger.error(f"Failed to list servers: {e}")
            return {"servers": [], "count": 0}

    def _get_credentials(self, server_type: str) -> Dict[str, str]:
        """Get credentials for a server type from environment."""
        credentials = {}

        if server_type.lower() == 'confluence':
            # Confluence credentials
            atlassian_email = os.environ.get("ATLASSIAN_EMAIL", "")
            atlassian_token = os.environ.get("ATLASSIAN_API_TOKEN", "")

            if atlassian_email:
                credentials['CONFLUENCE_USERNAME'] = atlassian_email
                credentials['ATLASSIAN_EMAIL'] = atlassian_email

            if atlassian_token:
                credentials['CONFLUENCE_API_TOKEN'] = atlassian_token
                credentials['ATLASSIAN_API_TOKEN'] = atlassian_token

        elif server_type.lower() in ['azuredevops', 'azure devops', 'devops']:
            # Azure DevOps credentials
            # Try multiple sources for PAT token
            azdo_pat = None

            p_local = Path(".azure_token")
            if p_local.exists():
                azdo_pat = p_local.read_text().strip()

            if not azdo_pat:
                azdo_pat = os.environ.get("AZDO_PAT", "").strip()

            if not azdo_pat:
                p_home = Path.home() / ".azdo_pat"
                if p_home.exists():
                    azdo_pat = p_home.read_text().strip()

            if azdo_pat:
                credentials['AZDO_PAT'] = azdo_pat
                credentials['AZURE_DEVOPS_PAT'] = azdo_pat

        return credentials

    def _ensure_session(self, server_type: str) -> MCPSession:
        """Ensure a session exists for the server type."""
        if not self._connected:
            raise RuntimeError("Not connected to gateway")

        # Check if we already have a session
        if server_type in self.sessions:
            return self.sessions[server_type]

        # Create new session with credentials
        credentials = self._get_credentials(server_type)

        if not credentials:
            logger.warning(f"No credentials found for {server_type}")

        logger.info(f"Creating session for {server_type} with {len(credentials)} credentials")

        try:
            session = self.client.create_session(server_type, credentials)
            self.sessions[server_type] = session
            logger.info(f"Created session {session.session_id} for {server_type}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session for {server_type}: {e}")
            raise

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> str:
        """
        Call a tool through the gateway.

        Args:
            server_name: Server name (e.g., 'devops', 'confluence', 'chatns')
            tool_name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool result as string
        """
        # Map server names to gateway server types (use class-level mapping)
        server_type = self.SERVER_TYPE_MAP.get(server_name.lower(), server_name)

        try:
            # Ensure session exists
            session = self._ensure_session(server_type)

            # Call tool through gateway
            result = self.client.call_tool(
                session.session_id,
                tool_name,
                kwargs
            )

            # Format result for dashboard compatibility
            if isinstance(result, dict):
                import json
                return json.dumps(result, indent=2)
            else:
                return str(result)

        except Exception as e:
            error_msg = f"Gateway tool call failed for {server_name}.{tool_name}: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    # Convenience methods matching DashboardMCPClient interface

    async def list_projects(self) -> List[str]:
        """Get list of Azure DevOps projects."""
        try:
            result = await self.call_tool("devops", "list_projects")
            # Parse result
            if "Found" in result and "projects:" in result:
                projects_part = result.split("projects:")[-1].strip()
                if projects_part:
                    return [p.strip() for p in projects_part.split(",")]
            return []
        except Exception:
            return []

    async def list_teams(self, project: str) -> List[str]:
        """Get list of teams for a project."""
        try:
            result = await self.call_tool("devops", "list_teams", project=project)
            if "Found" in result and "teams in" in result:
                teams_part = result.split(":")[-1].strip()
                if teams_part:
                    return [t.strip() for t in teams_part.split(",")]
            return []
        except Exception:
            return []

    async def refresh_data(self, project: str = None, teams: List[str] = None,
                          require_effort: bool = False) -> tuple[bool, str]:
        """Refresh sprint data."""
        try:
            result = await self.call_tool("devops", "refresh_data",
                                        project=project, teams=teams,
                                        require_effort=require_effort)
            success = "successful" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    async def health_check(self, server_name: str) -> str:
        """Check server health."""
        try:
            return await self.call_tool(server_name, "health_check")
        except Exception as e:
            return f"❌ Health check failed: {str(e)}"

    async def get_work_items(self, project: str, wiql_query: str = None, limit: int = 50) -> str:
        """Get work items using WIQL query."""
        return await self.call_tool("devops", "get_work_items",
                                   project=project, wiql_query=wiql_query, limit=limit)

    async def get_work_item_details(self, project: str, work_item_ids: List[int],
                                   fields: List[str] = None) -> str:
        """Get detailed information for specific work items."""
        return await self.call_tool("devops", "get_work_item_details",
                                   project=project, work_item_ids=work_item_ids, fields=fields)

    async def list_confluence_spaces(self, include_personal: bool = False) -> List[Dict[str, str]]:
        """Get list of Confluence spaces."""
        try:
            result = await self.call_tool("confluence", "list_spaces", include_personal=include_personal)

            # Try to parse as JSON first (MCP protocol format)
            try:
                import json
                result_json = json.loads(result)
                if "content" in result_json and isinstance(result_json["content"], list):
                    # Extract text from content array
                    text_parts = [c.get("text", "") for c in result_json["content"] if "text" in c]
                    full_text = " ".join(text_parts)

                    # Parse spaces from text (format: "KEY - Name (type)")
                    spaces = []
                    for line in full_text.split('\n'):
                        if ' - ' in line and '(' in line:
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                name_and_type = parts[1].rsplit('(', 1)
                                name = name_and_type[0].strip()
                                space_type = name_and_type[1].rstrip(')').strip() if len(name_and_type) > 1 else 'unknown'
                                spaces.append({'key': key, 'name': name, 'type': space_type})
                    return spaces
            except json.JSONDecodeError:
                pass

            # Fallback to old parsing method
            if "Data:" in result:
                data_part = result.split("Data: ", 1)[1]
                try:
                    import ast
                    spaces_data = ast.literal_eval(data_part)
                    return spaces_data if isinstance(spaces_data, list) else []
                except:
                    return []
            return []
        except Exception:
            return []

    async def search_confluence_pages(self, cql: str, limit: int = 100) -> List[Dict[str, str]]:
        """Search Confluence pages with CQL."""
        try:
            result = await self.call_tool("confluence", "search_pages", cql=cql, limit=limit)
            if "Data:" in result:
                data_part = result.split("Data: ", 1)[1]
                try:
                    import ast
                    pages_data = ast.literal_eval(data_part)
                    return pages_data if isinstance(pages_data, list) else []
                except:
                    return []
            return []
        except Exception:
            return []

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Example usage
if __name__ == '__main__':
    import asyncio

    logging.basicConfig(level=logging.DEBUG)

    async def main():
        print("Testing Gateway Dashboard Client...")

        # Set credentials in environment (normally done by dashboard)
        os.environ['ATLASSIAN_EMAIL'] = 'test@example.com'
        os.environ['ATLASSIAN_API_TOKEN'] = 'test-token-123'

        with GatewayDashboardClient() as client:
            # Test DevOps health check
            print("\n1. Testing DevOps health check...")
            result = await client.health_check('devops')
            print(f"Result: {result}")

            # Test Confluence health check
            print("\n2. Testing Confluence health check...")
            result = await client.health_check('confluence')
            print(f"Result: {result}")

            # Test listing projects
            print("\n3. Testing list projects...")
            projects = await client.list_projects()
            print(f"Projects: {projects}")

    asyncio.run(main())
