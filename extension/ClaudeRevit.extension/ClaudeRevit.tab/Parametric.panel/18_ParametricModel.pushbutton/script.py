# -*- coding: utf-8 -*-
__title__ = "Parametric\nModel"
__doc__ = "Describe parametric geometry in plain English — Claude generates Revit API code to create adaptive components, patterned facades, twisted forms, or mathematically driven geometry."

import sys, os, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, Wall, FamilySymbol,
    DirectShape, ElementId, BuiltInCategory
)
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

try:
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    level_info = [{"name": l.Name, "elev_m": round(l.Elevation * 0.3048, 3)} for l in levels]
    model_ctx = "{}  |  Levels:[{}]".format(doc.Title, ", ".join(l.Name for l in levels))
except Exception:
    level_info = []
    model_ctx = doc.Title

# ── Geometry type selector ────────────────────────────────────
geom_type = forms.CommandSwitchWindow.show(
    [
        "Parametric facade panel array",
        "Twisted / rotated tower form",
        "Sine wave or curved wall",
        "Point-driven adaptive component grid",
        "Structural grid with columns",
        "Data-driven floor plan from coordinates",
        "Custom — describe anything",
    ],
    message="Select parametric geometry type:"
)
if not geom_type:
    script.exit()

description = forms.ask_for_string(
    prompt=(
        "Describe the parametric geometry.\n\n"
        "Examples for '{}':\n"
        "  Parametric facade: 10 panels wide, 8 panels tall, sine wave pattern, amplitude 0.5m, period 3 panels\n"
        "  Twisted tower: rectangular 12x8m plan, 10 storeys, 3-degree rotation per floor\n"
        "  Sine wall: 15m long, amplitude 1.2m, wavelength 3m, wall height 3m on Level 0\n"
        "  Column grid: 5x4 grid, 6m spacing in X, 8m spacing in Y, starting at origin\n\n"
        "Model levels: {}"
    ).format(geom_type, ", ".join(l["name"] for l in level_info)),
    title="Parametric Model — {}".format(geom_type),
    default=""
)
if not description:
    script.exit()

output.print_md("# Parametric Model")
output.print_md("**Type:** {}".format(geom_type))
output.print_md("**Description:** {}".format(description))
output.print_md("Generating code with Claude...")

SYSTEM = """\
You are a Revit API Python expert specialising in parametric and computational design.
Generate IronPython 2.7 code that creates parametric geometry in Revit.

ENVIRONMENT (in scope, do NOT import):
  doc, uidoc, revit, DB, forms, output
  All DB classes: XYZ, Line, Wall, Level, Floor, DirectShape, CurveArray, etc.
  FilteredElementCollector, BuiltInCategory, ElementId, Transaction

UNITS: Revit internal = decimal feet. Always convert: 1m = 3.28084 ft, 1mm = 1/304.8 ft.

KEY PARAMETRIC APIs:
  import math  # math IS available in IronPython

  # Get a level by name:
  levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
  lvl = next((l for l in levels if "0" in l.Name), levels[0])

  # Create wall from computed points:
  pt1 = XYZ(x1_ft, y1_ft, 0)
  pt2 = XYZ(x2_ft, y2_ft, 0)
  wt = list(FilteredElementCollector(doc).OfClass(WallType).ToElements())[0]
  Wall.Create(doc, Line.CreateBound(pt1, pt2), wt.Id, lvl.Id, height_ft, 0, False, False)

  # DirectShape for custom mesh/solid geometry:
  ds = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_GenericModel))
  # Build TessellatedShapeBuilder or use BRepBuilder for solids

  # Sine wave example (wall along sine curve via short wall segments):
  import math
  n_segments = 40
  for i in range(n_segments):
      t0 = float(i) / n_segments
      t1 = float(i+1) / n_segments
      x0 = t0 * total_length_ft
      y0 = amplitude_ft * math.sin(2 * math.pi * t0 / wavelength_ft * total_length_ft)
      x1 = t1 * total_length_ft
      y1 = amplitude_ft * math.sin(2 * math.pi * t1 / wavelength_ft * total_length_ft)
      if abs(x1-x0) + abs(y1-y0) > 0.01:
          Wall.Create(doc, Line.CreateBound(XYZ(x0,y0,0), XYZ(x1,y1,0)),
                      wt.Id, lvl.Id, height_ft, 0, False, False)

TRANSACTION: with revit.Transaction("Parametric Model"): ...

STRICT RULES (IronPython 2.7):
  - "{}".format() ONLY. Zero f-strings.
  - No type hints, no walrus :=, no match/case
  - import math is allowed and available
  - forms.alert("msg", title="X") only — no ok_btn, no warn_icon
  - Return ONLY executable Python. No markdown. No explanation.
  - Wrap in try/except. End with forms.alert("Done: ...", title="Parametric Model")

MODEL CONTEXT:
  Levels: {}
""".format(json.dumps(level_info))

full_prompt = "Geometry type: {}\nDescription: {}".format(geom_type, description)

try:
    code = strip_fences(ask_claude(full_prompt, system=SYSTEM, max_tokens=2000))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("**Generated code:**")
output.print_code(code)

if not forms.alert(
    "Review the parametric code above.\n\n"
    "This will create geometry in your model.\nFully undoable with Ctrl+Z.\n\nProceed?",
    title="Run Parametric Model?", cancel=True
):
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Parametric error:\n\n{}".format(err[:500]), title="Error")
