# -*- coding: utf-8 -*-
__title__ = "Auto\nTag"
__doc__ = "Automatically place room tags, door marks, window marks, and level tags across selected views."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, ViewPlan, ViewSection,
    IndependentTag, TagMode, TagOrientation,
    BuiltInCategory, ElementId, XYZ, Reference,
    SpatialElement, FamilyInstance, Level, UV
)
from Autodesk.Revit.DB.Architecture import Room

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

active_view = uidoc.ActiveView

# ── Confirm view type ─────────────────────────────────────────
if not isinstance(active_view, (ViewPlan, ViewSection)):
    forms.alert(
        "Auto-Tag works on Floor Plan or Section views.\n"
        "Switch to a plan or section view and try again.",
        title="Wrong View Type"
    )
    script.exit()

# ── Ask what to tag ───────────────────────────────────────────
tag_choices = forms.SelectFromList.show(
    ["Rooms", "Doors", "Windows", "Walls", "Furniture"],
    title="Auto-Tag — Select Categories",
    multiselect=True,
    button_name="Tag Selected"
)
if not tag_choices:
    script.exit()

output.print_md("# Auto-Tag")
output.print_md("**View:** {}  |  **Tagging:** {}".format(active_view.Name, ", ".join(tag_choices)))

tag_counts = {}


def _get_tag_type(category_id):
    """Find the first loaded tag family type for a given category."""
    try:
        tags = FilteredElementCollector(doc).OfClass(FamilyInstance).ToElements()
        # Get family symbols for tags
        from Autodesk.Revit.DB import FamilySymbol
        symbols = FilteredElementCollector(doc).OfClass(FamilySymbol).ToElements()
        for sym in symbols:
            try:
                fam = sym.Family
                if fam and fam.IsTagFamily:
                    if sym.Category and sym.Category.Id == ElementId(category_id):
                        if not sym.IsActive:
                            with revit.Transaction("Activate tag"):
                                sym.Activate()
                        return sym.Id
            except Exception:
                pass
    except Exception:
        pass
    return None


def tag_rooms():
    rooms = list(
        FilteredElementCollector(doc, active_view.Id)
        .OfCategory(BuiltInCategory.OST_Rooms)
        .ToElements()
    )
    count = 0
    with revit.Transaction("Auto-Tag Rooms"):
        for room in rooms:
            try:
                loc = room.Location
                if not loc:
                    continue
                pt = loc.Point
                ref = Reference(room)
                tag = IndependentTag.Create(
                    doc, active_view.Id, ref, False,
                    TagMode.TM_ADDBY_CATEGORY,
                    TagOrientation.Horizontal,
                    pt
                )
                count += 1
            except Exception:
                pass
    return count


def tag_category(bic, label):
    elements = list(
        FilteredElementCollector(doc, active_view.Id)
        .OfCategory(bic)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    count = 0
    with revit.Transaction("Auto-Tag {}".format(label)):
        for elem in elements:
            try:
                loc = elem.Location
                if hasattr(loc, "Point"):
                    pt = loc.Point
                elif hasattr(loc, "Curve"):
                    curve = loc.Curve
                    pt = curve.Evaluate(0.5, True)
                else:
                    continue
                ref = Reference(elem)
                IndependentTag.Create(
                    doc, active_view.Id, ref, False,
                    TagMode.TM_ADDBY_CATEGORY,
                    TagOrientation.Horizontal,
                    pt
                )
                count += 1
            except Exception:
                pass
    return count


cat_map = {
    "Rooms":     (None, tag_rooms),
    "Doors":     (BuiltInCategory.OST_Doors,     None),
    "Windows":   (BuiltInCategory.OST_Windows,   None),
    "Walls":     (BuiltInCategory.OST_Walls,     None),
    "Furniture": (BuiltInCategory.OST_Furniture, None),
}

total = 0
for choice in tag_choices:
    try:
        bic, fn = cat_map.get(choice, (None, None))
        if fn:
            n = fn()
        elif bic:
            n = tag_category(bic, choice)
        else:
            n = 0
        tag_counts[choice] = n
        total += n
        output.print_md("- **{}**: {} tags placed".format(choice, n))
    except Exception as e:
        output.print_md("- **{}**: error — {}".format(choice, str(e)))

summary = "\n".join("{}: {}".format(k, v) for k, v in tag_counts.items())
forms.alert(
    "Auto-Tag complete.\n\nTotal tags placed: {}\n\n{}".format(total, summary),
    title="Auto-Tag"
)
