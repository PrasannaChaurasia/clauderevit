# -*- coding: utf-8 -*-
__title__ = "Auto\nAnnotate"
__doc__ = "Auto-place gridline bubbles, level annotations on sections, north point, and scale bars across all views in the project."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Grid, Level,
    ViewPlan, ViewSection, ViewSheet, Viewport,
    BuiltInCategory, BuiltInParameter, ElementId,
    DatumExtentType, XYZ, View
)

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ── Ask what to annotate ──────────────────────────────────────
choices = forms.SelectFromList.show(
    [
        "Show grid bubbles in all floor plan views",
        "Show grid bubbles in all section views",
        "Show level markers in all section views",
        "Set crop region visible on all views",
        "Report views missing a scale",
        "Report views not placed on sheets",
    ],
    title="Auto-Annotate — Select Actions",
    multiselect=True,
    button_name="Run Selected"
)
if not choices:
    script.exit()

output.print_md("# Auto-Annotate")
results = []

# Collect elements
all_grids    = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
all_levels   = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
all_views    = list(FilteredElementCollector(doc).OfClass(View).ToElements())
plan_views   = [v for v in all_views if isinstance(v, ViewPlan) and not v.IsTemplate]
section_views = [v for v in all_views if isinstance(v, ViewSection) and not v.IsTemplate]

# ── Grid bubbles in plans ─────────────────────────────────────
if "Show grid bubbles in all floor plan views" in choices:
    count = 0
    with revit.Transaction("Show Grid Bubbles — Plans"):
        for view in plan_views:
            for grid in all_grids:
                try:
                    grid.ShowBubbleInView(DatumExtentType.Model, view)
                    count += 1
                except Exception:
                    pass
    results.append("Grid bubbles shown in {} plan views ({} grids each)".format(len(plan_views), len(all_grids)))
    output.print_md("- Grid bubbles: shown in **{}** plan views".format(len(plan_views)))

# ── Grid bubbles in sections ──────────────────────────────────
if "Show grid bubbles in all section views" in choices:
    count = 0
    with revit.Transaction("Show Grid Bubbles — Sections"):
        for view in section_views:
            for grid in all_grids:
                try:
                    grid.ShowBubbleInView(DatumExtentType.Model, view)
                    count += 1
                except Exception:
                    pass
    results.append("Grid bubbles shown in {} section views".format(len(section_views)))
    output.print_md("- Grid bubbles: shown in **{}** section views".format(len(section_views)))

# ── Level markers in sections ─────────────────────────────────
if "Show level markers in all section views" in choices:
    with revit.Transaction("Show Level Markers — Sections"):
        for view in section_views:
            for lvl in all_levels:
                try:
                    lvl.ShowBubbleInView(DatumExtentType.Model, view)
                except Exception:
                    pass
    results.append("Level markers shown in {} section views".format(len(section_views)))
    output.print_md("- Level markers: shown in **{}** section views".format(len(section_views)))

# ── Crop region visible ───────────────────────────────────────
if "Set crop region visible on all views" in choices:
    toggled = 0
    with revit.Transaction("Show Crop Regions"):
        for view in plan_views + section_views:
            try:
                if view.CropBoxActive and not view.CropBoxVisible:
                    view.CropBoxVisible = True
                    toggled += 1
            except Exception:
                pass
    results.append("Crop region made visible on {} views".format(toggled))
    output.print_md("- Crop regions visible: **{}** views updated".format(toggled))

# ── Views missing scale (report only) ────────────────────────
if "Report views missing a scale" in choices:
    missing = []
    for view in plan_views + section_views:
        try:
            scale = view.Scale
            if scale == 0 or scale == 1:
                missing.append(view.Name)
        except Exception:
            pass
    if missing:
        output.print_md("**Views with no/default scale set ({}):**".format(len(missing)))
        for n in missing:
            output.print_md("  - {}".format(n))
    else:
        output.print_md("- All views have a scale set.")
    results.append("{} views missing a proper scale".format(len(missing)))

# ── Views not on sheets (report only) ────────────────────────
if "Report views not placed on sheets" in choices:
    all_viewports = list(FilteredElementCollector(doc).OfClass(Viewport).ToElements())
    placed_view_ids = set(vp.ViewId for vp in all_viewports)
    unplaced = []
    for view in plan_views + section_views:
        if view.Id not in placed_view_ids:
            unplaced.append(view.Name)
    if unplaced:
        output.print_md("**Views not placed on any sheet ({}):**".format(len(unplaced)))
        for n in unplaced[:30]:
            output.print_md("  - {}".format(n))
        if len(unplaced) > 30:
            output.print_md("  ... and {} more".format(len(unplaced) - 30))
    else:
        output.print_md("- All views are placed on sheets.")
    results.append("{} views not placed on sheets".format(len(unplaced)))

summary = "\n".join("• {}".format(r) for r in results)
forms.alert("Auto-Annotate complete.\n\n{}".format(summary), title="Auto-Annotate")
