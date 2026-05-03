# ClaudeRevit — Architecture Reference

## Input Channels

Three ways to send commands to Revit:

1. **Claude Command button** — WPF prompt inside Revit → Claude API → code → ExternalEventHandler
2. **Claude Desktop** — Chat → MCP server → file bridge → Idling event → ExternalEventHandler
3. **Script Panel** — Write code directly in Python or C# editor → ExternalEventHandler

## Execution Pipeline

```
User Input
    │
    ├─ Prompt Box (Claude Command / Build Model / etc.)
    │       └── Claude API (claude-sonnet-4-6, max_tokens=1500)
    │               └── Generated IronPython code
    │                       └── exec() inside ExternalEventHandler
    │
    ├─ Claude Desktop Chat
    │       └── MCP Server (Node.js, 14 tools, StdioServerTransport)
    │               └── Writes command.json → C:/tools/revit-bridge/
    │                       └── Idling event (500ms poll) reads command.json
    │                               └── ExternalEventHandler.Execute()
    │
    └─ Script Editor (Python / C#)
            └── Direct exec() or CSharpCodeProvider → ExternalEventHandler
```

## File Bridge Protocol

**Write by:** Claude Desktop (via MCP server)  
**Read by:** pyRevit Idling event (every 500ms)

```
C:/tools/revit-bridge/
├── command.json   ← Claude writes { "action": "...", "params": {...} }
└── result.json    ← Revit writes { "status": "ok", "data": {...} }
```

command.json is deleted after processing. result.json persists for dashboard.

## Threading Model

Revit API is single-threaded. All API calls must be in:
- `IExternalEventHandler.Execute(app)` — raised by `ExternalEvent.Raise()`
- `IExternalCommand.Execute(...)` — button click context
- `Application.Idling` event handler — polled from pyRevit

The file bridge + ExternalEvent pattern keeps everything on the correct thread.

## MCP Server Tools (14)

| Tool | Action |
|---|---|
| get_model_info | Returns levels, element counts, views |
| execute_revit_code | Runs arbitrary IronPython code via bridge |
| create_walls | Creates wall elements from coordinates |
| create_floors | Creates floor slabs |
| create_levels | Creates project levels |
| create_rooms | Places and names rooms |
| create_views | Creates floor plans, sections, 3D views |
| create_sheets | Creates sheets with title blocks |
| create_schedule | Creates element schedules |
| get_families | Lists all loaded families |
| place_family | Places a family instance |
| run_audit | Triggers model audit |
| get_views | Lists all views |
| get_elements | Lists elements by category |

## Dashboard

Next.js 14 Server Component reads result.json on every page request.  
No WebSocket — simple refresh-to-update pattern.  
Port 3333. Start: `cd C:/revit-claude/dashboard && npm run dev`
