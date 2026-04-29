# -*- coding: utf-8 -*-
__title__ = "Place\nRooms"
__doc__ = "Describe a room layout — Claude places and names rooms on your floor plans."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, BuiltInCategory, BuiltInParameter
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context
from wpf_helper import chat_prompt

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
level_info = [{"name": l.Name, "elev_ft": round(l.Elevation, 4)} for l in levels]

existing_rooms = []
for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).ToElements():
    try:
        existing_rooms.append({
            "name": r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(),
            "number": r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
        })
    except:
        pass

instruction = chat_prompt(
    title="Place Rooms",
    message=(
        "Describe the rooms to place.\n\n"
        "Examples:\n"
        "  Residential: Living Room, Kitchen, Bedroom 1, Bedroom 2, Bathroom on Level 0\n"
        "  Office: Reception, 4 Offices, Meeting Room, Kitchen on Level 0\n"
        "  Hotel room: Entrance, Bedroom, Ensuite, Wardrobe"
    ),
    context="Levels: {}  |  Existing rooms: {}".format(
        ", ".join(l["name"] for l in level_info),
        ", ".join(r["name"] for r in existing_rooms[:8]) or "None"
    )
)

if not instruction:
    script.exit()

SYSTEM = """\
You are a Revit API Python expert. Generate IronPython 2.7 code to place rooms in Revit.

ENVIRONMENT (in scope, do NOT import anything extra):
  doc, uidoc, revit, DB, forms, output
  FilteredElementCollector, Level, BuiltInCategory, BuiltInParameter, UV — all in scope.

BANNED IMPORTS — NEVER use these (they do not exist in this Revit version):
  ViewDuplicateType, CopyPasteOptions, ElementTransformUtils

KEY API:
  # Get a level
  all_levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
  all_levels.sort(key=lambda l: l.Elevation)
  lvl = all_levels[0]  # use lowest level, or match by name

  # Place room at UV position (feet from project origin)
  room = doc.Create.NewRoom(lvl, UV(x_ft, y_ft))
  room.get_Parameter(BuiltInParameter.ROOM_NAME).Set("Living Room")
  room.get_Parameter(BuiltInParameter.ROOM_NUMBER).Set("GF-01")

POSITIONING STRATEGY:
  - Place rooms in a grid starting at UV(10, 10), spaced 25ft apart.
  - Each room on a new row after 4 rooms.
  - Keep all coordinates positive and reasonable (under 300ft).
  - Rooms without wall boundaries show area=0 — that is normal behaviour.

TRANSACTION:
  with revit.Transaction("Place Rooms"):
      for each room: doc.Create.NewRoom(...)

RULES (IronPython 2.7):
  - "{{}}".format() ONLY. No f-strings.
  - forms.alert("msg", title="X") only.
  - Return ONLY executable Python. No markdown. No explanation.
  - Wrap entire block in try/except.
  - End with: forms.alert("{{}} rooms placed on {{}}".format(count, lvl.Name), title="Done")

LEVELS: {lvl}
""".format(lvl=json.dumps(level_info))

output.print_md("# Place Rooms")
output.print_md("**Instruction:** " + instruction)
output.print_md("Generating...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_code(code)

go = forms.alert("Claude will place rooms. Fully undoable.",
                 title="Place Rooms?", cancel=True)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="Room Error")
