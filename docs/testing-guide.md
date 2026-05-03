# ClaudeRevit — Step-by-Step Verification & Testing Guide

## Pre-Flight Checklist

Before testing any button, confirm:

- [ ] Revit 2023+ is open with a project (not a family or template)
- [ ] pyRevit 5.0+ is installed — ClaudeRevit tab is visible
- [ ] `C:/tools/revit-bridge/` folder exists
- [ ] `C:/revit-claude/extension/ClaudeRevit.extension/config.json` has valid `anthropic_api_key`
- [ ] Internet connection active (Claude API calls)
- [ ] For Claude Desktop tests: Claude Desktop is fully open (not minimised to tray)

---

## Panel 1 — Claude Panel

### Button 1: Start Listener (▶)
**Expected:**
1. Click — success alert: "Listener started. Bridge: C:/tools/revit-bridge/"
2. `C:/tools/revit-bridge/` auto-created if missing
3. No Revit lag (idling throttled to 500ms)

**Verify:** Open Task Manager — Revit CPU should stay flat when listener is running.

---

### Button 2: Stop Listener (■)
**Expected:**
1. Click — success alert: "Listener stopped."
2. No errors

---

### Button 3: Claude Command (✦)
**Expected:**
1. Dark WPF window opens, centred on screen
2. Title bar shows: traffic-light dots + doc name + "Claude Command"
3. Gold hint text visible in input area
4. Type a prompt, press Ctrl+Enter
5. Code appears in output area
6. Press "Run" or Ctrl+Enter again to execute
7. Revit updates inside a transaction (Ctrl+Z to undo)

**Test prompt:** `"Create a simple wall 10 metres long in the active view"`

---

### Button 4: Build Model (⬜)
**Test prompt:** `"Create a simple 3-storey residential building with 3 rooms per floor, 3m floor-to-floor height"`
**Expected:** Walls, floors, levels, rooms created. Check in Revit project browser.

---

### Button 5: Generate Views (⊞)
**Test prompt:** `"Create floor plans for all levels, one 3D view, and one building section"`
**Expected:** Views appear in project browser under Floor Plans, 3D Views, Sections.

---

### Button 6: Place Rooms (⊡)
**Expected:**
1. Room-bounded areas detected
2. Rooms placed with names and numbers
3. Check via Revit → Architecture → Room & Area → Rooms

---

### Button 7: Make Schedule (≡)
**Test prompts:**
1. `"Create a wall schedule showing type, length, and area"` — should produce ViewSchedule
2. `"Create a sheet list"` — should use CreateSheetList, NOT CreateSchedule with OST_Sheets
3. `"Create a door schedule"` — should produce door schedule

**Expected:** Schedule appears in project browser under Schedules/Quantities.

---

### Button 8: Create Sheets (⬒)
**Test prompt:** `"Create 5 sheets numbered A-001 to A-005 with the standard title block, place one floor plan on each"`
**Expected:** 5 sheets in project browser, each with a viewport.

---

### Button 9: Model Audit (◎)
**Expected:**
1. pyRevit output panel opens
2. Report shows: element counts, health percentage, issues ranked by severity
3. No Python errors in output

---

### Button 10: Ask Claude (◌)
**Test question:** `"How many walls are in this model and what types are they?"`
**Expected:** Claude response referencing actual model data.

---

## Panel 2 — Script Panel

### Button 11: Python Script
**Expected:**
1. Full-screen dark editor opens (Consolas font)
2. Ctrl+Enter runs code
3. "Ask Claude" button generates IronPython 2.7 compatible code
4. Test: type `output.print_md("Hello from Python")` → Ctrl+Enter → output panel shows message

---

### Button 12: C# Script
**Expected:**
1. Editor opens
2. Ask Claude → generates class named `RevitScript` with method `Execute(Document doc, UIDocument uidoc)`
3. Ctrl+Enter compiles and runs
4. Test: ask Claude for `"count all walls and return the count as a string"`

---

## Panel 3 — Automate Panel

### Button 13: Auto-Dimension
**Pre-req:** Open a floor plan view with walls
**Expected:**
1. Dialog: Horizontal / Vertical / Both
2. Select Horizontal → dimension strings appear on horizontal walls
3. Dimensions placed 3ft offset from wall centreline
4. Ctrl+Z undoable

---

### Button 14: Auto-Tag
**Pre-req:** Active floor plan with rooms and/or doors
**Expected:**
1. Multi-select dialog: Room Tags / Door Marks / Window Marks / Wall Tags / Furniture Tags
2. Select Room Tags → tags placed on all rooms
3. Tags centred on element locations

---

### Button 15: Auto-Annotate
**Expected:**
1. Grid bubbles shown in active view
2. Level markers shown in sections (if section view active)
3. Report: views missing scales
4. Report: unplaced views
5. Output panel shows summary

---

### Button 16: Sheet Template
**Expected:**
1. WPF dialog opens with fields: Project Name, Drawn By, Checked By, Title Block, Sheet Count, Start Number
2. Fill in and click Create
3. Sheets created with project info populated in title block parameters

---

## Panel 4 — Audit Panel

### Button 17: Arch Audit
**Expected:**
1. Region selector: UK / EU / US / International
2. Select UK → full audit with BS EN ISO 19650 references
3. 8-section report in output panel
4. Issues flagged with severity

---

### Button 18: MEP Audit
**Expected:**
1. Region selector with CIBSE/ASHRAE/EN options
2. Report: duct coverage, lighting ratios, plumbing fixture counts
3. Missing MEP sheets flagged

---

### Button 19: Structural Audit
**Expected:**
1. Region selector with Eurocode/US/International
2. Column grid naming analysis
3. Mark completeness on beams and columns
4. Storey height summary

---

## Panel 5 — Parametric Panel

### Button 20: Parametric Model
**Expected:**
1. Type selector: Sine Wave Wall / Twisted Tower / Patterned Facade / Column Grid / Attractor Grid / Voronoi Plan / Custom
2. Select Sine Wave Wall → enter amplitude and wavelength
3. Claude generates IronPython code using math.sin()
4. Code executed → curved wall segments created

---

### Button 21: DirectShape
**Expected:**
1. Category selector: Generic Model / Mass / Structural Column / Wall / Furniture
2. Shape selector: Box / Cylinder / Pyramid / Sphere / Extruded Profile / Custom
3. Claude generates TessellatedShapeBuilder code
4. Shape created as DirectShape element in model

---

### Button 22: Family Browser
**Expected:**
1. Split WPF window: families left, types right
2. Search box filters family list in real time
3. Select family → types list populates
4. Select type → info panel shows category, instance count
5. Click "Place Instance" → family placed at project origin on lowest level
6. Alert confirms placement with Move (MV) instructions

---

## Claude Desktop Integration Test

**Pre-req:** Start Listener is active in Revit

1. Open Claude Desktop
2. Click hammer icon (🔨) — should show `revit-file-bridge` with 14 tools
3. Type: `"List all levels in the current Revit model"`
4. Claude calls `get_model_info` tool
5. Result appears in chat with level names and elevations
6. Open `http://localhost:3333` → dashboard shows model data

**MCP tools available (14):**
- get_model_info, execute_revit_code, create_walls, create_floors
- create_levels, create_rooms, create_views, create_sheets
- create_schedule, get_families, place_family, run_audit
- get_views, get_elements

---

## Dashboard Test

```bash
cd C:/revit-claude/dashboard
npm run dev
```

Open `http://localhost:3333`

**Expected:**
- Dark dashboard with ClaudeRevit header
- Green dot (connected) or grey dot (no data)
- After running any Claude Desktop command: model name, levels, element counts visible

---

## Common Issues & Fixes

| Symptom | Fix |
|---|---|
| WPF window doesn't open | Check pyRevit output for TypeError — likely enum issue |
| "categoryId invalid" on schedule | Use CreateSheetList for sheets, not CreateSchedule(OST_Sheets) |
| Can't type in prompt box | Restart Revit and pyRevit reload |
| Hammer not in Claude Desktop | Fully quit from system tray, reopen |
| Bridge timeout | Ensure Start Listener is active first |
| Revit laggy | Pull latest — throttle is in StartListener |
| C# compile error | Verify class name is RevitScript, method is Execute |
| DirectShape not visible | View → Visibility/Graphics → check Generic Models |
