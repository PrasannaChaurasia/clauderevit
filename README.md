# ClaudeRevit — AI-Powered Revit Control via Claude

**ClaudeRevit** connects Autodesk Revit to Claude (Anthropic's AI) so you can control your BIM model in plain English — no scripting knowledge required. Type "Create 5 levels at 4m spacing and add a floor plan view for each", and Claude writes and executes the Revit API code live inside your model.

---

## What It Does

| Button | Function |
|---|---|
| **Start Listener** | Activates the file-bridge so Claude Desktop can talk to Revit |
| **Stop Listener** | Deactivates the listener and clears the bridge |
| **Claude Command** | Type any instruction → Claude generates code → executes live in model |
| **Build Model** | Describe a building → Claude creates levels, walls, floors, rooms |
| **Generate Views** | Create floor plans, sections, elevations, 3D views automatically |
| **Place Rooms** | Auto-place and name rooms from a room list or description |
| **Make Schedule** | Generate wall, room, door, or custom schedules |
| **Create Sheets** | Create drawing sheets with title blocks and place views |
| **Model Audit** | Claude reads your model and produces a full BIM audit report |
| **Ask Claude** | Ask any Revit or BIM question with model context included |

---

## Architecture

```
Claude Desktop App
       │
       │  MCP (Model Context Protocol)
       ▼
 MCP Server (Node.js)
 revit-connections-with-claude/mcp-server/src/index.js
       │
       │  File Bridge (command.json / result.json)
       │  C:/tools/revit-bridge/
       ▼
 pyRevit Idling Event Handler
 (running inside Revit process)
       │
       │  Revit ExternalEventHandler
       ▼
 Revit API (valid API context)
       │
       ▼
 Revit Model (.rvt)
```

The file bridge is the key architectural pattern: Claude writes a command to `command.json`, pyRevit polls it during the Revit Idling event, raises an ExternalEvent, and the handler executes inside a valid Revit API context — which is required because Revit's API cannot be called from external threads.

---

## Requirements

### On the Revit machine:

| Requirement | Version | Notes |
|---|---|---|
| Autodesk Revit | 2023 or later | Earlier versions may work but are untested |
| pyRevit | 5.0+ | Free, open-source Revit plugin |
| Node.js | 18+ | For the MCP server |
| Claude Desktop | Latest | Anthropic's desktop app |

### Accounts / Keys:

| Service | Notes |
|---|---|
| Anthropic API key | Required — get from console.anthropic.com |
| Claude Pro or API plan | Required for Claude Desktop MCP features |

---

## Installation

### Step 1 — Clone this repository

```bash
git clone https://github.com/PrasannaChaurasia/revit-connections-with-claude.git
```

### Step 2 — Install the pyRevit extension

Copy the extension folder into pyRevit's Extensions directory:

```
Source:  revit-connections-with-claude/extension/ClaudeRevit.extension
Target:  C:/Users/<YourName>/AppData/Roaming/pyRevit/Extensions/
```

Result path should be:
```
C:/Users/<YourName>/AppData/Roaming/pyRevit/Extensions/ClaudeRevit.extension/
```

### Step 3 — Add your API key

Copy the example config file and add your Anthropic API key:

```
Source:  extension/ClaudeRevit.extension/config.example.json
Target:  extension/ClaudeRevit.extension/config.json
```

Edit `config.json`:
```json
{
  "anthropic_api_key": "sk-ant-api03-YOUR-KEY-HERE",
  "model": "claude-sonnet-4-6",
  "max_tokens": 1500
}
```

> **Important:** Never commit `config.json` to GitHub. It is already in `.gitignore`.  
> Your API key is personal — each user must use their own.

### Step 4 — Create the bridge directory

```bash
mkdir C:\tools\revit-bridge
```

### Step 5 — Install MCP server dependencies

```bash
cd revit-connections-with-claude/mcp-server
npm install
```

### Step 6 — Configure Claude Desktop

Open (or create) this file:
```
C:/Users/<YourName>/AppData/Roaming/Claude/claude_desktop_config.json
```

Add the following, adjusting the path to match where you cloned the repo:

```json
{
  "mcpServers": {
    "revit-file-bridge": {
      "command": "node",
      "args": ["C:/revit-connections-with-claude/mcp-server/src/index.js"],
      "env": {
        "BRIDGE_DIR": "C:\\tools\\revit-bridge",
        "REVIT_TIMEOUT": "15000"
      }
    }
  }
}
```

### Step 7 — Start everything

1. Open Revit with a project
2. Go to the **pyRevit** tab → click **Reload**
3. The **ClaudeRevit** tab will appear
4. Click **Start Listener** — Revit is now watching for commands
5. Restart **Claude Desktop** — it will connect to the MCP server automatically
6. You are ready

---

## Using Claude Command

1. Open a Revit project
2. Click **Start Listener** (once per session)
3. Click **Claude Command**
4. A large prompt window opens — type your instruction in plain English
5. Claude generates Revit API code
6. Review the code in the output window
7. Click **Proceed** to execute, or **Cancel** to abort
8. All changes are undoable with **Ctrl+Z**

### Example instructions

```
Create 5 storeys at 4m spacing starting at 0m
```
```
Build a 15m x 10m rectangular floor plan with 200mm brick walls on Level 1
```
```
Create sheets A101 through A115 with A1 title block and place one floor plan per level
```
```
Rename all rooms on Level 0 to start with prefix GF-
```
```
Create a room schedule showing Name, Number, Area, Level
```
```
Add a 3D isometric view and a north-facing section through the building
```
```
Create a 5-storey residential building: Level 0 = ground floor lobby, Levels 1-4 = 4 apartments each, Level 5 = roof terrace. Add all floor plan views and a sheet for each level.
```

---

## Using Claude Desktop (MCP Tools)

Once connected and the Listener is running in Revit, type directly in the Claude chat window:

```
What levels does my Revit model have?
```
```
Create 3 levels at 3m, 6m, and 9m
```
```
List all rooms and their areas
```
```
Create a wall schedule with Type, Length, and Area columns
```

Claude will use the `revit-file-bridge` MCP tools automatically. No button clicks required.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| ClaudeRevit tab not showing | pyRevit tab → Reload. If still missing, restart Revit. |
| "Claude API error" | Check your API key in `config.json`. Verify it starts with `sk-ant-` |
| "Timeout waiting for Revit" | Click **Start Listener** first, then retry the command |
| Code runs but nothing changes in model | Check pyRevit output window for Python errors — likely a units or element ID issue |
| Claude Desktop shows "MCP not connected" | Restart Claude Desktop after editing `claude_desktop_config.json` |
| `command.json` keeps re-executing | Fixed in v2 — bridge clears command.json after reading |
| Undo doesn't work | Code must use `with revit.Transaction()` — all generated code includes this |

---

## Can I Share This With Another Person?

Yes. The repository is fully portable. Each person needs to:

1. Clone this repository to their machine
2. Copy the extension to their `AppData/Roaming/pyRevit/Extensions/` folder
3. Create `config.json` with **their own Anthropic API key**
4. Create `C:/tools/revit-bridge/` on their machine
5. Run `npm install` in the `mcp-server` folder
6. Configure `claude_desktop_config.json` with the path on their machine
7. Reload pyRevit and restart Claude Desktop

The only thing that is not shared is the API key — each user must obtain their own from [console.anthropic.com](https://console.anthropic.com).

---

## File Structure

```
revit-connections-with-claude/
├── extension/
│   └── ClaudeRevit.extension/
│       ├── lib/
│       │   ├── claude_client.py          ← Shared Claude API caller
│       │   └── command_dispatcher.py     ← 14 Revit API action handlers
│       ├── config.example.json           ← Template (copy to config.json, add key)
│       ├── config.json                   ← YOUR KEY — gitignored, never commit
│       └── ClaudeRevit.tab/
│           └── Claude.panel/
│               ├── 00_StartListener.pushbutton/
│               ├── 00_StopListener.pushbutton/
│               ├── 01_ClaudeCommand.pushbutton/
│               ├── 02_BuildModel.pushbutton/
│               ├── 03_GenerateViews.pushbutton/
│               ├── 04_PlaceRooms.pushbutton/
│               ├── 05_MakeSchedule.pushbutton/
│               ├── 06_CreateSheets.pushbutton/
│               ├── 07_ModelAudit.pushbutton/
│               └── 08_AskClaude.pushbutton/
├── mcp-server/
│   ├── src/
│   │   └── index.js                      ← Node.js MCP server (14 Revit tools)
│   └── package.json
├── .gitignore
└── README.md
```

---

## How Claude Generates Safe Revit Code

Every Claude-generated script follows strict rules enforced by the system prompt:

- **IronPython 2.7 compatible** — no f-strings, no type hints, uses `.format()`
- **All changes wrapped in a Transaction** — makes everything undoable with Ctrl+Z
- **Units always converted** — 1 metre = 3.28084 feet (Revit internal unit)
- **Errors surfaced as alerts** — if something fails, you see the message in Revit, not a silent crash
- **No imports needed** — all Revit API classes are pre-loaded into the execution context

---

## Author

**Prasanna Chaurasia**  
Architectural Designer & BIM Specialist  
Urban Matrix — Manchester, UK  
GitHub: [PrasannaChaurasia](https://github.com/PrasannaChaurasia)

---

## License

MIT — free to use, modify, and distribute with attribution.
