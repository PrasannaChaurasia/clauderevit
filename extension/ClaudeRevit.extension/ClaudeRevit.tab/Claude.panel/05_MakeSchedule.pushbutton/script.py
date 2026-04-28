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
        "  Door schedule: Mark, Width, Height, Level\n"
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

CRITICAL SCHEDULE API RULES:
  # For element schedules (walls, rooms, doors, windows, floors, etc.):
  sched = ViewSchedule.CreateSchedule(doc, ElementId(BuiltInCategory.OST_Walls))

  # For sheet lists ONLY — do NOT use CreateSchedule for sheets:
  sched = ViewSchedule.CreateSheetList(doc)

  # NEVER use OST_Sheets with CreateSchedule — it will throw an exception.

  # Add fields:
  definition = sched.Definition
  for sf in definition.GetSchedulableFields():
      fname = sf.GetName(doc)
      if fname in ["Type Name", "Length", "Area"]:
          try:
              definition.AddField(sf)
          except Exception:
              pass

  # Sort (get field from definition after adding):
  added = definition.GetFieldOrder()
  if added:
      field = definition.GetField(added[0])
      sort_field = ScheduleSortGroupField(field.FieldId, ScheduleSortOrder.Ascending)
      definition.AddSortGroupField(sort_field)

VALID CATEGORIES for CreateSchedule:
  OST_Walls, OST_Rooms, OST_Doors, OST_Windows, OST_Floors,
  OST_Ceilings, OST_Levels, OST_StructuralFraming, OST_Furniture,
  OST_MechanicalEquipment, OST_PipeAccessory, OST_DuctCurves

COMMON FIELD NAMES (match doc field names exactly using GetName(doc)):
  Walls   : "Type Name", "Length", "Area", "Volume", "Base Constraint", "Top Constraint"
  Rooms   : "Number", "Name", "Area", "Level", "Perimeter", "Department"
  Doors   : "Mark", "Width", "Height", "Level", "Family and Type", "Count"
  Windows : "Mark", "Width", "Height", "Level", "Family and Type"
  Sheets  : "Sheet Number", "Sheet Name", "Drawn By", "Checked By", "Approved By"
  Floors  : "Type Name", "Area", "Volume", "Level"

TRANSACTION:
  with revit.Transaction("Create Schedule"):
      sched = ...
      ...
  # Note: the schedule object remains valid AFTER the transaction closes.
  # You can set sched.Name before or inside the transaction.

RULES (IronPython 2.7):
  - "{}".format() ONLY. No f-strings.
  - forms.alert("msg", title="X") only. No ok_btn, no warn_icon.
  - Return ONLY executable Python. No markdown. No explanation.
  - Wrap field AddField in try/except (some fields may be unavailable).
  - End with: forms.alert("Schedule created: " + sched.Name, title="Done")
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

go = forms.alert(
    "Claude will create a schedule. Fully undoable with Ctrl+Z.",
    title="Create Schedule?", cancel=True
)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="Schedule Error")
