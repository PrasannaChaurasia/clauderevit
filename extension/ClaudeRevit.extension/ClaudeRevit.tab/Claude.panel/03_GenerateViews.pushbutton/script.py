# -*- coding: utf-8 -*-
__title__ = "Generate\nViews"
__doc__ = "Claude creates floor plans, sections, elevations, 3D views."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, ViewFamilyType, ViewFamily, View
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
level_info = [{"name": l.Name, "elev_ft": round(l.Elevation, 4)} for l in levels]

existing_views = [v.Name for v in FilteredElementCollector(doc).OfClass(View).ToElements()
                  if not v.IsTemplate and v.Name][:15]

instruction = forms.ask_for_string(
    prompt=(
        "Describe the views to create.\n\n"
        "Examples:\n"
        "  Floor plan for every level\n"
        "  North South East West elevations\n"
        "  One 3D isometric view of the whole model\n"
        "  Reflected ceiling plan for Level 0\n"
        "  Section through X=5m cutting east-west\n\n"
        "Levels: {lvl}\nExisting views: {ev}"
    ).format(
        lvl=", ".join(l["name"] for l in level_info),
        ev=", ".join(existing_views)
    ),
    title="Generate Views",
    default=""
)

if not instruction:
    script.exit()

SYSTEM = """\
You are a Revit API Python expert. Generate IronPython 2.7 code to create views in Revit.

ENVIRONMENT (in scope, do NOT import):
  doc, uidoc, revit, DB, forms, output
  All Autodesk.Revit.DB classes in scope.

KEY APIs:

  # Get ViewFamilyType for floor plan:
  fp_vft = next(x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
                if x.ViewFamily == ViewFamily.FloorPlan)

  # Create floor plan:
  plan = ViewPlan.Create(doc, fp_vft.Id, level.Id)
  plan.Name = "Floor Plan - Level 0"

  # Get ViewFamilyType for 3D:
  td_vft = next(x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
                if x.ViewFamily == ViewFamily.ThreeDimensional)

  # Create 3D:
  v3d = View3D.CreateIsometric(doc, td_vft.Id)
  v3d.Name = "3D - Overall"

  # Elevation — use ElevationMarker:
  marker = ElevationMarker.CreateElevationMarker(doc, elev_vft.Id, XYZ(0,0,0), 100)
  elev = marker.CreateElevation(doc, plan.Id, 0)  # index 0=North,1=East,2=South,3=West

TRANSACTION:
  with revit.Transaction("Create Views"):
      ...

RULES:
  - Return ONLY executable Python. No markdown. No explanation.
  - End with: forms.alert("Views created", title="Done", warn_icon=False)

LEVELS: {lvl}
""".format(lvl=json.dumps(level_info))

output.print_md("# Generate Views")
output.print_md("**Instruction:** " + instruction)
output.print_md("Generating...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_code(code)

go = forms.alert("Claude will create views. Fully undoable.",
                 title="Create Views?", ok_btn="Create", cancel=True)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="View Error")
