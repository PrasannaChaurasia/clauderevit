# -*- coding: utf-8 -*-
__title__ = "Place\nRooms"
__doc__ = "Describe a room layout — Claude places and names rooms on your floor plans."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, BuiltInCategory, BuiltInParameter
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

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

instruction = forms.ask_for_string(
    prompt=(
        "Describe the rooms to place.\n\n"
        "Examples:\n"
        "  Residential: Living Room, Kitchen, Bedroom 1, Bedroom 2, Bathroom on Level 0\n"
        "  Office: Reception, 4 Offices, Meeting Room, Kitchen on Level 0\n"
        "  Hotel room: Entrance, Bedroom, Ensuite, Wardrobe\n\n"
        "Levels: {lvl}\nExisting rooms: {er}"
    ).format(
        lvl=", ".join(l["name"] for l in level_info),
        er=", ".join(r["name"] for r in existing_rooms[:8]) or "None"
    ),
    title="Place Rooms",
    default=""
)

if not instruction:
    script.exit()

SYSTEM = """\
You are a Revit API Python expert. Generate IronPython 2.7 code to place rooms in Revit.

ENVIRONMENT (in scope):
  doc, uidoc, revit, DB, forms, output, all DB classes.

KEY APIs:
  # Get level
  lvl = next(l for l in FilteredElementCollector(doc).OfClass(Level).ToElements() if l.Name == "Level 0")

  # Place room at UV position (in feet from origin)
  room = doc.Create.NewRoom(lvl, UV(x_ft, y_ft))
  room.get_Parameter(BuiltInParameter.ROOM_NAME).Set("Living Room")
  room.get_Parameter(BuiltInParameter.ROOM_NUMBER).Set("GF-01")

POSITIONING:
  - Start grid at UV(5, 5). Each room spaced 20ft apart in a row.
  - Rooms must be inside wall boundaries to get area — if no walls, place them anyway (area will be unenclosed).
  - Number rooms sequentially: GF-01, GF-02 etc.

TRANSACTION:
  with revit.Transaction("Place Rooms"):
      ...

RULES:
  - Return ONLY executable Python. No markdown. No explanation.
  - End with: forms.alert("Rooms placed", title="Done")

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
