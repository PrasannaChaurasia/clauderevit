# Revit Claude MCP Server

MCP server that exposes Revit as tools for Claude Desktop / Claude Code.

## Architecture

```
Claude Desktop
     ↓ MCP protocol (stdio)
revit-claude-mcp (this Node.js server)
     ↓ HTTP REST
Revit HTTP Server (pyRevit or .NET add-in running inside Revit)
     ↓ Revit API
Autodesk Revit 2026
```

## Setup

1. Install Revit HTTP server (pyRevit script or .NET add-in — see /docs)
2. `npm install` in this folder
3. Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "revit": {
      "command": "node",
      "args": ["C:/revit-claude/mcp-server/src/index.js"],
      "env": {
        "REVIT_API_BASE": "http://localhost:8765"
      }
    }
  }
}
```

## Tools exposed to Claude

| Tool | Description |
|---|---|
| revit_get_model_info | Model name, element counts |
| revit_get_elements | Get walls, rooms, doors etc by category |
| revit_get_views | All views and sheets |
| revit_get_rooms | Rooms with areas and levels |
| revit_get_sheets | Sheet list with revision data |
| revit_execute_code | Execute Python inside Revit live |

## Status

Awaiting Revit HTTP server details. Scaffold complete.
