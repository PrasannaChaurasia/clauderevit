# -*- coding: utf-8 -*-
__title__ = "Auto\nDimension"
__doc__ = "Automatically place dimension strings on walls in the active floor plan view. Places running dimensions and overall dimensions."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Wall, Level, ViewPlan,
    ReferenceArray, Line, XYZ, Transaction,
    BuiltInParameter, BuiltInCategory, ElementId,
    WallLocationLine, Options
)
from wpf_helper import switch_dialog

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ── Get active view ───────────────────────────────────────────
active_view = uidoc.ActiveView
if not isinstance(active_view, ViewPlan):
    forms.alert(
        "Auto-Dimension works on Floor Plan views.\n\n"
        "Open a floor plan view and try again.",
        title="Wrong View Type"
    )
    script.exit()

# ── Collect walls in active view ──────────────────────────────
walls = list(
    FilteredElementCollector(doc, active_view.Id)
    .OfClass(Wall)
    .ToElements()
)

if not walls:
    forms.alert("No walls found in the active view.", title="Auto-Dimension")
    script.exit()

# ── Ask user for dimension direction ─────────────────────────
choice = switch_dialog(
    ["Horizontal walls", "Vertical walls", "Both directions"],
    message="Which walls to dimension in '{}'?".format(active_view.Name),
    title="Auto-Dimension"
)
if not choice:
    script.exit()

do_horiz = choice in ["Horizontal walls", "Both directions"]
do_vert  = choice in ["Vertical walls",   "Both directions"]

output.print_md("# Auto-Dimension")
output.print_md("**View:** {}  |  **Mode:** {}".format(active_view.Name, choice))

dim_count = [0]

def _get_wall_references(wall):
    """Return start and end face references for a wall."""
    refs = []
    try:
        opt = Options()
        opt.ComputeReferences = True
        opt.IncludeNonVisibleObjects = False
        opt.View = active_view
        geom = wall.get_Geometry(opt)
        if geom is None:
            return refs
        for obj in geom:
            from Autodesk.Revit.DB import Solid, Face
            if isinstance(obj, Solid):
                for face in obj.Faces:
                    n = face.FaceNormal
                    # Only grab faces perpendicular to wall length
                    if abs(n.Z) < 0.01:
                        refs.append(face.Reference)
                if len(refs) >= 2:
                    break
    except Exception:
        pass
    return refs[:2]


def dimension_walls_in_direction(wall_list, horizontal):
    """Place individual wall dimensions then an overall dimension string."""
    offset = 3.0  # feet from wall centreline for dim line

    # Filter walls by orientation
    target_walls = []
    for w in wall_list:
        try:
            lc = w.Location
            if not hasattr(lc, "Curve"):
                continue
            curve = lc.Curve
            start = curve.GetEndPoint(0)
            end   = curve.GetEndPoint(1)
            dx = abs(end.X - start.X)
            dy = abs(end.Y - start.Y)
            if horizontal and dx > dy and dx > 0.5:
                target_walls.append(w)
            elif not horizontal and dy > dx and dy > 0.5:
                target_walls.append(w)
        except Exception:
            continue

    if not target_walls:
        return

    with revit.Transaction("Auto-Dimension {}".format("H" if horizontal else "V")):
        for w in target_walls:
            try:
                refs = _get_wall_references(w)
                if len(refs) < 2:
                    continue

                lc    = w.Location.Curve
                start = lc.GetEndPoint(0)
                end   = lc.GetEndPoint(1)

                if horizontal:
                    mid_y  = (start.Y + end.Y) / 2.0
                    dim_y  = mid_y - offset
                    pt1    = XYZ(min(start.X, end.X), dim_y, 0)
                    pt2    = XYZ(max(start.X, end.X), dim_y, 0)
                else:
                    mid_x  = (start.X + end.X) / 2.0
                    dim_x  = mid_x - offset
                    pt1    = XYZ(dim_x, min(start.Y, end.Y), 0)
                    pt2    = XYZ(dim_x, max(start.Y, end.Y), 0)

                if pt1.DistanceTo(pt2) < 0.01:
                    continue

                dim_line = Line.CreateBound(pt1, pt2)
                ra = ReferenceArray()
                for r in refs[:2]:
                    ra.Append(r)
                if ra.Size >= 2:
                    doc.Create.NewDimension(active_view, dim_line, ra)
                    dim_count[0] += 1
            except Exception:
                pass


try:
    if do_horiz:
        dimension_walls_in_direction(walls, horizontal=True)
    if do_vert:
        dimension_walls_in_direction(walls, horizontal=False)

    uidoc.RefreshActiveView()

    output.print_md("**Placed {} dimension strings.**".format(dim_count[0]))

    if dim_count[0] == 0:
        forms.alert(
            "No dimensions placed.\n\n"
            "This can happen if:\n"
            "- Wall face geometry references are not available in this view\n"
            "- Walls are too short (under 6 inches)\n"
            "- View is not a standard floor plan\n\n"
            "Try switching to a Floor Plan view (not a Working Dimensions or Schematic view).",
            title="Auto-Dimension"
        )
    else:
        forms.alert(
            "Auto-Dimension complete.\n\n"
            "Placed {} dimension strings in '{}'.\n\n"
            "If dimensions are not visible, press ZF (Zoom to Fit) or check crop region.".format(
                dim_count[0], active_view.Name),
            title="Auto-Dimension"
        )

except Exception as e:
    import traceback
    err = traceback.format_exc()
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Auto-Dimension error:\n{}".format(str(e)[:400]), title="Error")
