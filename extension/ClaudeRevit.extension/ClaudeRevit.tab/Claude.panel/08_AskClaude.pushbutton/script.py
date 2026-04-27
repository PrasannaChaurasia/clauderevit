# -*- coding: utf-8 -*-
__title__ = "Ask\nClaude"
__doc__ = "Ask Claude anything about your model, BIM standards, or Revit workflows."

import sys, os
_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (FilteredElementCollector, Wall, Floor,
    ViewSheet, Level, BuiltInCategory)
from claude_client import ask_claude

doc    = revit.doc
output = script.get_output()

# Quick model snapshot
try:
    walls  = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    rooms  = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).GetElementCount()
    lvl_names = ", ".join(l.Name for l in levels)
    model_ctx = "Model: {} | Walls:{} Sheets:{} Rooms:{} Levels:[{}]".format(
        doc.Title, walls, sheets, rooms, lvl_names)
except Exception as e:
    model_ctx = "Model: {} (snapshot error: {})".format(doc.Title, e)

question = forms.ask_for_string(
    prompt=(
        "Ask Claude anything.\n\n"
        "Examples:\n"
        "  What is the recommended wall structure for a UK residential project?\n"
        "  How should I organise my sheet numbering for a mixed-use development?\n"
        "  What BIM Level 2 requirements apply to my model?\n"
        "  How do I create a parametric curtain wall in Revit?\n"
        "  What data should I capture in room parameters for a healthcare project?\n\n"
        + model_ctx
    ),
    title="Ask Claude",
    default=""
)

if not question:
    script.exit()

SYSTEM = """\
You are an expert architectural BIM consultant specialising in Autodesk Revit, UK building standards, and BIM Level 2.
You are working with Prasanna Chaurasia, an architectural designer and BIM specialist at Urban Matrix, Manchester.
Give precise, actionable answers. Reference real Revit workflows and UK standards where relevant.
Current model context: """ + model_ctx

try:
    answer = ask_claude(question, system=SYSTEM)
except Exception as e:
    forms.alert("Claude API error:\n{}".format(e))
    script.exit()

output.print_md("# Claude says")
output.print_md("**Q:** " + question)
output.print_md("---")
output.print_md(answer)
