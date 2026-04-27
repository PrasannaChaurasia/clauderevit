# -*- coding: utf-8 -*-
__title__ = "Claude\nCommand"
__doc__ = "Type any instruction. Claude writes and executes the Revit API code live."

import sys
import os

# -- lib path --
_lib = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(_lib))

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Wall, Floor, ViewSheet, Level
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ---- Gather model context ----
try:
    walls  = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    floors = FilteredElementCollector(doc).OfClass(Floor).GetElementCount()
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    level_names = ", ".join(l.Name for l in levels)
    model_ctx = "Model: {} | Walls:{} Floors:{} Sheets:{} Levels:[{}]".format(
        doc.Title, walls, floors, sheets, level_names)
except Exception as e:
    model_ctx = "Model: {} (context error: {})".format(doc.Title, e)

# ---- Ask user ----
instruction = forms.ask_for_string(
    prompt=(
        "Type your Revit instruction in plain English.\n\n"
        "Examples:\n"
        "  Create 3 levels at 3m, 6m, 9m\n"
        "  Build a 10m x 8m rectangular room with walls on Level 0\n"
        "  Create sheets A101 to A110 with title block A1\n"
        "  Add a floor plan view for every level\n"
        "  Rename all rooms on Level 0 with prefix GF-\n"
        "  Create a wall schedule with Type, Length, Area\n\n"
        + model_ctx
    ),
    title="Claude Command — {}".format(doc.Title),
    default=""
)

if not instruction:
    script.exit()

# ---- System prompt for Claude ----
SYSTEM = """\
You are a Revit API Python expert writing code for pyRevit (IronPython 2.7).

ENVIRONMENT — these are already available, do NOT re-import:
  doc      → Autodesk.Revit.DB.Document
  uidoc    → Autodesk.Revit.UI.UIDocument
  revit    → pyrevit.revit module
  DB       → Autodesk.Revit.DB module
  forms    → pyrevit.forms module
  output   → pyrevit script output
  All DB classes (XYZ, Line, Wall, Level, ViewSheet, etc.) are in scope directly.

UNITS: Revit internal = decimal feet. Always convert: 1m = 3.28084 ft.

TRANSACTIONS: Wrap ALL model changes in:
  with revit.Transaction("description"):
      ...

RULES:
  - Return ONLY executable Python code. No markdown fences. No explanation.
  - Do not import anything — everything is already in scope.
  - Handle exceptions with try/except and surface them via forms.alert().
  - End every script with: forms.alert("Done: <summary>", title="Claude", warn_icon=False)

MODEL CONTEXT: """ + model_ctx

# ---- Call Claude ----
output.print_md("# Claude Command")
output.print_md("**Instruction:** " + instruction)
output.print_md("Generating code with claude-sonnet-4-6...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("**Generated code — review before running:**")
output.print_code(code)

# ---- Confirm ----
go = forms.alert(
    "Review the code above in the output window.\n\n"
    "Everything is undoable with Ctrl+Z.\n\nProceed?",
    title="Execute Claude Code?",
    ok_btn="Run",
    cancel=True
)
if not go:
    output.print_md("*Cancelled.*")
    script.exit()

# ---- Execute ----
ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Execution error:**\n```\n{}\n```".format(err))
    forms.alert("Execution failed. See output window for details.\n\n{}".format(err[:500]),
                title="Claude Command Error")
