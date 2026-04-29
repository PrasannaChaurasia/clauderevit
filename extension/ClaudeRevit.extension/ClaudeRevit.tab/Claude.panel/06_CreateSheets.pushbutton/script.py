# -*- coding: utf-8 -*-
__title__ = "Create\nSheets"
__doc__ = "Claude creates Revit sheets from plain English. Describe what you need."

import sys, os, json
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (FilteredElementCollector, ViewSheet,
                                BuiltInCategory, ElementId)
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

existing = [{"number": s.SheetNumber, "name": s.Name}
            for s in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements()]

tbs = list(FilteredElementCollector(doc)
           .OfCategory(BuiltInCategory.OST_TitleBlocks)
           .WhereElementIsElementType()
           .ToElements())

if not tbs:
    forms.alert("No title blocks found in this project. Load a title block family first.",
                title="No Title Blocks", exitscript=True)

tb_options = {}
for t in tbs:
    try:
        p = t.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_AND_TYPE_NAMES_PARAM)
        name = p.AsString() if p and p.AsString() else "{} - {}".format(t.FamilyName, t.Name)
    except Exception:
        name = "{} - {}".format(t.FamilyName, t.Name)
    if name:
        tb_options[name] = t.Id
tb_names = list(tb_options.keys())

instruction = forms.ask_for_string(
    prompt=(
        "Describe the sheets to create.\n\n"
        "Examples:\n"
        "  Create sheets A001 Location Plan, A100 Ground Floor Plan, A101 First Floor Plan\n"
        "  Structural sheets S001-S010 all named Structural General Arrangement\n"
        "  Duplicate A100 as A101, A102, A103 with same name\n"
        "  Create 20 sheets A100 to A120 named Floor Plan - Level [n]\n\n"
        "Existing: {ex}"
    ).format(ex=", ".join(s["number"] for s in existing[:10]) or "None"),
    title="Create Sheets",
    default=""
)

if not instruction:
    script.exit()

tb_choice = forms.SelectFromList.show(tb_names, title="Select Title Block", multiselect=False)
if not tb_choice:
    script.exit()

tb_id = tb_options[tb_choice]

full_system = (
    "You are a Revit API Python expert. Generate IronPython 2.7 code to create ViewSheets.\n\n"
    "ENVIRONMENT (in scope):\n"
    "  doc, uidoc, revit, DB, forms, output, all DB classes.\n"
    "  tb_id is already defined in scope — use it directly.\n\n"
    "KEY API:\n"
    "  with revit.Transaction('Create Sheets'):\n"
    "      sheet = ViewSheet.Create(doc, tb_id)\n"
    "      sheet.SheetNumber = 'A100'\n"
    "      sheet.Name = 'Ground Floor Plan'\n\n"
    "RULES:\n"
    "  - Use .format() only. No f-strings.\n"
    "  - forms.alert('msg', title='X') only.\n"
    "  - Skip sheet numbers that already exist (wrap in try/except).\n"
    "  - Return ONLY executable Python. No markdown. No explanation.\n"
    "  - End with: forms.alert('Sheets created: X sheets', title='Done')\n\n"
    "EXISTING SHEETS: " + json.dumps(existing[:15]) + "\n\n"
    "INSTRUCTION: " + instruction
)

output.print_md("# Create Sheets")
output.print_md("**Instruction:** " + instruction)
output.print_md("Generating...")

try:
    code = strip_fences(ask_claude(instruction, system=full_system))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_code(code)

go = forms.alert("Claude will create sheets. Fully undoable.",
                 title="Create Sheets?", cancel=True)
if not go:
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ctx["tb_id"] = tb_id
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Error — see output.\n\n" + err[:400], title="Sheet Error")
