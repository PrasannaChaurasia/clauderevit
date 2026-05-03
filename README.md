<div align="center">

<img src="https://img.shields.io/badge/-%E2%96%A0%20CLAUDEREVIT-C8A96E?style=for-the-badge&logoColor=1a1a1a" height="40"/>

# ClaudeRevit — AI-Powered BIM Platform

<p>
<img src="https://img.shields.io/badge/Revit-2023%2B-0696D7?style=flat-square&logo=autodesk"/>
<img src="https://img.shields.io/badge/pyRevit-5.0%2B-FF6B35?style=flat-square"/>
<img src="https://img.shields.io/badge/Claude-Sonnet%204.6-8B5CF6?style=flat-square"/>
<img src="https://img.shields.io/badge/Node.js-18%2B-339933?style=flat-square&logo=nodedotjs"/>
<img src="https://img.shields.io/badge/Buttons-20-C8A96E?style=flat-square"/>
<img src="https://img.shields.io/badge/MCP%20Tools-14-22C55E?style=flat-square"/>
<img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square"/>
</p>

**Type in plain English. Revit builds it.**

Control every aspect of Revit through natural language — model creation, drawing production,
multi-discipline auditing, parametric geometry, and live dashboards.
Works via Claude Desktop (MCP), the pyRevit ribbon, or direct script execution.

[Installation](#installation) · [Panels & Buttons](#panels--buttons) · [MCP Tools](#mcp-server--14-tools) · [Architecture](#architecture) · [Story](STORY.md)

</div>

---

## What It Does

| Input | Output |
|---|---|
| `"Create a two-storey house, open plan ground floor, two bedrooms upstairs"` | Walls, floors, levels, rooms — placed in the model |
| `"Generate floor plans, sections, and a 3D view"` | Views created and ready to place on sheets |
| `"Run a full model audit"` | Ranked issue list: parameter gaps, naming, counts |
| `"Create sheets A100–A110 with the title block"` | Numbered sheets with title blocks populated |
| `"Write a Python script to renumber all rooms by level"` | Script in editor — review then run |

---

## Architecture Overview

Three channels for sending commands to Revit:

```
┌─────────────────────────────────────────────────────────────┐
│  Channel 1: Claude Desktop (via MCP Server)                  │
│  Chat → Node.js MCP (14 tools) → command.json bridge        │
│          → Revit Idling event → ExternalEventHandler        │
├─────────────────────────────────────────────────────────────┤
│  Channel 2: pyRevit Ribbon Buttons                           │
│  Click button → WPF prompt → Claude API → IronPython code   │
│          → ExternalEventHandler.Execute()                   │
├─────────────────────────────────────────────────────────────┤
│  Channel 3: Script Panel (Direct Code)                       │
│  Write Python/C# → review → Execute inside ExternalEvent    │
└─────────────────────────────────────────────────────────────┘
```

**File Bridge Protocol** (Channel 1):
```
C:/tools/revit-bridge/
├── command.json   ← MCP server writes { "action": "...", "params": {...} }
└── result.json    ← Revit writes back { "status": "ok", "data": {...} }
```
Revit polls every 500ms via the Idling event — the only safe cross-thread hook in the Revit API.

---

## Installation

### Prerequisites

| Requirement | Version | Install |
|---|---|---|
| Autodesk Revit | 2023+ | Via Autodesk Account |
| pyRevit | 5.0+ | [pyrevitlabs.io](https://pyrevitlabs.io) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Claude Desktop | Latest | [claude.ai/download](https://claude.ai/download) |
| Anthropic API Key | — | [console.anthropic.com](https://console.anthropic.com) |

### Step 1 — Clone the Repo

```bash
git clone https://github.com/PrasannaChaurasia/clauderevit.git
cd clauderevit
```

### Step 2 — Install the pyRevit Extension

```powershell
# Copy the extension to pyRevit's Extensions folder
Copy-Item -Recurse -Force "extension\ClaudeRevit.extension" `
  "$env:APPDATA\pyRevit\Extensions\ClaudeRevit.extension"
```

### Step 3 — Configure API Key

```powershell
# Copy example config
Copy-Item "extension\ClaudeRevit.extension\config.example.json" `
          "extension\ClaudeRevit.extension\config.json"
```

Edit `config.json`:
```json
{
  "api_key": "sk-ant-YOUR_KEY_HERE",
  "model": "claude-sonnet-4-5",
  "max_tokens": 1500,
  "bridge_dir": "C:/tools/revit-bridge"
}
```

### Step 4 — Create the Bridge Folder

```powershell
New-Item -ItemType Directory -Path "C:\tools\revit-bridge" -Force
```

### Step 5 — Install and Start the MCP Server

```powershell
cd mcp-server
npm install
```

Add to Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "revit": {
      "command": "node",
      "args": ["C:/path/to/clauderevit/mcp-server/src/index.js"],
      "env": {
        "BRIDGE_DIR": "C:/tools/revit-bridge"
      }
    }
  }
}
```

### Step 6 — Restart Revit

Open Revit. You should see the **ClaudeRevit** tab in the ribbon with all 5 panels.

Click **▶ Start Listener** to arm the bridge for Claude Desktop commands.

---

## Panels & Buttons

### Panel 1 — Claude (Core AI Control)

| Button | What it does |
|---|---|
| ▶ **Start Listener** | Arms Revit for Claude Desktop commands. Creates bridge folder automatically. Throttled to 2× per second. |
| ■ **Stop Listener** | Closes bridge, deactivates the listener. |
| ✦ **Claude Command** | Dark WPF prompt → Claude generates IronPython → review → run. `Ctrl+Enter` to execute. |
| ⬜ **Build Model** | Plain-English building description → walls, floors, levels, rooms created automatically. |
| ⊞ **Generate Views** | Create floor plans, sections, elevations, 3D views, and ceiling plans from a description. |
| ⊡ **Place Rooms** | Auto-place and name rooms with numbers, departments, and area targets. |
| ≡ **Make Schedule** | Any schedule from plain English — walls, rooms, doors, windows, sheets, custom categories. |
| ⬒ **Create Sheets** | Create numbered sheets with title blocks, auto-placed views, and project info populated. |
| ◎ **Model Audit** | Full BIM audit: element counts, health report, issues ranked by severity. |
| ◌ **Ask Claude** | Ask any Revit or BIM question with your live model as context. |

### Panel 2 — Script (Direct Code Execution)

| Button | What it does |
|---|---|
| **Python Script** | Full-screen IronPython 2.7 editor. Write directly or press **Ask Claude** to generate from description. `Ctrl+Enter` to run. |
| **C# Script** | Write and compile C# code with access to the full Revit API. Ask Claude for the code. |

### Panel 3 — Automate

| Button | What it does |
|---|---|
| **Auto Dimension** | Dimension selected elements or an entire floor plan automatically. |
| **Auto Tag** | Tag all elements in a view by category — doors, windows, rooms, walls. |
| **Auto Annotate** | Add keynotes, text notes, and annotations from a description. |
| **Sheet Template** | Apply a standard sheet template across multiple sheets in one operation. |

### Panel 4 — Audit

| Button | What it does |
|---|---|
| **Arch Audit** | Architectural model audit — walls, floors, rooms, openings, naming conventions. |
| **MEP Audit** | MEP coordination check — pipe/duct clearances, system naming, connection gaps. |
| **Structural Audit** | Structural model check — column grids, load-bearing elements, analytical model. |

*All audits check against four code frameworks: UK (BS), EU (Eurocode), US (IBC), International.*

### Panel 5 — Parametric

| Button | What it does |
|---|---|
| **Parametric Model** | Create parametric geometry from a description — adaptive components, rule-based forms. |
| **DirectShape** | Create DirectShape solids and surfaces directly in the model from geometry descriptions. |
| **Family Browser** | Browse, filter, and place families from the project library using natural language. |

---

## MCP Server — 14 Tools

When connected via Claude Desktop, these 14 tools are available for direct model manipulation:

| Tool | Description |
|---|---|
| `revit_get_model_info` | Model name, element counts — run first to understand the model |
| `revit_get_levels` | All levels with names and elevations in mm |
| `revit_get_sheets` | All sheets with numbers and names |
| `revit_get_rooms` | All rooms with name, number, area, level |
| `revit_get_elements` | Element count by category (Walls, Floors, Doors, Windows, Rooms, Furniture) |
| `revit_create_levels` | Create one or more levels at specified elevations |
| `revit_create_walls` | Create walls from XY coordinates in mm |
| `revit_create_room` | Place and name a room at a specified position |
| `revit_create_sheets` | Create numbered drawing sheets with title blocks |
| `revit_create_views` | Create FloorPlan, CeilingPlan, or ThreeD views |
| `revit_create_schedule` | Create a quantity schedule for any element category |
| `revit_run_python` | Execute any IronPython 2.7 code directly in Revit |
| `revit_run_csharp` | Execute any C# code with full Revit API access |
| `revit_audit_model` | Full BIM health report — counts, gaps, issues ranked by severity |

---

## Example Prompts (Claude Desktop)

```
Build a two-storey residential building:
- Ground floor: open kitchen/dining, living room, WC — approx 80m²
- First floor: main bedroom with en-suite, two further bedrooms, bathroom — approx 80m²
- 3m floor-to-floor height

Then generate floor plans for both levels, a section, and a 3D view.
Create sheets A100–A103 and place the views on them.
Run a model audit and tell me what needs fixing.
```

---

## Folder Structure

```
clauderevit/
├── extension/
│   └── ClaudeRevit.extension/
│       ├── ClaudeRevit.tab/
│       │   ├── Claude.panel/          # 10 buttons
│       │   ├── Script.panel/          # 2 buttons
│       │   ├── Automate.panel/        # 4 buttons
│       │   ├── Audit.panel/           # 3 buttons
│       │   └── Parametric.panel/      # 3 buttons
│       ├── lib/
│       │   ├── claude_client.py       # Anthropic API wrapper
│       │   ├── command_dispatcher.py  # Command routing
│       │   └── wpf_helper.py          # WPF UI components
│       ├── config.json                # API key + settings (gitignored)
│       └── config.example.json
├── mcp-server/
│   └── src/index.js                   # Node.js MCP server (14 tools)
├── dashboard/                         # Next.js dashboard (port 3333)
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   └── testing-guide.md
├── discussion/                        # 47 screenshots of the working system
├── references/
│   └── revit-mcp-community/
├── STORY.md                           # Why this was built
├── CLAUDE.md                          # Claude Code project context
└── DESIGN.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Revit extension | pyRevit 5.0+ / IronPython 2.7 |
| AI model | Claude Sonnet (Anthropic API) |
| MCP server | Node.js 18+, StdioServerTransport |
| Claude interface | Claude Desktop (local, via MCP) |
| Dashboard | Next.js 14, port 3333 |
| Bridge protocol | JSON files, 500ms Idling poll |
| Platform | Windows, Revit 2023–2026 |

---

## Roadmap

**v1.1** — NBS Specification linker · COBie readiness report · IFC export validator · Drawing issue manager

**v2.0** — Real-time WebSocket dashboard · Multi-model support · Family creation from description · Enscape/V-Ray hooks

Read the full roadmap: [docs/roadmap.md](docs/roadmap.md)

---

## The Story

Read [STORY.md](STORY.md) — why this was built, how the file bridge architecture was designed, and what problem it solves for architectural practice.

---

## License

MIT

---

<div align="center">
<sub>Built by <strong>Prasanna Chaurasia</strong> — Urban Matrix, Manchester UK</sub><br/>
<sub>prasanna.subx@gmail.com · github.com/PrasannaChaurasia</sub>
</div>
