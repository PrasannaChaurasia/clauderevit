# -*- coding: utf-8 -*-
__title__ = "Structural\nAudit"
__doc__ = "Structural drawing audit: column grid consistency, beam sizing, slab thickness, structural parameters, coordination with architecture, and code compliance."

import sys, os, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, Grid, Wall, Floor,
    ViewSheet, BuiltInCategory, BuiltInParameter, ElementId,
    FamilyInstance, Structure
)
from claude_client import ask_claude

doc    = revit.doc
output = script.get_output()

region = forms.CommandSwitchWindow.show(
    ["UK (Eurocode + UK NA)", "EU (Eurocode)", "US (AISC / ACI / IBC)", "International"],
    message="Select the structural code standard:"
)
if not region:
    script.exit()

output.print_md("# Structural Audit  —  {}".format(doc.Title))
output.print_md("**Standard:** {}".format(region))
output.print_md("Collecting structural data...")

data = {}

# ── Levels ────────────────────────────────────────────────────
levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
levels.sort(key=lambda l: l.Elevation)
level_data = []
for i, l in enumerate(levels):
    storey_h = None
    if i > 0:
        storey_h = round((l.Elevation - levels[i-1].Elevation) * 0.3048, 3)
    level_data.append({"name": l.Name, "elev_m": round(l.Elevation * 0.3048, 3), "storey_height_m": storey_h})
data["levels"] = level_data

# ── Grids ─────────────────────────────────────────────────────
grids = list(FilteredElementCollector(doc).OfClass(Grid).ToElements())
grid_names = [g.Name for g in grids]
data["grid_count"] = len(grids)
data["grid_names"] = grid_names[:30]

# Detect grid naming convention
alpha = [n for n in grid_names if n and n[0].isalpha()]
numeric = [n for n in grid_names if n and n[0].isdigit()]
data["grid_alpha_count"]   = len(alpha)
data["grid_numeric_count"] = len(numeric)

# ── Structural columns ────────────────────────────────────────
columns = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_StructuralColumns)
    .WhereElementIsNotElementType()
    .ToElements()
)
col_data = []
for c in columns[:60]:
    try:
        sym = c.Symbol
        col_data.append({
            "type": sym.FamilyName + " : " + sym.Name,
            "level": c.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM).AsValueString()
                     if c.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM) else "?"
        })
    except Exception:
        pass
data["column_count"] = len(columns)
data["columns_sample"] = col_data

# ── Structural framing (beams) ────────────────────────────────
beams = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_StructuralFraming)
    .WhereElementIsNotElementType()
    .ToElements()
)
beam_data = []
for b in beams[:60]:
    try:
        sym = b.Symbol
        lp  = b.get_Parameter(BuiltInParameter.STRUCTURAL_FRAME_SECTION_SHAPE_ID)
        beam_data.append({
            "type":  sym.FamilyName + " : " + sym.Name,
            "length_m": round(b.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH).AsDouble() * 0.3048, 2)
                        if b.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH) else 0
        })
    except Exception:
        pass
data["beam_count"]   = len(beams)
data["beams_sample"] = beam_data

# ── Structural walls ──────────────────────────────────────────
all_walls = list(FilteredElementCollector(doc).OfClass(Wall).ToElements())
struct_walls = []
for w in all_walls:
    try:
        p = w.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_USAGE_TEXT_PARAM)
        if p and p.AsValueString() not in ["Non-bearing", ""]:
            lp = w.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
            struct_walls.append({
                "type": w.WallType.Name,
                "length_m": round(lp.AsDouble() * 0.3048, 2) if lp else 0,
                "structural_usage": p.AsValueString()
            })
    except Exception:
        pass
data["structural_wall_count"]   = len(struct_walls)
data["structural_walls_sample"] = struct_walls[:30]

# ── Floors ────────────────────────────────────────────────────
floors = list(FilteredElementCollector(doc).OfClass(Floor).ToElements())
floor_data = []
for f in floors[:40]:
    try:
        area = f.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
        floor_data.append({
            "type": f.FloorType.Name,
            "area_sqm": round(area.AsDouble() * 0.0929, 2) if area else 0
        })
    except Exception:
        pass
data["floor_count"]   = len(floors)
data["floors_sample"] = floor_data

# ── Structural sheets ─────────────────────────────────────────
sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
struct_sheets = [s for s in sheets if any(k in s.Name.upper() for k in
                ["STRUCT", "FOUND", "FRAME", "SLAB", "BEAM", "COLUMN", "S-", "SE-"])]
data["total_sheet_count"]    = len(sheets)
data["structural_sheet_count"] = len(struct_sheets)
data["structural_sheet_names"] = [s.Name for s in struct_sheets]

# ── Parameter completeness ────────────────────────────────────
beams_without_mark = sum(1 for b in beams if not b.LookupParameter("Mark") or
                         not b.LookupParameter("Mark").AsString())
cols_without_mark  = sum(1 for c in columns if not c.LookupParameter("Mark") or
                         not c.LookupParameter("Mark").AsString())
data["beams_without_mark"]   = beams_without_mark
data["columns_without_mark"] = cols_without_mark

output.print_md("Data collected. Running Claude structural audit...")

SYSTEM = """\
You are a senior Structural BIM Coordinator and structural engineer specialising in {standard}.

Analyse this Revit model's structural data and produce a STRUCTURAL AUDIT REPORT:

## 1. Structural Overview
Element counts, structural system type assessment, RAG rating, summary.

## 2. Grid System Audit
- Grid count, naming convention (alpha/numeric — standard: alpha for Y, numeric for X)
- Flag inconsistent naming, missing grids, unusual spacing
- Assess structural bay sizes if inferable

## 3. Column Audit
- Column types and distribution
- Columns missing Mark parameter
- Column type variety (flag if too many different types — indicates rationalisation needed)
- Assess grid alignment (flag if column count doesn't match expected grid intersections)

## 4. Beam / Structural Framing Audit
- Beam types, size ranges, length ranges
- Beams missing Mark parameter
- Beam type rationalisation assessment
- Span-to-depth ratios if inferable (typical steel beam: span/20, concrete: span/25)

## 5. Floor / Slab Audit
- Floor types and areas
- Missing floor levels
- Slab type consistency

## 6. Structural Wall Audit
- Structural wall count and types
- Verify structural walls have correct structural usage parameter

## 7. Structural Drawing Completeness
- Structural sheet count vs. expected (foundation plan, structural plans per floor, roof plan, details)
- Flag if no structural sheets exist

## 8. Code Compliance ({standard})
Reference actual regulation numbers. Flag:
- Storey heights outside normal range (UK: 2.4m–4.5m typical)
- Missing structural parameters required for calculations
- Coordination flags between structural and architectural levels

## 9. Priority Actions
Numbered, severity [CRITICAL/WARNING/INFO].

Be specific. Reference actual type names and counts from the data.
""".format(standard=region)

prompt = "Audit this Revit structural model:\n\n{}".format(json.dumps(data, indent=2))

try:
    report = ask_claude(prompt, system=SYSTEM, max_tokens=2500)
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("---")
output.print_md(report)
output.print_md("---")
output.print_md("*Grids: {} | Columns: {} | Beams: {} | Struct Walls: {} | Floors: {}*".format(
    len(grids), len(columns), len(beams), len(struct_walls), len(floors)))

forms.alert(
    "Structural Audit complete.\nFull report in output window.\n\n"
    "Columns: {}  Beams: {}  Grids: {}".format(len(columns), len(beams), len(grids)),
    title="Structural Audit"
)
