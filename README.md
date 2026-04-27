# Revit × Claude — Full Integration

**Author:** Prasanna Chaurasia — Urban Matrix, Manchester UK  
**Repo:** https://github.com/PrasannaChaurasia/revit-connections-with-claude  
**Local:** C:/revit-claude/

---

## What this is

Full Claude AI ↔ Autodesk Revit 2026 integration. Two parallel approaches:

### 1. pyRevit Extension (`/extension`)
A tab inside Revit with buttons that call Claude API directly.  
Claude reads your model, writes Revit API code, and executes it live.  
**No external server needed. Works immediately after pyRevit install.**

### 2. MCP Server (`/mcp-server`)
A proper Model Context Protocol server that exposes Revit data and actions  
as tools Claude can call natively from Claude Desktop or Claude Code.  
**Full bidirectional control — Claude can read and write any Revit element.**

---

## Folder Structure

```
C:/revit-claude/
├── extension/                    → pyRevit extension (install in Revit)
│   └── ClaudeRevit.extension/
│       ├── lib/
│       │   └── claude_client.py  → Shared Claude API caller
│       ├── ClaudeRevit.tab/
│       │   └── Claude.panel/
│       │       └── [buttons]/    → Individual script buttons
│       ├── config.json           → API key + model settings
│       └── extension.json        → pyRevit manifest
├── mcp-server/                   → MCP server (Node.js)
│   ├── src/
│   │   └── index.js              → MCP server entry point
│   ├── package.json
│   └── README.md
├── docs/                         → Architecture notes, API reference
├── scripts/                      → Standalone pyRevit scripts
└── README.md                     → This file
```

---

## Quick Start — pyRevit Extension

1. Install pyRevit from pyrevitlabs.io
2. Edit `extension/ClaudeRevit.extension/config.json` — add your Anthropic API key
3. In Revit → pyRevit tab → Settings → Custom Extensions → Add `C:/revit-claude/extension/ClaudeRevit.extension`
4. Reload pyRevit
5. Use the **ClaudeRevit** tab

---

## API Key

Anthropic Claude API: `console.anthropic.com`  
Model in use: `claude-sonnet-4-6` (cost-efficient, high capability)

---

## Status

| Component | Status |
|---|---|
| pyRevit extension | Active |
| MCP server | In development |
| Revit API bridge | Planned |
