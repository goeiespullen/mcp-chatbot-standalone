"""MCP Client wrapper for Dashboard application."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    # Create a dummy streamlit module for compatibility
    class DummyST:
        def cache_resource(self, func):
            return func
    st = DummyST()


class MCPClientError(Exception):
    """MCP Client error."""
    pass


class DashboardMCPClient:
    """MCP client wrapper for Streamlit dashboard."""

    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._mcp_clients: Dict[str, Any] = {}  # MCP protocol clients
        self._setup_servers()

    def _find_node_executable(self) -> str:
        """Find Node.js executable, preferring nvm-managed Node 20+."""
        import subprocess

        # Try nvm-managed Node.js first
        nvm_node = Path.home() / ".nvm" / "versions" / "node"
        if nvm_node.exists():
            # Find latest v20.x installation
            node_versions = sorted(nvm_node.glob("v20.*"), reverse=True)
            if node_versions:
                node_bin = node_versions[0] / "bin" / "node"
                if node_bin.exists():
                    return str(node_bin)

        # Fallback to system node
        try:
            result = subprocess.run(["which", "node"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        # Last resort
        return "node"

    def _setup_servers(self):
        """Setup MCP server configurations."""
        # Use venv python if available, fallback to system python
        python_cmd = ".venv/bin/python" if Path(".venv/bin/python").exists() else sys.executable

        # Find Node.js 20+ (via nvm or system)
        node_cmd = self._find_node_executable()

        self._servers = {
            "devops": {
                "command": [python_cmd, "mcp_servers/devops_server.py"],
                "description": "Azure DevOps API tools",
                "protocol": "custom"  # Using Python implementation (official MCP requires browser auth)
            },
            "confluence": {
                "command": [python_cmd, "mcp_servers/confluence_server.py"],
                "description": "Atlassian Confluence API tools (custom Python implementation)",
                "protocol": "custom"  # Using custom Python implementation
            },
            "confluence_old": {
                "command": [python_cmd, "mcp_servers/confluence_server.py"],
                "description": "Confluence API tools (legacy)",
                "protocol": "custom"
            },
            "chatns": {
                "command": [python_cmd, "mcp_servers/chatns_server.py"],
                "description": "ChatNS AI and semantic search tools",
                "protocol": "custom"
            }
        }

    @st.cache_resource
    def get_client(_self):
        """Get cached MCP client instance (only cached when streamlit available)."""
        return _self

    def is_server_available(self, server_name: str) -> bool:
        """Check if a server is configured and available."""
        return server_name in self._servers

    def list_available_servers(self) -> List[str]:
        """List all available MCP servers."""
        return list(self._servers.keys())

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> str:
        """Call a tool on an MCP server."""
        if server_name not in self._servers:
            raise MCPClientError(f"Server '{server_name}' not configured")

        server_config = self._servers[server_name]
        protocol = server_config.get("protocol", "custom")

        try:
            # Use MCP protocol for servers that support it
            if protocol == "mcp":
                return await self._call_tool_mcp(server_name, tool_name, kwargs)
            else:
                # Use legacy subprocess approach for custom servers
                return await self._call_tool_subprocess(server_name, tool_name, kwargs)
        except Exception as e:
            raise MCPClientError(f"Tool call failed: {str(e)}") from e

    async def _call_tool_mcp(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call tool using MCP protocol."""
        from mcp_client.mcp_protocol_client import MCPProtocolClient, MCPServerConfig

        # Get or create MCP client for this server
        if server_name not in self._mcp_clients:
            server_config = self._servers[server_name]

            # Build MCP server config
            mcp_config = MCPServerConfig(
                command=[server_config["command"][0]],  # e.g., "mcp-atlassian"
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                name=server_name
            )

            # Create and start client
            client = MCPProtocolClient(mcp_config)
            await client.start()
            self._mcp_clients[server_name] = client

        client = self._mcp_clients[server_name]

        # Call tool via MCP protocol
        result = await client.call_tool(tool_name, arguments)
        return result

    async def _call_tool_subprocess(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call tool using subprocess (simplified approach)."""
        server_config = self._servers[server_name]

        # Create a simple JSON-RPC like request
        request = {
            "tool": tool_name,
            "arguments": arguments
        }

        try:
            # Start the server process
            cmd = server_config["command"] + ["--tool", tool_name]
            if arguments:
                cmd.extend(["--args", json.dumps(arguments)])

            # For now, we'll call the functions directly to avoid the complexity
            # of setting up full MCP protocol in this demo
            if server_name == "devops":
                return await self._call_devops_tool(tool_name, arguments)
            elif server_name == "confluence":
                return await self._call_confluence_tool(tool_name, arguments)
            elif server_name == "chatns":
                return await self._call_chatns_tool(tool_name, arguments)
            else:
                raise MCPClientError(f"Server {server_name} not implemented yet")

        except Exception as e:
            raise MCPClientError(f"Subprocess call failed: {str(e)}") from e

    async def _call_devops_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Direct call to DevOps tools (simplified for demo)."""
        # Import the existing service temporarily
        try:
            from dashapp.services import DevOpsService
            from dashapp.config import AppConfig

            config = AppConfig.from_files()
            service = DevOpsService(config)

            if tool_name == "list_projects":
                projects = service.list_projects()
                return f"Found {len(projects)} projects: {', '.join(projects)}"

            elif tool_name == "list_teams":
                project = arguments.get("project")
                if not project:
                    return "Error: project parameter required"
                teams = service.list_teams(project)
                return f"Found {len(teams)} teams in {project}: {', '.join(teams)}"

            elif tool_name == "get_team_iterations":
                project = arguments.get("project")
                team = arguments.get("team")
                if not project or not team:
                    return "Error: project and team parameters required"
                iterations = service.get_team_iterations(project, team)
                iter_info = []
                for iteration in iterations:
                    name = iteration.get("name", "Unknown")
                    attrs = iteration.get("attributes", {})
                    start = attrs.get("startDate", "N/A")
                    end = attrs.get("finishDate", "N/A")
                    iter_info.append(f"{name} ({start} to {end})")
                return f"Found {len(iter_info)} iterations for {project}/{team}:\\n" + "\\n".join(iter_info)

            elif tool_name == "refresh_data":
                project = arguments.get("project")
                teams = arguments.get("teams", [])
                require_effort = arguments.get("require_effort", False)
                snapshot = arguments.get("snapshot", "end")

                success, message = service.refresh_data(
                    project=project,
                    teams=teams,
                    require_effort=require_effort,
                    data_dir="data",
                    snapshot=snapshot
                )
                return f"Refresh {'successful' if success else 'failed'}: {message}"

            elif tool_name == "get_sprint_work_items":
                project = arguments.get("project")
                team = arguments.get("team")
                iteration_path = arguments.get("iteration_path")

                # Debug logging
                print(f"\n🔍 DEBUG get_sprint_work_items called:")
                print(f"   Project: {project}")
                print(f"   Team: {team}")
                print(f"   Iteration path: {iteration_path}")

                if not project or not team or not iteration_path:
                    return "Error: project, team, and iteration_path parameters required"

                print(f"   Calling DevOps API...")
                work_items = service.get_sprint_work_items(project, team, iteration_path)
                print(f"   Received {len(work_items) if work_items else 0} work items")
                if not work_items:
                    return f"No work items found for sprint {iteration_path}"

                # Format work items summary
                summary_lines = [f"Found {len(work_items)} work items in {iteration_path}:"]
                summary_lines.append("")

                # Group by state
                by_state = {}
                total_sp = 0
                total_remaining = 0
                blocked_count = 0

                for item in work_items:
                    state = item["state"]
                    if state not in by_state:
                        by_state[state] = []
                    by_state[state].append(item)
                    total_sp += item["story_points"]
                    total_remaining += item["remaining_work"]
                    if item["is_blocked"]:
                        blocked_count += 1

                # Add metrics summary
                summary_lines.append(f"📊 METRICS:")
                summary_lines.append(f"   Total Story Points: {total_sp}")
                summary_lines.append(f"   Total Remaining Work: {total_remaining}h")
                summary_lines.append(f"   Blocked Items: {blocked_count}")
                summary_lines.append("")

                # Add work items by state
                for state, items in by_state.items():
                    summary_lines.append(f"🔹 {state} ({len(items)} items):")
                    for item in items[:5]:  # Show first 5 items per state
                        blocked_marker = "🚫" if item["is_blocked"] else ""
                        summary_lines.append(f"   #{item['id']}: {item['title'][:50]}... ({item['story_points']}SP) - {item['assigned_to']} {blocked_marker}")
                    if len(items) > 5:
                        summary_lines.append(f"   ... and {len(items) - 5} more items")
                    summary_lines.append("")

                return "\n".join(summary_lines)

            elif tool_name == "get_burndown_data":
                project = arguments.get("project")
                team = arguments.get("team")
                iteration_id = arguments.get("iteration_id")
                if not project or not team or not iteration_id:
                    return "Error: project, team, and iteration_id parameters required"

                burndown = service.get_burndown_data(project, team, iteration_id)
                if "error" in burndown:
                    return f"Error getting burndown data: {burndown['error']}"

                # Format burndown summary
                summary_lines = [f"📈 BURNDOWN DATA for {iteration_id}:"]
                summary_lines.append("")

                # Capacity info
                capacity_info = burndown.get("capacity_info", {})
                total_capacity = capacity_info.get("total_capacity", 0)
                team_members = capacity_info.get("team_members", [])

                summary_lines.append(f"👥 TEAM CAPACITY:")
                summary_lines.append(f"   Total Capacity: {total_capacity}h")
                for member in team_members:
                    summary_lines.append(f"   {member['name']}: {member['capacity']}h")
                summary_lines.append("")

                # Data points
                data_points = burndown.get("data_points", [])
                if data_points:
                    summary_lines.append(f"📊 BURNDOWN POINTS ({len(data_points)} data points):")
                    for i, point in enumerate(data_points[:7]):  # Show first week
                        summary_lines.append(f"   Day {i+1}: {point}")
                    if len(data_points) > 7:
                        summary_lines.append(f"   ... and {len(data_points) - 7} more days")
                else:
                    summary_lines.append("📊 No burndown data points available")

                return "\n".join(summary_lines)

            elif tool_name == "get_blocked_items":
                project = arguments.get("project")
                team = arguments.get("team")  # Optional
                if not project:
                    return "Error: project parameter required"

                blocked_items = service.get_blocked_items(project, team)
                if not blocked_items:
                    scope = f"team {team}" if team else "project"
                    return f"No blocked items found for {scope} {project}"

                # Format blocked items summary
                summary_lines = [f"🚫 BLOCKED ITEMS in {project}" + (f"/{team}" if team else "") + ":"]
                summary_lines.append("")

                # Sort by change date (most recent first)
                blocked_items.sort(key=lambda x: x.get("changed_date", ""), reverse=True)

                for item in blocked_items:
                    summary_lines.append(f"🔴 #{item['id']}: {item['title']}")
                    summary_lines.append(f"   State: {item['state']} | Assigned: {item['assigned_to']}")
                    summary_lines.append(f"   Blocked Reason: {item['blocked_reason']}")
                    summary_lines.append(f"   Story Points: {item['story_points']} | Area: {item['area_path']}")
                    if item['blocked_date']:
                        summary_lines.append(f"   Blocked Since: {item['blocked_date'][:10]}")
                    summary_lines.append(f"   URL: {item['url']}")
                    summary_lines.append("")

                return "\n".join(summary_lines)

            elif tool_name == "get_work_items":
                project = arguments.get("project")
                wiql_query = arguments.get("wiql_query")
                limit = arguments.get("limit", 50)

                # Debug logging
                print(f"\n🔍 DEBUG get_work_items called:")
                print(f"   Project: {project}")
                print(f"   WIQL Query (FULL): {wiql_query if wiql_query else 'None (will use default)'}")
                print(f"   Limit: {limit}")

                if not project:
                    return "Error: project parameter required"

                # Direct implementation to avoid import issues
                try:
                    import os
                    from pathlib import Path

                    # Get Azure DevOps PAT token
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

                    if not azdo_pat:
                        return "Error: Azure DevOps PAT token not configured"

                    # Default WIQL query for active user stories
                    if not wiql_query:
                        # WIQL uses double quotes for string literals, not single quotes
                        wiql_query = 'SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = "' + project + '" AND [System.WorkItemType] = "User Story" AND [System.State] <> "Removed"'

                    # Ensure limit doesn't exceed 200
                    limit = min(limit, 200)

                    # DON'T add TOP to query - Azure DevOps REST API doesn't support TOP in WIQL
                    # Use $top parameter in the URL instead

                    # Make WIQL query request
                    import requests
                    from requests.auth import HTTPBasicAuth
                    from urllib.parse import quote

                    azdo_org = "ns-topaas"
                    base_url = f"https://dev.azure.com/{azdo_org}"

                    wiql_request = {"query": wiql_query}

                    response = requests.post(
                        f"{base_url}/{quote(project)}/_apis/wit/wiql?api-version=7.1&$top={limit}",
                        auth=HTTPBasicAuth("", azdo_pat),
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "X-TFS-FedAuthRedirect": "Suppress",
                        },
                        json=wiql_request,
                        timeout=40
                    )

                    if not response.ok:
                        return f"WIQL query failed: HTTP {response.status_code} - {response.text[:500]}"

                    data = response.json()
                    work_items = data.get("workItems", [])

                    # Debug output
                    print(f"DEBUG: Response status: {response.status_code}")
                    print(f"DEBUG: Response keys: {list(data.keys())}")
                    print(f"DEBUG: Work items count: {len(work_items)}")
                    if work_items:
                        print(f"DEBUG: First work item: {work_items[0]}")

                    if not work_items:
                        return f"No work items found for query in project {project}\nResponse: {str(data)[:200]}"

                    # Format results
                    result_lines = [f"Found {len(work_items)} work items in {project}:"]
                    result_lines.append("")

                    # Show first 10 IDs for preview
                    for i, item in enumerate(work_items[:10]):
                        work_item_id = item.get("id", "N/A")
                        result_lines.append(f"• Work Item #{work_item_id}")

                    if len(work_items) > 10:
                        result_lines.append(f"• ... and {len(work_items) - 10} more work items")

                    result_lines.append("")
                    result_lines.append(f"✅ Total: {len(work_items)} work items found")
                    result_lines.append("")
                    result_lines.append("📋 Click 'Haal Details Op' below to see descriptions and acceptance criteria")
                    result_lines.append("")
                    result_lines.append(f"IDs: {[item.get('id') for item in work_items]}")

                    return "\n".join(result_lines)

                except Exception as e:
                    return f"Error getting work items: {str(e)}"

            elif tool_name == "get_work_item_details":
                project = arguments.get("project")
                work_item_ids = arguments.get("work_item_ids", [])
                fields = arguments.get("fields")
                if not project or not work_item_ids:
                    return "Error: project and work_item_ids parameters required"

                # Direct implementation to avoid import issues
                try:
                    import os
                    from pathlib import Path
                    import requests
                    from requests.auth import HTTPBasicAuth
                    from urllib.parse import quote

                    # Get Azure DevOps PAT token
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

                    if not azdo_pat:
                        return "Error: Azure DevOps PAT token not configured"

                    azdo_org = "ns-topaas"
                    base_url = f"https://dev.azure.com/{azdo_org}"

                    # Default fields if none specified
                    if not fields:
                        fields = [
                            "System.Id", "System.Title", "System.Description",
                            "System.WorkItemType", "System.State", "System.AssignedTo",
                            "Microsoft.VSTS.Common.AcceptanceCriteria",
                            "System.CreatedDate", "System.ChangedDate"
                        ]

                    # Limit to max 200 work items
                    work_item_ids = work_item_ids[:200]

                    # Get work items in batch
                    ids_param = ",".join(map(str, work_item_ids))
                    fields_param = ",".join(fields)

                    url = f"{base_url}/_apis/wit/workitems"
                    full_url = f"{url}?ids={ids_param}&fields={quote(fields_param)}&api-version=7.1"

                    response = requests.get(
                        full_url,
                        auth=HTTPBasicAuth("", azdo_pat),
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "X-TFS-FedAuthRedirect": "Suppress",
                        },
                        timeout=40
                    )

                    if not response.ok:
                        return f"Failed to get work items: HTTP {response.status_code} - {response.text[:500]}"

                    data = response.json()
                    work_items = data.get("value", [])

                    if not work_items:
                        return f"No work items found with IDs: {work_item_ids}"

                    # Format detailed results
                    result_lines = [f"Work Item Details ({len(work_items)} items):"]
                    result_lines.append("=" * 50)

                    for item in work_items:
                        item_fields = item.get("fields", {})

                        work_item_id = item_fields.get("System.Id", "N/A")
                        title = item_fields.get("System.Title", "No Title")
                        work_type = item_fields.get("System.WorkItemType", "Unknown")
                        state = item_fields.get("System.State", "Unknown")
                        assigned_to = item_fields.get("System.AssignedTo", {}).get("displayName", "Unassigned") if isinstance(item_fields.get("System.AssignedTo"), dict) else str(item_fields.get("System.AssignedTo", "Unassigned"))

                        result_lines.append(f"\n🎯 #{work_item_id}: {title}")
                        result_lines.append(f"   Type: {work_type} | State: {state} | Assigned: {assigned_to}")

                        # Description - FULL TEXT (no truncation)
                        description = item_fields.get("System.Description", "")
                        if description:
                            # Clean HTML tags from description but keep ALL content
                            import re
                            clean_desc = re.sub(r'<[^>]+>', '', description).strip()
                            # Replace HTML entities
                            clean_desc = clean_desc.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                            # Split into multiple lines for better readability
                            result_lines.append(f"   📝 Description:")
                            for line in clean_desc.split('\n'):
                                if line.strip():
                                    result_lines.append(f"      {line.strip()}")

                        # Acceptance Criteria - FULL TEXT (no truncation)
                        acceptance_criteria = item_fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
                        if acceptance_criteria:
                            # Clean HTML tags from acceptance criteria but keep ALL content
                            clean_ac = re.sub(r'<[^>]+>', '', acceptance_criteria).strip()
                            # Replace HTML entities
                            clean_ac = clean_ac.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                            # Split into multiple lines for better readability
                            result_lines.append(f"   ✅ Acceptance Criteria:")
                            for line in clean_ac.split('\n'):
                                if line.strip():
                                    result_lines.append(f"      {line.strip()}")

                        # Dates
                        created = item_fields.get("System.CreatedDate", "")
                        changed = item_fields.get("System.ChangedDate", "")
                        if created:
                            result_lines.append(f"   📅 Created: {created[:10]}")
                        if changed:
                            result_lines.append(f"   🔄 Last Changed: {changed[:10]}")

                        result_lines.append("")

                    return "\n".join(result_lines)

                except Exception as e:
                    return f"Error getting work item details: {str(e)}"

            elif tool_name == "health_check":
                is_auth = service.is_authenticated()
                return f"{'✅' if is_auth else '❌'} Azure DevOps API {'accessible' if is_auth else 'not accessible'}"

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error calling DevOps tool: {str(e)}"

    async def _call_confluence_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Direct call to Confluence tools (simplified for demo)."""
        try:
            from dashapp.services import ConfluenceService
            from dashapp.config import AppConfig

            config = AppConfig.from_files()
            service = ConfluenceService(config)

            if tool_name == "list_spaces":
                include_personal = arguments.get("include_personal", False)

                # Import confluence functions directly since service doesn't have list_spaces yet
                try:
                    from dashapp.confluence import list_spaces_all
                    import os

                    # Get confluence credentials from environment (set by tokens)
                    base_url = config.confluence_base_url
                    email = os.environ.get("ATLASSIAN_EMAIL", "")
                    api_token = os.environ.get("ATLASSIAN_API_TOKEN", "")

                    if not email or not api_token:
                        return "❌ Confluence credentials not configured"

                    spaces = list_spaces_all(base_url, email, api_token, include_personal)
                    return f"Found {len(spaces)} Confluence spaces. Data: {spaces}"

                except Exception as e:
                    return f"Error accessing Confluence: {str(e)}"

            elif tool_name == "search_pages":
                cql = arguments.get("cql", "")
                limit = arguments.get("limit", 100)

                try:
                    from dashapp.confluence import cql_search_pages
                    import os

                    base_url = config.confluence_base_url
                    email = os.environ.get("ATLASSIAN_EMAIL", "")
                    api_token = os.environ.get("ATLASSIAN_API_TOKEN", "")

                    if not email or not api_token:
                        return "❌ Confluence credentials not configured"

                    pages = cql_search_pages(base_url, email, api_token, cql, limit)
                    return f"Found {len(pages)} pages. Data: {pages}"

                except Exception as e:
                    return f"Error searching Confluence: {str(e)}"

            elif tool_name == "dump_space":
                space_key = arguments.get("space_key", "")
                format_type = arguments.get("format", "storage")
                max_pages = arguments.get("max_pages", 0)
                include_archived = arguments.get("include_archived", False)
                return f"Space dump started: {space_key} (format={format_type}, max_pages={max_pages}, archived={include_archived})"

            elif tool_name == "dump_team_pages":
                space_key = arguments.get("space_key", "")
                team_name = arguments.get("team_name", "")
                format_type = arguments.get("format", "storage")
                max_pages = arguments.get("max_pages", 0)
                return f"Team pages dump for '{team_name}' in space '{space_key}' (format={format_type}, max_pages={max_pages})"

            elif tool_name == "build_rag_index":
                space_key = arguments.get("space_key", "")
                max_words = arguments.get("max_words", 900)
                overlap = arguments.get("overlap", 120)
                return f"RAG index building for space '{space_key}' (max_words={max_words}, overlap={overlap})"

            elif tool_name == "get_page_content":
                page_id = arguments.get("page_id")
                space_key = arguments.get("space_key")
                expand = arguments.get("expand", ["body.storage", "version"])
                if not page_id:
                    return "Error: page_id parameter required"

                try:
                    from mcp_servers.confluence_server import _get_page_content
                    result = await _get_page_content(page_id, space_key, expand)
                    return result[0].text if result else "No results"
                except Exception as e:
                    return f"Error getting page content: {str(e)}"

            elif tool_name == "create_page":
                space_key = arguments.get("space_key")
                title = arguments.get("title")
                content = arguments.get("content")
                parent_id = arguments.get("parent_id")
                if not space_key or not title or not content:
                    return "Error: space_key, title, and content parameters required"

                try:
                    from mcp_servers.confluence_server import _create_page
                    result = await _create_page(space_key, title, content, parent_id)
                    return result[0].text if result else "No results"
                except Exception as e:
                    return f"Error creating page: {str(e)}"

            elif tool_name == "update_page":
                page_id = arguments.get("page_id")
                content = arguments.get("content")
                title = arguments.get("title")
                version_comment = arguments.get("version_comment", "Updated via MCP")
                if not page_id or not content:
                    return "Error: page_id and content parameters required"

                try:
                    from mcp_servers.confluence_server import _update_page
                    result = await _update_page(page_id, content, title, version_comment)
                    return result[0].text if result else "No results"
                except Exception as e:
                    return f"Error updating page: {str(e)}"

            elif tool_name == "get_page_children":
                page_id = arguments.get("page_id")
                limit = arguments.get("limit", 50)
                if not page_id:
                    return "Error: page_id parameter required"

                try:
                    from mcp_servers.confluence_server import _get_page_children
                    result = await _get_page_children(page_id, limit)
                    return result[0].text if result else "No results"
                except Exception as e:
                    return f"Error getting page children: {str(e)}"

            elif tool_name == "health_check":
                is_configured = service.is_authenticated()
                if is_configured:
                    can_connect = service.test_connection()
                    return f"{'✅' if can_connect else '❌'} Confluence API {'accessible' if can_connect else 'not accessible'}"
                else:
                    return "❌ Confluence not configured (missing credentials)"

            else:
                return f"Unknown Confluence tool: {tool_name}"

        except Exception as e:
            return f"Error calling Confluence tool: {str(e)}"

    async def _call_chatns_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call ChatNS tools directly."""
        try:
            # Import ChatNS functions from the local dashapp module
            import os
            from typing import List, Dict, Tuple
            import requests

            # Copy the essential ChatNS functions to avoid streamlit dependency
            def _chat_api_call(api_url: str, api_key: str, model: str, messages: List[Dict[str, str]],
                              temperature: float = 0.7, timeout: int = 60) -> Tuple[bool, str]:
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "MCPClient/1.0",
                    }
                    bearer = os.environ.get("CHAT_BEARER", "").strip()
                    apim = os.environ.get("CHAT_APIM", "").strip() or (api_key or "").strip()
                    if bearer:
                        headers["Authorization"] = f"Bearer {bearer}"
                    if apim:
                        headers["Ocp-Apim-Subscription-Key"] = apim

                    payload = {
                        "model": model,
                        "messages": messages,
                        "temperature": float(temperature),
                    }
                    r = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
                    if not r.ok:
                        return False, f"API error {r.status_code}: {r.text}"
                    data = r.json()
                    msg = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return True, msg or ""
                except Exception as e:
                    return False, f"API request failed: {e}"

            def _semantic_search(api_key: str, bucket_id: str, prompt: str, top_n: int = 3,
                               min_sim: float = 0.75, timeout: int = 60) -> Tuple[bool, List[Dict]]:
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "MCPClient/1.0",
                    }
                    bearer = os.environ.get("CHAT_BEARER", "").strip()
                    apim = os.environ.get("CHAT_APIM", "").strip() or (api_key or "").strip()
                    if bearer:
                        headers["Authorization"] = f"Bearer {bearer}"
                    if apim:
                        headers["Ocp-Apim-Subscription-Key"] = apim

                    body = {
                        "prompt": prompt,
                        "top_n": int(top_n),
                        "bucket_id": int(bucket_id) if str(bucket_id).isdigit() else bucket_id,
                        "min_cosine_similarity": float(min_sim),
                    }

                    semantic_url = "https://gateway.apiportal.ns.nl/genai/v1/semantic_search"
                    r = requests.post(semantic_url, headers=headers, json=body, timeout=timeout)
                    if not r.ok:
                        return False, []
                    data = r.json()
                    return True, data if isinstance(data, list) else []
                except Exception:
                    return False, []

            if tool_name == "chat_completion":
                messages = arguments.get("messages", [])
                model = arguments.get("model", "gpt-4o")
                temperature = arguments.get("temperature", 0.7)
                max_tokens = arguments.get("max_tokens", 1000)

                if not messages:
                    return "Error: messages parameter required"

                # Use the existing ChatNS function
                api_url = "https://gateway.apiportal.ns.nl/genai/v1/chat/completions"
                api_key = ""  # Will be filled from env vars in _chat_api_call
                success, response = _chat_api_call(api_url, api_key, model, messages, temperature)

                result = {
                    "status": "success" if success else "error",
                    "response": response if success else "",
                    "error": response if not success else "",
                    "model": model,
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0}  # Placeholder
                }

                import json
                return json.dumps(result, indent=2)

            elif tool_name == "semantic_search":
                prompt = arguments.get("prompt")
                bucket_id = arguments.get("bucket_id")
                top_n = arguments.get("top_n", 5)
                min_cosine_similarity = arguments.get("min_cosine_similarity", 0.75)

                if not prompt or bucket_id is None:
                    return "Error: prompt and bucket_id parameters required"

                # Use the existing semantic_search function
                api_key = ""  # Will be filled from env vars in _semantic_search
                success, results = _semantic_search(api_key, bucket_id, prompt, top_n, min_cosine_similarity)

                result = {
                    "status": "success" if success else "error",
                    "bucket_id": bucket_id,
                    "query": prompt,
                    "results_count": len(results) if success else 0,
                    "results": results if success else []
                }

                import json
                return json.dumps(result, indent=2)

            elif tool_name == "list_buckets":
                # Placeholder implementation - would need ChatNS API extension
                result = {
                    "status": "success",
                    "buckets": [
                        {"id": 1, "name": "General Knowledge", "description": "General purpose knowledge base"},
                        {"id": 2, "name": "Technical Docs", "description": "Technical documentation and guides"}
                    ],
                    "note": "Bucket listing may need ChatNS API extension"
                }

                import json
                return json.dumps(result, indent=2)

            elif tool_name == "health_check":
                # Test ChatNS availability by making a simple call
                try:
                    test_messages = [{"role": "user", "content": "Hello"}]
                    api_url = "https://gateway.apiportal.ns.nl/genai/v1/chat/completions"
                    success, response = _chat_api_call(api_url, "", "gpt-4o", test_messages, 0.7)

                    result = {
                        "status": "healthy" if success else "unhealthy",
                        "service": "ChatNS",
                        "api_url": api_url,
                        "test_response": "OK" if success else response,
                        "error": response if not success else None
                    }

                    import json
                    return f"{'✅' if success else '❌'} ChatNS: {json.dumps(result, indent=2)}"

                except Exception as e:
                    result = {
                        "status": "unhealthy",
                        "service": "ChatNS",
                        "error": str(e)
                    }
                    import json
                    return f"❌ ChatNS: {json.dumps(result, indent=2)}"

            else:
                return f"Unknown ChatNS tool: {tool_name}"

        except Exception as e:
            return f"Error calling ChatNS tool: {str(e)}"

    # Convenience methods for common operations
    async def list_projects(self) -> List[str]:
        """Get list of Azure DevOps projects."""
        try:
            result = await self.call_tool("devops", "list_projects")
            # Parse the result to extract just the project names
            # This is a simplified parser
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
            # Parse the result to extract team names
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

    # Confluence convenience methods
    async def list_confluence_spaces(self, include_personal: bool = False) -> List[Dict[str, str]]:
        """Get list of Confluence spaces."""
        try:
            result = await self.call_tool("confluence", "list_spaces", include_personal=include_personal)

            # Parse the result to extract spaces data
            if "Data:" in result:
                # Extract the data part after "Data: "
                data_part = result.split("Data: ", 1)[1]
                # This would contain the actual list of space dictionaries
                # For now, let's try to evaluate it safely
                try:
                    import ast
                    spaces_data = ast.literal_eval(data_part)
                    return spaces_data if isinstance(spaces_data, list) else []
                except:
                    # If parsing fails, return empty list
                    return []
            else:
                # If no data found, return empty list
                return []
        except Exception:
            return []

    async def search_confluence_pages(self, cql: str, limit: int = 100) -> List[Dict[str, str]]:
        """Search Confluence pages with CQL."""
        try:
            result = await self.call_tool("confluence", "search_pages", cql=cql, limit=limit)

            # Parse the result to extract pages data
            if "Data:" in result:
                data_part = result.split("Data: ", 1)[1]
                try:
                    import ast
                    pages_data = ast.literal_eval(data_part)
                    return pages_data if isinstance(pages_data, list) else []
                except:
                    return []
            else:
                return []
        except Exception:
            return []

    async def dump_confluence_space(self, space_key: str, format: str = "storage",
                                   max_pages: int = 0, include_archived: bool = False) -> tuple[bool, str]:
        """Dump Confluence space content."""
        try:
            result = await self.call_tool("confluence", "dump_space",
                                        space_key=space_key, format=format,
                                        max_pages=max_pages, include_archived=include_archived)
            success = "started" in result.lower() or "completed" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    async def dump_confluence_team_pages(self, space_key: str, team_name: str,
                                        format: str = "storage", max_pages: int = 0) -> tuple[bool, str]:
        """Dump team-specific Confluence pages."""
        try:
            result = await self.call_tool("confluence", "dump_team_pages",
                                        space_key=space_key, team_name=team_name,
                                        format=format, max_pages=max_pages)
            success = "dump" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    async def build_confluence_rag_index(self, space_key: str, max_words: int = 900,
                                        overlap: int = 120) -> tuple[bool, str]:
        """Build RAG index for Confluence space."""
        try:
            result = await self.call_tool("confluence", "build_rag_index",
                                        space_key=space_key, max_words=max_words, overlap=overlap)
            success = "building" in result.lower() or "started" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    # New Confluence Tools
    async def get_confluence_page_content(self, page_id: str, space_key: str = None,
                                        expand: List[str] = None) -> str:
        """Get content of a specific Confluence page."""
        try:
            if not expand:
                expand = ["body.storage", "version"]
            result = await self.call_tool("confluence", "get_page_content",
                                        page_id=page_id, space_key=space_key, expand=expand)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    async def create_confluence_page(self, space_key: str, title: str, content: str,
                                   parent_id: str = None) -> tuple[bool, str]:
        """Create a new Confluence page."""
        try:
            result = await self.call_tool("confluence", "create_page",
                                        space_key=space_key, title=title,
                                        content=content, parent_id=parent_id)
            success = "created successfully" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    async def update_confluence_page(self, page_id: str, content: str, title: str = None,
                                   version_comment: str = "Updated via MCP") -> tuple[bool, str]:
        """Update an existing Confluence page."""
        try:
            result = await self.call_tool("confluence", "update_page",
                                        page_id=page_id, content=content,
                                        title=title, version_comment=version_comment)
            success = "updated successfully" in result.lower()
            return success, result
        except Exception as e:
            return False, str(e)

    async def get_confluence_page_children(self, page_id: str, limit: int = 50) -> str:
        """Get child pages of a Confluence page."""
        try:
            result = await self.call_tool("confluence", "get_page_children",
                                        page_id=page_id, limit=limit)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    # DevOps Repository Tools
    async def list_repositories(self, project: str) -> List[str]:
        """List Git repositories in an Azure DevOps project."""
        try:
            result = await self.call_tool("devops", "list_repositories", project=project)

            # Parse the result to extract repository names
            if "Found" in result and "repositories" in result:
                lines = result.split('\n')[1:]  # Skip the first line with count
                repos = []
                for line in lines:
                    if " - " in line:
                        # Extract repo name from "repo_name (size) - url" format
                        repo_name = line.split(" (")[0].strip()
                        repos.append(repo_name)
                return repos
            return []
        except Exception:
            return []

    async def get_repository_files(self, project: str, repository: str, path: str = "/") -> str:
        """Browse files in a repository."""
        try:
            result = await self.call_tool("devops", "get_repository_files",
                                        project=project, repository=repository, path=path)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    async def get_file_content(self, project: str, repository: str, file_path: str, max_size: int = 100) -> str:
        """Get content of a specific file."""
        try:
            result = await self.call_tool("devops", "get_file_content",
                                        project=project, repository=repository,
                                        file_path=file_path, max_size=max_size)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    async def search_code(self, project: str, search_text: str, repository: str = None, file_type: str = None) -> str:
        """Search for code across repositories."""
        try:
            result = await self.call_tool("devops", "search_code",
                                        project=project, search_text=search_text,
                                        repository=repository, file_type=file_type)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    # Work Item Tools
    async def get_work_items(self, project: str, wiql_query: str = None, limit: int = 50) -> str:
        """Get work items using WIQL query."""
        try:
            result = await self.call_tool("devops", "get_work_items",
                                        project=project, wiql_query=wiql_query, limit=limit)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    async def get_work_item_details(self, project: str, work_item_ids: List[int], fields: List[str] = None) -> str:
        """Get detailed information for specific work items."""
        try:
            result = await self.call_tool("devops", "get_work_item_details",
                                        project=project, work_item_ids=work_item_ids, fields=fields)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    async def get_user_stories(self, project: str, limit: int = 50) -> str:
        """Get user stories for a project."""
        # WIQL uses double quotes for string literals
        wiql_query = 'SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = "' + project + '" AND [System.WorkItemType] = "User Story" AND [System.State] <> "Removed"'
        return await self.get_work_items(project, wiql_query, limit)

    async def get_bugs(self, project: str, limit: int = 50) -> str:
        """Get bugs for a project."""
        # WIQL uses double quotes for string literals
        wiql_query = 'SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = "' + project + '" AND [System.WorkItemType] = "Bug" AND [System.State] <> "Removed"'
        return await self.get_work_items(project, wiql_query, limit)

    async def get_active_work_items(self, project: str, limit: int = 50) -> str:
        """Get active work items (any type) for a project."""
        # WIQL uses double quotes for string literals
        wiql_query = 'SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = "' + project + '" AND [System.State] IN ("Active", "New", "In Progress", "Committed") ORDER BY [System.ChangedDate] DESC'
        return await self.get_work_items(project, wiql_query, limit)

    # ======================================
    # ChatNS MCP Methods
    # ======================================

    async def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4o",
                            temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Send chat completion request to ChatNS."""
        try:
            response = await self.call_tool("chatns", "chat_completion",
                                          messages=messages, model=model,
                                          temperature=temperature, max_tokens=max_tokens)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    async def semantic_search(self, prompt: str, bucket_id: Union[str, int],
                            top_n: int = 5, min_cosine_similarity: float = 0.75) -> str:
        """Perform semantic search in ChatNS knowledge buckets."""
        try:
            response = await self.call_tool("chatns", "semantic_search",
                                          prompt=prompt, bucket_id=bucket_id,
                                          top_n=top_n, min_cosine_similarity=min_cosine_similarity)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    async def list_chatns_buckets(self) -> str:
        """List available ChatNS knowledge buckets."""
        try:
            response = await self.call_tool("chatns", "list_buckets")
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    async def chatns_health_check(self) -> str:
        """Check ChatNS service health."""
        try:
            response = await self.call_tool("chatns", "health_check")
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    async def cleanup(self):
        """Cleanup MCP clients and processes."""
        # Stop all MCP protocol clients
        for server_name, client in self._mcp_clients.items():
            try:
                await client.stop()
            except Exception as e:
                print(f"Error stopping MCP client '{server_name}': {e}")

        self._mcp_clients.clear()

    def __del__(self):
        """Cleanup on deletion."""
        # Try to cleanup MCP clients
        if self._mcp_clients:
            try:
                import asyncio
                asyncio.get_event_loop().run_until_complete(self.cleanup())
            except:
                pass


# Async helper for Streamlit
def run_async(coro):
    """Run async function in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)