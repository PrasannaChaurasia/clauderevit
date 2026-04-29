# -*- coding: utf-8 -*-
__title__ = "Direct\nShape"
__doc__ = "Push any geometry into Revit as a DirectShape element — the fastest way to place custom 3D forms, imported mesh geometry, or mathematically generated solids without creating a family."

import sys, os, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, DirectShape, ElementId,
    BuiltInCategory, XYZ, Line, Arc, TessellatedShapeBuilder,
    TessellatedFace, TessellatedShapeBuilderResult,
    TessellatedShapeBuilderTarget, TessellatedShapeBuilderFallback
)
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

try:
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    model_ctx = "{}  |  Levels:[{}]".format(doc.Title, ", ".join(l.Name for l in levels))
except Exception:
    model_ctx = doc.Title

# ── Shape selector ────────────────────────────────────────────
shape_type = forms.CommandSwitchWindow.show(
    [
        "Box / rectangular prism",
        "Cylinder",
        "Pyramid / tapered form",
        "Sphere (approximated)",
        "Irregular polyhedron",
        "Extruded profile",
        "Custom — describe your shape",
    ],
    message="Select DirectShape geometry type:"
)
if not shape_type:
    script.exit()

description = forms.ask_for_string(
    prompt=(
        "Describe the shape to create.\n\n"
        "Examples:\n"
        "  Box 3m x 2m x 4m at origin on Level 0\n"
        "  Cylinder radius 1.5m height 5m at grid intersection A1\n"
        "  Pyramid 4m x 4m base, 6m tall, centred at origin\n"
        "  Sphere radius 2m at XY centre 5,5\n"
        "  Irregular 5-sided prism from coordinates: (0,0),(4,0),(5,3),(3,5),(0,4), height 3m\n\n"
        "Specify position (X,Y in metres from project origin) and the level."
    ),
    title="DirectShape — {}".format(shape_type),
    default=""
)
if not description:
    script.exit()

# ── Category selector ─────────────────────────────────────────
category = forms.CommandSwitchWindow.show(
    ["Generic Model", "Mass", "Structural Column", "Wall", "Furniture"],
    message="Assign to category:"
)
cat_map = {
    "Generic Model":    BuiltInCategory.OST_GenericModel,
    "Mass":             BuiltInCategory.OST_Mass,
    "Structural Column": BuiltInCategory.OST_StructuralColumns,
    "Wall":             BuiltInCategory.OST_Walls,
    "Furniture":        BuiltInCategory.OST_Furniture,
}
bic = cat_map.get(category or "Generic Model", BuiltInCategory.OST_GenericModel)

output.print_md("# DirectShape Generator")
output.print_md("**Shape:** {}  |  **Category:** {}".format(shape_type, category))
output.print_md("**Description:** {}".format(description))
output.print_md("Generating with Claude...")

SYSTEM = """\
You are a Revit API expert. Generate IronPython 2.7 code to create a DirectShape element in Revit.

ENVIRONMENT (in scope):
  doc, uidoc, revit, DB, forms, output
  DirectShape, TessellatedShapeBuilder, TessellatedFace, XYZ, ElementId, BuiltInCategory
  All DB classes available. import math is allowed.

UNITS: decimal feet. 1m = 3.28084 ft.

THE CORRECT DIRECTSHAPE WORKFLOW:

import math
from Autodesk.Revit.DB import (
    DirectShape, TessellatedShapeBuilder, TessellatedFace,
    TessellatedShapeBuilderTarget, TessellatedShapeBuilderFallback,
    ElementId, BuiltInCategory, XYZ
)

# Example: create a box DirectShape
def ft(m): return m * 3.28084

with revit.Transaction("Create DirectShape"):
    builder = TessellatedShapeBuilder()
    builder.OpenConnectedFaceSet(False)

    # Bottom face (Z=0) — always use ElementId.InvalidElementId for material
    bottom = [XYZ(0,0,0), XYZ(ft(3),0,0), XYZ(ft(3),ft(2),0), XYZ(0,ft(2),0)]
    builder.AddFace(TessellatedFace(bottom, ElementId.InvalidElementId))

    # Top face
    top = [XYZ(0,ft(2),ft(4)), XYZ(ft(3),ft(2),ft(4)), XYZ(ft(3),0,ft(4)), XYZ(0,0,ft(4))]
    builder.AddFace(TessellatedFace(top, ElementId.InvalidElementId))

    # 4 side faces (quads) — always use ElementId.InvalidElementId for material
    sides = [
        [XYZ(0,0,0), XYZ(0,0,ft(4)), XYZ(ft(3),0,ft(4)), XYZ(ft(3),0,0)],
        [XYZ(ft(3),0,0), XYZ(ft(3),0,ft(4)), XYZ(ft(3),ft(2),ft(4)), XYZ(ft(3),ft(2),0)],
        [XYZ(ft(3),ft(2),0), XYZ(ft(3),ft(2),ft(4)), XYZ(0,ft(2),ft(4)), XYZ(0,ft(2),0)],
        [XYZ(0,ft(2),0), XYZ(0,ft(2),ft(4)), XYZ(0,0,ft(4)), XYZ(0,0,0)],
    ]
    for face_pts in sides:
        builder.AddFace(TessellatedFace(face_pts, ElementId.InvalidElementId))

    # IMPORTANT: Must set Target BEFORE calling Build()
    # Use AnyGeometry to avoid "Multiple targets could match" error

    builder.CloseConnectedFaceSet()
    builder.Target = TessellatedShapeBuilderTarget.AnyGeometry
    builder.Fallback = TessellatedShapeBuilderFallback.Salvage
    builder.Build()
    result = builder.GetBuildResult()

    ds = DirectShape.CreateElement(doc, ElementId(BuiltInCategory.OST_GenericModel))
    ds.SetShape(result.GetGeometricalObjects())
    ds.Name = "Box 3x2x4m"

forms.alert("DirectShape created.", title="Done")

STRICT RULES (IronPython 2.7):
  - "{}".format() ONLY. Zero f-strings.
  - No type hints, no walrus :=
  - forms.alert("msg", title="X") only
  - Return ONLY executable Python. No markdown.
  - All faces must be PLANAR (quads or triangles). For curves, approximate with many segments.
  - TessellatedFace material: ALWAYS use ElementId.InvalidElementId — never DB.MaterialsMaterialId
  - builder.Target: ALWAYS use TessellatedShapeBuilderTarget.AnyGeometry — never .Solid alone (causes "Multiple targets" error)
  - builder.Fallback: TessellatedShapeBuilderFallback.Salvage
  - Wrap in try/except. End with forms.alert("Done: ...", title="DirectShape")
"""

bic_name = category or "Generic Model"
prompt = "Create a DirectShape in category '{}'. Shape type: {}. Description: {}".format(
    bic_name, shape_type, description)

try:
    code = strip_fences(ask_claude(prompt, system=SYSTEM, max_tokens=2000))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("**Generated code:**")
output.print_code(code)

if not forms.alert(
    "Review the code above.\nThis creates a DirectShape in category: {}\n\nFully undoable with Ctrl+Z.\n\nProceed?".format(bic_name),
    title="Create DirectShape?", cancel=True
):
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("DirectShape error:\n\n{}".format(err[:500]), title="Error")
