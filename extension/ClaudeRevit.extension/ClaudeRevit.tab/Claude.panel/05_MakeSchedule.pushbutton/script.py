# -*- coding: utf-8 -*-
__title__ = "Make\nSchedule"
__doc__ = "Claude creates Revit schedules from plain English."

import sys, os
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, ViewSchedule
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

instruction = forms.ask_for_string(
    prompt=(
        "Describe the schedule to create.\n\n"
        "Examples:\n"
        "  Wall schedule: Type Name, Length, Area, Volume\n"
        "  Room schedule: Number, Name, Area, Level\n"
        "  Door schedule: Mark, Width, Height, Level, Count\n"
        "  Window schedule: Type, Width, Height grouped by type\n"
        "  Sheet list: Number, Name, Revision Date\n"
        "  Floor schedule: Type, Area, Volume\n"
    ),
    title="Make Schedule",
    default=""
)

if not instruction:
    script.exit()

SYSTEM = """\
You are a Revit API Python expert. Generate IronPython 2.7 code to create a ViewSchedule.

ENVIRONMENT (in scope, do NOT import):
  doc, uidoc, revit, DB, forms, output, all DB classes.

KEY APIs:
  # Create schedule for walls:
  sched = ViewSchedule.CreateSchedule(doc, ElementId(BuiltInCategory.OST_Walls))
  sched.Name = "Wall Schedule"

  # Add fields:
  definition = sched.Definition
  for sf in definition.GetSchedulableFields():
      if sf.GetName(doc) in ["Type Name", "Length", "Area"]:
          definition.AddField(sf)

  # Sort by field:
  field = definition.GetField(0)
  sort_field = ScheduleSortGroupField(field.FieldId, ScheduleSortOrder.Ascending)
  definition.AddSortGroupField(sort_field)

COMMON CATEGORIES:
  OST_Walls, OST_Rooms, OST_Doors, OST_Windows, OST_Floors,
  OST_Sheets, OST_Levels, OST_StructuralFraming, OST_Furniture

COMMON FIELD NAMES (match exactly):
  Walls: "Type Name", "Length", "Area", "Volume", "Base Constraint", "Top Constraint"
  Rooms: "Number", "Name", "Area", "Level", "Perimeter"
  Doors/Windows: "Mark", "Width", "Height", "Level", "Family and Type"
  Sheets: "Sheet Number", "Sheet Name", "Drawn By", "Checked By"

TRANSACTION:
  with revit.Transaction("Create Schedule"):
      sched = ViewSchedule.CreateSchedule(...)
      ...

RULES:
  - Return ONLY executable Python. No markdown. No explanation.
  - Wrap field lookup in try/except to skip unavailable fields.
  - End with: forms.alert("Schedule created: " + sched.Name, title="Done", warn_icon=False)
"""

output.print_md("# Make Schedule")
output.print_md("**Instruction:** " + instruction)
output.print_md("Generating...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_code(code)

go = forms.alert("Claude will create a schedule. Fully undoable.",
                 title="Create Schedule?", ok_btn="Create", cancel=True)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="Schedule Error")
