# -*- coding: utf-8 -*-
__title__ = "Arch\nAudit"
__doc__ = "Comprehensive architectural drawing audit: spaces, accessibility, annotations, dimensions, sheet completeness, BIM compliance, and code checks against UK/EU/US standards."

import sys, os, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Wall, Floor, Level, ViewSheet, ViewPlan,
    ViewSection, Viewport, Grid, IndependentTag, TextElement,
    Dimension, Room, BuiltInCategory, BuiltInParameter,
    ElementId, View, FamilyInstance
)
from Autodesk.Revit.DB.Architecture import Room as ArchRoom
from claude_client import ask_claude
from wpf_helper import switch_dialog

doc    = revit.doc
output = script.get_output()

def _s(v):
    if v is None:
        return ""
    try:
        return unicode(v).encode('ascii', 'ignore').decode('ascii')
    except Exception:
        return str(v)

# ── Region / standard selector ────────────────────────────────
region = switch_dialog(
    [
        "UK (BS EN ISO 19650 / Building Regs)",
        "EU (Eurocode + EN standards)",
        "US (IBC / AIA standards)",
        "Australia / NZ (NCC / AS standards)",
        "Middle East (IBC + local)",
        "International (general best practice)",
    ],
    message="Select the code standard for this audit:",
    title="Architectural Audit"
)
if not region:
    script.exit()

output.print_md("# Architectural Audit  —  {}".format(doc.Title))
output.print_md("**Standard:** {}".format(region))
output.print_md("Collecting model data...")

# ── Collect all data ──────────────────────────────────────────
data = {}

# Levels
levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
levels.sort(key=lambda l: l.Elevation)
data["levels"] = [{"name": _s(l.Name), "elev_m": round(l.Elevation * 0.3048, 3)} for l in levels]

# Walls
walls = list(FilteredElementCollector(doc).OfClass(Wall).ToElements())
wall_data = []
for w in walls:
    try:
        lp = w.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
        wall_data.append({
            "type": _s(w.WallType.Name),
            "length_m": round(lp.AsDouble() * 0.3048, 2) if lp else 0,
            "level": _s(w.get_Parameter(BuiltInParameter.WALL_BASE_CONSTRAINT).AsValueString()) if w.get_Parameter(BuiltInParameter.WALL_BASE_CONSTRAINT) else "?"
        })
    except Exception:
        pass
data["walls"] = wall_data[:80]
data["wall_count"] = len(walls)

# Rooms
rooms = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).ToElements())
room_data = []
for r in rooms:
    try:
        name  = r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
        num   = r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
        area  = r.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble() * 0.0929
        level = r.get_Parameter(BuiltInParameter.ROOM_LEVEL_ID)
        dept  = r.LookupParameter("Department")
        room_data.append({
            "name":   _s(name) or "",
            "number": _s(num)  or "",
            "area_sqm": round(area, 2),
            "level": _s(r.Level.Name) if r.Level else "?",
            "department": _s(dept.AsString()) if dept and dept.AsString() else "",
            "has_tag": False
        })
    except Exception:
        pass
data["rooms"] = room_data[:80]
data["room_count"] = len(rooms)

# Check which rooms have tags in any view
tagged_room_ids = set()
all_tags = list(FilteredElementCollector(doc).OfClass(IndependentTag).ToElements())
for tag in all_tags:
    try:
        tid = getattr(tag, 'TaggedLocalElementId', None) or getattr(tag, 'TaggedElementId', None)
        if tid:
            tagged_room_ids.add(tid)
    except Exception:
        pass
untagged_rooms = [r for r in room_data if r.get("number", "") not in tagged_room_ids]
data["untagged_room_count"] = len(untagged_rooms)

# Sheets
sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
sheet_data = []
for s in sheets:
    drawn = s.LookupParameter("Drawn By")
    checked = s.LookupParameter("Checked By")
    sheet_data.append({
        "number": _s(s.SheetNumber),
        "name":   _s(s.Name),
        "drawn_by":   _s(drawn.AsString()) if drawn and drawn.AsString() else "",
        "checked_by": _s(checked.AsString()) if checked and checked.AsString() else "",
        "viewport_count": len(list(Viewport.GetViewportIds(doc, s.Id) if hasattr(Viewport, 'GetViewportIds') else []))
    })
data["sheets"] = sheet_data[:50]
data["sheet_count"] = len(sheets)

# Views
all_views = list(FilteredElementCollector(doc).OfClass(View).ToElements())
plan_views = [v for v in all_views if isinstance(v, ViewPlan) and not v.IsTemplate]
section_views = [v for v in all_views if isinstance(v, ViewSection) and not v.IsTemplate]

placed_ids = set()
for s in sheets:
    try:
        from Autodesk.Revit.DB import Viewport as VP
        for vpid in s.GetAllViewports():
            vp = doc.GetElement(vpid)
            if vp:
                placed_ids.add(vp.ViewId)
    except Exception:
        pass

unplaced_views = [v.Name for v in plan_views + section_views if v.Id not in placed_ids]
no_scale_views = [v.Name for v in plan_views + section_views if v.Scale == 0 or v.Scale == 1]

data["plan_view_count"]    = len(plan_views)
data["section_view_count"] = len(section_views)
data["unplaced_views"]     = unplaced_views[:20]
data["no_scale_views"]     = no_scale_views[:20]

# Grids
grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
data["grid_count"] = len(grids)

# Dimensions and tags counts
dims = list(FilteredElementCollector(doc).OfClass(Dimension).ToElements())
texts = list(FilteredElementCollector(doc).OfClass(TextElement).ToElements())
data["dimension_count"] = len(dims)
data["text_note_count"]  = len(texts)
data["tag_count"]        = len(all_tags)

# Duplicate room numbers
room_nums = [r["number"] for r in room_data if r["number"]]
duplicates = [n for n in set(room_nums) if room_nums.count(n) > 1]
data["duplicate_room_numbers"] = duplicates

# Rooms with no name or zero area
unnamed_rooms = [r["number"] for r in room_data if not r["name"] or r["name"] == "Room"]
zero_area     = [r["number"] for r in room_data if r["area_sqm"] < 0.1]
data["unnamed_rooms"]  = unnamed_rooms[:20]
data["zero_area_rooms"] = zero_area[:20]

# Sheets missing drawn_by
sheets_missing_info = [s["number"] for s in sheet_data if not s["drawn_by"]]
data["sheets_missing_drawn_by"] = sheets_missing_info[:20]

output.print_md("Data collected. Running Claude audit...")

# ── Claude audit ──────────────────────────────────────────────
SYSTEM = """\
You are a senior BIM Manager and architectural drawing auditor specialising in {standard}.

Analyse the model data below and produce a STRUCTURED AUDIT REPORT with these exact sections:

## 1. Model Overview
Counts summary, overall health rating (RAG: Red/Amber/Green), one-paragraph assessment.

## 2. Space Planning Audit
- Room count, areas, adjacency logic observations
- Flag rooms under standard minimum areas (UK: bathroom 4sqm, bedroom 7.5sqm, kitchen 5.5sqm)
- Flag rooms with no name, number, or zero area
- Flag duplicate room numbers
- Accessibility observations where inferable (Part M / ADA)

## 3. Drawing Completeness Audit
- Views without scales set
- Views not placed on any sheet
- Sheets missing Drawn By / Checked By information
- Missing standard view types (e.g. no 3D view, no site plan, no sections)

## 4. Annotation Audit
- Rooms without tags
- Dimension count relative to wall/room count (flag if very low)
- Text note count
- Grid count vs. wall count ratio

## 5. BIM Data Quality
- Parameter completeness
- Duplicate room numbers
- Unnamed/unplaced rooms
- Wall types without clear names

## 6. Code Compliance Flags ({standard})
Based on data, flag likely compliance issues. Be specific — reference actual regulation numbers.
E.g. "Room 101 (4.2sqm) may not meet Part M minimum for accessible bedroom (7.5sqm)"

## 7. Priority Action List
Numbered list, most critical first. Each item: severity [CRITICAL/WARNING/INFO], what to fix, which element.

## 8. Positive Observations
What is done well in this model.

Be specific. Reference actual data. Do not be generic.
""".format(standard=region)

prompt = "Audit this Revit architectural model:\n\n{}".format(json.dumps(data, indent=2, ensure_ascii=True))

try:
    report = ask_claude(prompt, system=SYSTEM, max_tokens=3000)
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("---")
output.print_md(report)
output.print_md("---")
output.print_md("*Audit: {} walls | {} rooms | {} sheets | {} levels | {} tags | {} dimensions*".format(
    len(walls), len(rooms), len(sheets), len(levels), len(all_tags), len(dims)))

forms.alert(
    "Arch Audit complete.\n\nFull report in the output window.\n\n"
    "Standard: {}\nRooms: {}  |  Sheets: {}  |  Walls: {}".format(
        region, len(rooms), len(sheets), len(walls)),
    title="Architectural Audit"
)
