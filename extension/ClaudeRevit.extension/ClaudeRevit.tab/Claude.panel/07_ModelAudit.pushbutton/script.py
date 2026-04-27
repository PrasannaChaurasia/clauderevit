# -*- coding: utf-8 -*-
__title__ = "Model\nAudit"
__doc__ = "Claude reads your full model and produces a structured BIM audit report."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (FilteredElementCollector, Wall, Floor,
    ViewSheet, Level, BuiltInCategory, BuiltInParameter)
from claude_client import ask_claude

doc    = revit.doc
output = script.get_output()

output.print_md("# Claude Model Audit — {}".format(doc.Title))
output.print_md("Collecting model data — please wait...")

# --- Walls ---
walls = list(FilteredElementCollector(doc).OfClass(Wall).ToElements())
wall_data = []
for w in walls:
    try:
        lp = w.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
        wall_data.append({
            "type": w.WallType.Name,
            "length_m": round(lp.AsDouble() * 0.3048, 2) if lp else 0
        })
    except:
        pass

# --- Rooms ---
rooms = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).ToElements())
room_data = []
for r in rooms:
    try:
        area_p  = r.get_Parameter(BuiltInParameter.ROOM_AREA)
        name_p  = r.get_Parameter(BuiltInParameter.ROOM_NAME)
        num_p   = r.get_Parameter(BuiltInParameter.ROOM_NUMBER)
        level_p = r.get_Parameter(BuiltInParameter.ROOM_LEVEL_ID)
        room_data.append({
            "name":    name_p.AsString() if name_p else "?",
            "number":  num_p.AsString()  if num_p  else "?",
            "area_sqm": round(area_p.AsDouble() * 0.0929, 2) if area_p else 0
        })
    except:
        pass

# --- Sheets ---
sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
sheet_data = [{"number": s.SheetNumber, "name": s.Name} for s in sheets]

# --- Levels ---
levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
level_data = [{"name": l.Name, "elev_m": round(l.Elevation * 0.3048, 2)} for l in levels]

# --- Summary for Claude ---
model_data = {
    "model_name": doc.Title,
    "walls":  wall_data[:60],
    "rooms":  room_data[:60],
    "sheets": sheet_data[:30],
    "levels": level_data
}

SYSTEM = """\
You are a senior BIM Manager and Revit auditor.
Analyse the model data and return a structured audit report with these sections:

1. **Model Overview** — counts, levels, general health
2. **Walls** — flag any zero-length walls, duplicate types, anything unusual
3. **Rooms** — flag unnamed rooms, zero-area rooms, missing numbers, duplicates
4. **Sheets** — flag missing sheets for expected drawing types, duplicates
5. **Levels** — flag unusual spacing, missing ground/roof levels
6. **BIM Issues** — ranked list of things to fix, highest priority first
7. **Recommendations** — 3-5 actionable next steps

Be specific, not generic. Reference actual data from the model.
"""

output.print_md("Running Claude audit (claude-sonnet-4-6)...")

try:
    report = ask_claude(
        "Audit this Revit model:\n\n" + json.dumps(model_data, indent=2),
        system=SYSTEM
    )
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_md("---")
output.print_md(report)
output.print_md("---")
output.print_md(
    "*Stats: {} walls | {} rooms | {} sheets | {} levels*".format(
        len(walls), len(rooms), len(sheets), len(levels)
    )
)
