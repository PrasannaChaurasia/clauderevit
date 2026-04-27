# -*- coding: utf-8 -*-
__title__ = "Build\nModel"
__doc__ = "Describe a building. Claude creates walls, levels, floors, and geometry."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, Wall, WallType
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

levels     = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
wall_types = list(FilteredElementCollector(doc).OfClass(WallType).ToElements())
level_info = [{"name": l.Name, "elev_ft": round(l.Elevation, 4)} for l in levels]
wt_names   = [wt.Name for wt in wall_types[:8]]

brief = forms.ask_for_string(
    prompt=(
        "Describe the building or space to build.\n\n"
        "Examples:\n"
        "  Rectangular room 6m x 4m x 3m tall on Level 0, Generic 200mm walls\n"
        "  Two-storey building 12m x 8m. Ground floor 3.5m, First floor 3m.\n"
        "  L-shaped plan: 10m x 4m + 4m x 6m wing on Level 0\n\n"
        "Levels: {lvl}\nWall types: {wt}"
    ).format(
        lvl=", ".join(l["name"] for l in level_info),
        wt=", ".join(wt_names)
    ),
    title="Build Model — {}".format(doc.Title),
    default=""
)

if not brief:
    script.exit()

SYSTEM = """\
You are a Revit API Python expert. Generate IronPython 2.7 code for pyRevit that builds Revit geometry from a plain-English brief.

ENVIRONMENT (already in scope, do NOT import):
  doc, uidoc, revit, DB, forms, output
  All Autodesk.Revit.DB classes: XYZ, Line, Wall, Level, Floor, etc.

UNITS: decimal feet. 1m = 3.28084 ft. Always convert.

KEY APIs:
  # Get level
  lvl = next((l for l in FilteredElementCollector(doc).OfClass(Level).ToElements() if l.Name == "Level 0"), None)

  # Get wall type
  wt = next((w for w in FilteredElementCollector(doc).OfClass(WallType).ToElements() if "200" in w.Name), None)

  # Create wall (structural=False, offset=0)
  line = Line.CreateBound(XYZ(0,0,0), XYZ(19.685,0,0))  # 6m in feet
  Wall.Create(doc, line, wt.Id, lvl.Id, 9.843, 0.0, False, False)  # height 3m

  # Create floor
  curve_array = CurveArray()
  curve_array.Append(Line.CreateBound(XYZ(0,0,0), XYZ(6.562,0,0)))
  # ... add all edges
  floor_type = next(ft for ft in FilteredElementCollector(doc).OfClass(FloorType).ToElements())
  Floor.Create(doc, curve_array, floor_type.Id, lvl.Id)

TRANSACTION: wrap all changes:
  with revit.Transaction("Build Model"):
      ...

RULES:
  - Return ONLY executable Python. No markdown. No explanation.
  - Avoid duplicate walls — use distinct coordinates.
  - End with: forms.alert("Model built", title="Done", warn_icon=False)

AVAILABLE CONTEXT:
Levels: {lvl}
Wall types: {wt}
""".format(lvl=json.dumps(level_info), wt=", ".join(wt_names))

output.print_md("# Build Model")
output.print_md("**Brief:** " + brief)
output.print_md("Generating...")

try:
    code = strip_fences(ask_claude(brief, system=SYSTEM))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_code(code)

go = forms.alert(
    "Claude will build geometry in your model.\nFully undoable with Ctrl+Z.",
    title="Build Model?", ok_btn="Build", cancel=True
)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="Build Error")
