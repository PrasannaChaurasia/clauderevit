# ClaudeRevit — The Story Behind the Build

> *An architectural designer's account of why this exists, what problem it solves,
> and how it was built from first principles.*

---

## The Problem

Every architect who has spent serious time in Revit knows the tax.

Not the licence tax — the cognitive tax. The gap between the thing you want to create and the thirty clicks it takes to create it. You have a clear idea in your head: *three levels, open-plan ground floor, two bedroom upper floor, place the rooms, dimension them, generate the floor plans, get them on sheets.* In your mind it takes ten seconds. In Revit it takes forty minutes — and half of that is menu navigation.

The frustration compounds in practice. You're mid-project, there's a design review in two hours, and you need to model a quick massing option to test if it works. You know exactly what it should be. Revit doesn't care. It makes you find the right family, set the right parameters, draw the right lines, in the right order, at the right scale. The tool that's supposed to serve the design ends up dominating it.

I'd been using Claude for code and writing for months before it occurred to me: *what if Revit took instructions the same way?*

---

## The Idea

The initial experiment was simple. I wanted to type *"create a ground floor plan with an open kitchen, living room, and two bedrooms, roughly 90 square metres"* and have Revit build it.

Not a plugin that generates a floor plan image. Not a script that fills in a template. An actual Revit model — walls, rooms, levels, the works — responding to plain English.

I'd seen enough of what Claude could do with code generation to believe it was possible. The question was architecture. How does a chat interface connect to a running Revit session?

---

## The Architecture Problem

Revit runs on the .NET Revit API. Everything that touches the model has to execute inside an `ExternalEventHandler` on the main UI thread. You can't call the API from a background thread, from a socket listener, from a timer that fires whenever it wants. Revit will simply refuse, often without a useful error.

This is the single constraint that shapes the entire system.

The solution — the file bridge — is elegantly simple once you see it:

1. Claude writes a `command.json` file to a shared folder
2. Revit polls that folder every 500ms on the Idling event (the one safe background hook Revit exposes)
3. When it finds a command, it reads it, executes it inside an ExternalEventHandler, and writes a `result.json`
4. Claude reads the result

```
Claude Desktop
    └─ MCP Server (Node.js, 14 tools)
            └─ writes  →  C:/tools/revit-bridge/command.json
                                    ↓
                          Revit Idling event (500ms)
                                    ↓
                          ExternalEventHandler.Execute()
                                    ↓
                          writes  →  C:/tools/revit-bridge/result.json
                                    ↑
            └─ reads   ←  MCP Server
```

It's not glamorous. It's a folder watch. But it's reliable, it works across Revit versions, and it requires no COM interop, no WebSocket server inside Revit, no unsafe threading hacks.

---

## Building the pyRevit Extension

The second channel — the direct Revit buttons — came from a different need. Sometimes you want the AI embedded *inside* Revit, not talking to it from a chat window.

pyRevit made this straightforward. It's an extension framework for Revit that lets you add ribbon panels and buttons without a compiled C# plugin. Write IronPython 2.7 scripts, drop them in the right folder structure, restart Revit, and the buttons appear.

IronPython 2.7 is a constraint worth noting. It's not Python 3. No f-strings. No type hints. No `match/case`. Standard library is mostly absent — `import json` works, `import os` works, `import math` works, but that's about the extent of it. Every WPF enum has to be called by name, not integer. Working within these constraints without mistakes requires discipline and consistent rules — exactly what CLAUDE.md encodes.

The extension grew to five panels and twenty buttons across three sessions of development:

- **Claude Panel** — the core AI interface: start/stop the listener, natural language to Revit model, generate views, place rooms, create sheets, full audit, open chat
- **Script Panel** — Python and C# editors with Claude assistance built in
- **Automate Panel** — dimension, tag, annotate, sheet templates in one click
- **Audit Panel** — architecture, MEP, and structural audit across four code frameworks (UK, EU, US, International)
- **Parametric Panel** — parametric geometry, DirectShape primitives, family browser

---

## The MCP Server

The Model Context Protocol server is the bridge for Claude Desktop. Fourteen tools, each one a precise operation:

| Tool | What it does |
|---|---|
| `revit_get_model_info` | Model name, element counts — always run this first |
| `revit_get_levels` | All levels with elevations in mm |
| `revit_get_sheets` | All sheets with numbers and names |
| `revit_get_rooms` | All rooms with area and level |
| `revit_get_elements` | Element counts by category |
| `revit_create_levels` | Create any number of levels |
| `revit_create_walls` | Create walls from XY coordinates |
| `revit_create_room` | Place and name a room |
| `revit_create_sheets` | Create drawing sheets |
| `revit_create_views` | Floor plans, ceiling plans, 3D views |
| `revit_create_schedule` | Quantity schedules for any category |
| `revit_run_python` | Execute any IronPython code directly |
| `revit_run_csharp` | Execute any C# code directly |
| `revit_audit_model` | Full model health report |

The last two — run_python and run_csharp — are the escape hatch for anything the named tools don't cover. If Claude can generate valid IronPython, it can do anything the Revit API can do.

---

## What It Solves

The workflow that prompted all of this now takes under two minutes:

```
"Build a two-storey house. Ground floor: open kitchen/living, one WC.
First floor: two bedrooms, one bathroom. Approximately 80m² per floor."
```

Revit builds it. Claude generates the levels, places the walls, drops the rooms, and returns the model info confirming everything was created. From there — generate views, create sheets, run the audit, export.

The audit tool alone has saved more time than I can count. It checks every wall, floor, door, window, and room against the BIM Execution Plan requirements, flags parameter gaps, and generates a ranked issue list. What used to be a half-day exercise before coordination meetings is now a three-second button press.

---

## Why Open Source

Because the problem isn't unique to one practice.

Every architectural team using Revit carries the same cognitive tax. The tool is powerful and deeply frustrating in equal measure. The solution described here is not complex — it doesn't require a large team or a funded startup. It requires understanding the Revit API's threading model, a Node.js MCP server, and a Claude subscription. All of which are available to any practice willing to spend a weekend on it.

This repository is the working implementation. Clone it, configure it, adapt it for your own projects.

---

## Stack

| Layer | Technology |
|---|---|
| Revit extension | pyRevit 5.0+ / IronPython 2.7 |
| AI model | Claude Sonnet (Anthropic API) |
| MCP server | Node.js 18+, StdioServerTransport |
| AI interface | Claude Desktop (local) |
| Dashboard | Next.js 14, port 3333 |
| Bridge protocol | JSON files, 500ms Idling poll |
| Platform | Windows, Revit 2023–2026 |

---

## What's Next

Version 1.1 targets:
- NBS Specification linker — wall/floor types linked to NBS clauses
- COBie readiness report — parameter completeness for handover
- IFC export validator — model checked against IFC4 LOD before export
- Drawing issue manager — revision clouds and issue registers

Version 2.0 targets:
- Real-time WebSocket dashboard
- Multi-model and workset support
- Family creation from description
- Enscape/V-Ray API hooks for rendered view generation

---

*Prasanna Chaurasia — Urban Matrix, Manchester UK*
*prasanna.subx@gmail.com | github.com/PrasannaChaurasia*
