# -*- coding: utf-8 -*-
__title__ = "MEP\nAudit"
__doc__ = "MEP drawing audit: mechanical systems, electrical circuits, plumbing connections, spatial coverage, coordination clashes, and code compliance."

import sys, os, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Level, ViewSheet, View,
    BuiltInCategory, BuiltInParameter, ElementId,
    Mechanical, Plumbing, Electrical
)
from claude_client import ask_claude
from wpf_helper import switch_dialog

doc    = revit.doc
output = script.get_output()

region = switch_dialog(
    [
        "UK (CIBSE / BS standards)",
        "EU (EN standards)",
        "US (ASHRAE / NEC / IPC)",
        "Australia / NZ (AS/NZS standards)",
        "Middle East (ASHRAE + local)",
        "International (general best practice)",
    ],
    message="Select the MEP code standard for this audit:",
    title="MEP Audit"
)
if not region:
    script.exit()

output.print_md("# MEP Audit  —  {}".format(doc.Title))
output.print_md("**Standard:** {}".format(region))
output.print_md("Collecting MEP data...")

data = {}

# ── Mechanical elements ───────────────────────────────────────
mech_equipment = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_MechanicalEquipment)
    .WhereElementIsNotElementType()
    .ToElements()
)
air_terminals = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_MechanicalEquipment)
    .WhereElementIsNotElementType()
    .ToElements()
)
ducts = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_DuctCurves)
    .ToElements()
)
duct_data = []
for d in ducts[:60]:
    try:
        lp = d.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
        sys_type = d.LookupParameter("System Type")
        duct_data.append({
            "length_m": round(lp.AsDouble() * 0.3048, 2) if lp else 0,
            "system": sys_type.AsValueString() if sys_type else "Unknown"
        })
    except Exception:
        pass

data["duct_count"]      = len(ducts)
data["ducts_sample"]    = duct_data
data["mech_equip_count"] = len(mech_equipment)

# ── Electrical elements ───────────────────────────────────────
light_fixtures = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_LightingFixtures)
    .WhereElementIsNotElementType()
    .ToElements()
)
electrical_equip = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_ElectricalEquipment)
    .WhereElementIsNotElementType()
    .ToElements()
)
data["light_fixture_count"]    = len(light_fixtures)
data["electrical_equip_count"] = len(electrical_equip)

# ── Plumbing elements ─────────────────────────────────────────
pipes = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_PipeCurves)
    .ToElements()
)
plumbing_fixtures = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_PlumbingFixtures)
    .WhereElementIsNotElementType()
    .ToElements()
)
pipe_data = []
for p in pipes[:60]:
    try:
        lp  = p.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
        dia = p.LookupParameter("Outer Diameter") or p.LookupParameter("Diameter")
        pipe_data.append({
            "length_m": round(lp.AsDouble() * 0.3048, 2) if lp else 0,
            "diameter_mm": round(dia.AsDouble() * 304.8, 1) if dia else 0
        })
    except Exception:
        pass

data["pipe_count"]           = len(pipes)
data["pipes_sample"]         = pipe_data
data["plumbing_fixture_count"] = len(plumbing_fixtures)

# ── Rooms and service coverage ────────────────────────────────
rooms = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Rooms)
    .ToElements()
)
room_summary = []
for r in rooms[:60]:
    try:
        name = r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
        area = r.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble() * 0.0929
        room_summary.append({"name": name or "?", "area_sqm": round(area, 2)})
    except Exception:
        pass

data["room_count"]   = len(rooms)
data["room_summary"] = room_summary

# ── Levels ────────────────────────────────────────────────────
levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
data["levels"] = [{"name": l.Name, "elev_m": round(l.Elevation * 0.3048, 3)} for l in levels]
data["level_count"] = len(levels)

# ── Sheets ────────────────────────────────────────────────────
sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
mep_sheets = [s for s in sheets if any(k in s.Name.upper() for k in
              ["MECH", "ELEC", "PLUMB", "MEP", "HVAC", "SERVICE", "M&E"])]
data["total_sheet_count"] = len(sheets)
data["mep_sheet_count"]   = len(mep_sheets)
data["mep_sheet_names"]   = [s.Name for s in mep_sheets]

output.print_md("Data collected. Running Claude MEP audit...")

SYSTEM = """\
You are a senior MEP BIM Coordinator and building services engineer specialising in {standard}.

Analyse this Revit model's MEP data and produce a STRUCTURED MEP AUDIT REPORT:

## 1. MEP Overview
Element counts, overall MEP completion status (RAG), summary assessment.

## 2. Mechanical (HVAC) Audit
- Duct network extent vs. room count (is every room likely served?)
- Flag rooms with no nearby duct elements
- System types identified
- Equipment count and coverage assessment
- Compliance observations ({standard} ventilation rates)

## 3. Electrical Audit
- Lighting fixture count vs. room count ratio
- Flag rooms likely without lighting
- Electrical equipment/distribution board count
- Missing emergency lighting indicators
- Compliance: {standard} electrical standards

## 4. Plumbing Audit
- Pipe network extent and diameter range
- Plumbing fixtures vs. expected fixture count for room types
- Flag rooms that should have plumbing (bathrooms, kitchens) by name
- Compliance: {standard} plumbing codes

## 5. Coordination & Clash Risk
- Assess spatial clash risk given duct/pipe counts and level layout
- Flag floors with high element density
- Missing MEP sheets for specific disciplines

## 6. Drawing Completeness
- MEP sheet count vs. expected (flag if no mechanical/electrical/plumbing sheets)
- Untagged MEP elements indicators

## 7. Priority Actions
Numbered, severity [CRITICAL/WARNING/INFO]. Reference actual data.

Be specific. Reference actual counts and values from the data.
""".format(standard=region)

prompt = "Audit this Revit MEP model:\n\n{}".format(json.dumps(data, indent=2, ensure_ascii=True))

try:
    report = ask_claude(prompt, system=SYSTEM, max_tokens=2500)
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("---")
output.print_md(report)
output.print_md("---")
output.print_md("*Ducts: {} | Pipes: {} | Lighting: {} | Mech Equip: {} | Plumbing Fixtures: {}*".format(
    len(ducts), len(pipes), len(light_fixtures), len(mech_equipment), len(plumbing_fixtures)))

forms.alert(
    "MEP Audit complete.\nFull report in output window.\n\n"
    "Ducts: {}  Pipes: {}  Lighting fixtures: {}".format(
        len(ducts), len(pipes), len(light_fixtures)),
    title="MEP Audit"
)
