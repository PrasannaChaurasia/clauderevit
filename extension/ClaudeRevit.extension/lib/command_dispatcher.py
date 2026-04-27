# -*- coding: utf-8 -*-
"""
command_dispatcher.py
Executes Claude commands inside the Revit API context.
Called by the ExternalEventHandler — always runs inside a valid Revit API context.
All units: Revit internal = decimal feet. mm() converts mm to feet.
"""

import json
import os
import traceback

from Autodesk.Revit.DB import (
    Transaction, Level, Wall, WallType, Floor, FloorType,
    ViewPlan, View3D, ViewSheet, ViewFamilyType, ViewFamily,
    ViewSchedule, ScheduleSortGroupField, ScheduleSortOrder,
    FilteredElementCollector, XYZ, Line, UV,
    BuiltInCategory, BuiltInParameter, ElementId,
    CurveArray, CurveLoop, ElevationMarker
)
from Autodesk.Revit.DB.Architecture import Room

BRIDGE_CMD    = r"C:\tools\revit-bridge\command.json"
BRIDGE_RESULT = r"C:\tools\revit-bridge\result.json"


def ft(mm_val):
    """Convert millimetres to decimal feet."""
    return float(mm_val) / 304.8


def get_level(doc, name):
    """Get level by name, or first level if name not found."""
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    match = next((l for l in levels if l.Name == name), None)
    return match or (levels[0] if levels else None)


def get_wall_type(doc, name_hint=""):
    """Get wall type by partial name match, or first available."""
    types = list(FilteredElementCollector(doc).OfClass(WallType).ToElements())
    if name_hint:
        match = next((wt for wt in types if name_hint.lower() in wt.Name.lower()), None)
        if match:
            return match
    return types[0] if types else None


def dispatch(doc, data):
    """
    Main dispatcher. Routes command to the correct handler.
    Returns a result dict that gets written to result.json.
    """
    action = data.get("action", "")

    handlers = {
        "create_levels":    cmd_create_levels,
        "create_walls":     cmd_create_walls,
        "create_room":      cmd_create_room,
        "create_floor":     cmd_create_floor,
        "create_sheets":    cmd_create_sheets,
        "create_views":     cmd_create_views,
        "create_schedule":  cmd_create_schedule,
        "set_parameter":    cmd_set_parameter,
        "delete_elements":  cmd_delete_elements,
        "get_model_info":   cmd_get_model_info,
        "get_elements":     cmd_get_elements,
        "get_sheets":       cmd_get_sheets,
        "get_rooms":        cmd_get_rooms,
        "get_levels":       cmd_get_levels,
        "exec_python":      cmd_exec_python,
    }

    handler = handlers.get(action)
    if not handler:
        return {"status": "error", "message": "Unknown action: {}".format(action)}

    try:
        result = handler(doc, data)
        result["action"] = action
        return result
    except Exception:
        return {
            "action": action,
            "status": "error",
            "message": traceback.format_exc()
        }


# ─────────────────────────────────────────────
# READ COMMANDS (no transaction needed)
# ─────────────────────────────────────────────

def cmd_get_model_info(doc, data):
    walls   = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    floors  = FilteredElementCollector(doc).OfClass(Floor).GetElementCount()
    sheets  = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels  = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    rooms   = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).GetElementCount()
    return {
        "status": "ok",
        "model": doc.Title,
        "walls": walls, "floors": floors, "sheets": sheets, "rooms": rooms,
        "levels": [{"name": l.Name, "elevation_mm": round(l.Elevation * 304.8, 1)} for l in levels]
    }

def cmd_get_levels(doc, data):
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    return {
        "status": "ok",
        "levels": [{"id": str(l.Id), "name": l.Name, "elevation_mm": round(l.Elevation * 304.8, 1)} for l in levels]
    }

def cmd_get_sheets(doc, data):
    sheets = list(FilteredElementCollector(doc).OfClass(ViewSheet).ToElements())
    return {
        "status": "ok",
        "count": len(sheets),
        "sheets": [{"number": s.SheetNumber, "name": s.Name} for s in sheets]
    }

def cmd_get_rooms(doc, data):
    rooms = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).ToElements())
    result = []
    for r in rooms:
        try:
            area_p = r.get_Parameter(BuiltInParameter.ROOM_AREA)
            result.append({
                "id": str(r.Id),
                "name": r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(),
                "number": r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString(),
                "area_sqm": round(area_p.AsDouble() * 0.0929, 2) if area_p else 0
            })
        except:
            pass
    return {"status": "ok", "count": len(result), "rooms": result}

def cmd_get_elements(doc, data):
    cat_name = data.get("category", "Walls")
    cat_map = {
        "Walls": BuiltInCategory.OST_Walls,
        "Floors": BuiltInCategory.OST_Floors,
        "Doors": BuiltInCategory.OST_Doors,
        "Windows": BuiltInCategory.OST_Windows,
        "Rooms": BuiltInCategory.OST_Rooms,
        "Furniture": BuiltInCategory.OST_Furniture,
    }
    cat = cat_map.get(cat_name, BuiltInCategory.OST_Walls)
    elems = list(FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType().ToElements())
    return {"status": "ok", "category": cat_name, "count": len(elems)}


# ─────────────────────────────────────────────
# WRITE COMMANDS (require Transaction)
# ─────────────────────────────────────────────

def cmd_create_levels(doc, data):
    """
    data: { "levels": [{"name": "Level 1", "elevation_mm": 3500}, ...] }
    """
    levels_in = data.get("levels", [])
    created = []
    with Transaction(doc, "Claude — Create Levels") as t:
        t.Start()
        for l in levels_in:
            elev_ft = ft(l.get("elevation_mm", 0))
            lvl = Level.Create(doc, elev_ft)
            lvl.Name = l.get("name", "Level {}".format(len(created) + 1))
            created.append(lvl.Name)
        t.Commit()
    return {"status": "ok", "created": created}


def cmd_create_walls(doc, data):
    """
    data: {
        "level": "Level 0",
        "wall_type": "Generic - 200mm",
        "height_mm": 3000,
        "walls": [ {"x1":0,"y1":0,"x2":6000,"y2":0}, ... ]  (mm coords)
    }
    """
    lvl = get_level(doc, data.get("level", "Level 0"))
    wt  = get_wall_type(doc, data.get("wall_type", ""))
    if not lvl or not wt:
        return {"status": "error", "message": "Level or wall type not found"}

    height_ft = ft(data.get("height_mm", 3000))
    walls_in  = data.get("walls", [])
    created = 0

    with Transaction(doc, "Claude — Create Walls") as t:
        t.Start()
        for w in walls_in:
            p1   = XYZ(ft(w["x1"]), ft(w["y1"]), 0)
            p2   = XYZ(ft(w["x2"]), ft(w["y2"]), 0)
            line = Line.CreateBound(p1, p2)
            Wall.Create(doc, line, wt.Id, lvl.Id, height_ft, 0.0, False, False)
            created += 1
        t.Commit()
    return {"status": "ok", "walls_created": created}


def cmd_create_room(doc, data):
    """
    data: { "level": "Level 0", "name": "Living Room", "number": "GF-01",
            "x_mm": 3000, "y_mm": 3000 }
    """
    lvl = get_level(doc, data.get("level", "Level 0"))
    if not lvl:
        return {"status": "error", "message": "Level not found"}

    with Transaction(doc, "Claude — Create Room") as t:
        t.Start()
        uv   = UV(ft(data.get("x_mm", 3000)), ft(data.get("y_mm", 3000)))
        room = doc.Create.NewRoom(lvl, uv)
        room.get_Parameter(BuiltInParameter.ROOM_NAME).Set(data.get("name", "Room"))
        room.get_Parameter(BuiltInParameter.ROOM_NUMBER).Set(data.get("number", "01"))
        t.Commit()
    return {"status": "ok", "room": data.get("name"), "id": str(room.Id)}


def cmd_create_sheets(doc, data):
    """
    data: { "sheets": [{"number":"A100","name":"Ground Floor Plan"}, ...] }
    """
    sheets_in = data.get("sheets", [])
    tbs = list(FilteredElementCollector(doc)
               .OfCategory(BuiltInCategory.OST_TitleBlocks)
               .WhereElementIsElementType().ToElements())
    if not tbs:
        return {"status": "error", "message": "No title blocks in project"}

    tb_id = tbs[0].Id
    created = []

    with Transaction(doc, "Claude — Create Sheets") as t:
        t.Start()
        for s in sheets_in:
            try:
                sheet = ViewSheet.Create(doc, tb_id)
                sheet.SheetNumber = s["number"]
                sheet.Name = s["name"]
                created.append(s["number"])
            except Exception as e:
                created.append("FAIL {}: {}".format(s.get("number","?"), str(e)))
        t.Commit()
    return {"status": "ok", "created": created}


def cmd_create_views(doc, data):
    """
    data: { "views": [{"type":"FloorPlan","level":"Level 0","name":"Ground Floor Plan"}, ...] }
    view types: FloorPlan, CeilingPlan, ThreeD, Elevation
    """
    views_in = data.get("views", [])
    created  = []

    vfts = list(FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements())

    def get_vft(family):
        return next((v for v in vfts if v.ViewFamily == family), None)

    with Transaction(doc, "Claude — Create Views") as t:
        t.Start()
        for v in views_in:
            vtype = v.get("type", "FloorPlan")
            try:
                if vtype == "FloorPlan":
                    vft = get_vft(ViewFamily.FloorPlan)
                    lvl = get_level(doc, v.get("level", "Level 0"))
                    view = ViewPlan.Create(doc, vft.Id, lvl.Id)
                    view.Name = v.get("name", "Floor Plan")
                elif vtype == "CeilingPlan":
                    vft = get_vft(ViewFamily.CeilingPlan)
                    lvl = get_level(doc, v.get("level", "Level 0"))
                    view = ViewPlan.Create(doc, vft.Id, lvl.Id)
                    view.Name = v.get("name", "Ceiling Plan")
                elif vtype == "ThreeD":
                    vft = get_vft(ViewFamily.ThreeDimensional)
                    view = View3D.CreateIsometric(doc, vft.Id)
                    view.Name = v.get("name", "3D View")
                else:
                    continue
                created.append(view.Name)
            except Exception as e:
                created.append("FAIL {}: {}".format(v.get("name","?"), str(e)))
        t.Commit()
    return {"status": "ok", "created": created}


def cmd_create_schedule(doc, data):
    """
    data: { "category": "Walls", "name": "Wall Schedule",
            "fields": ["Type Name", "Length", "Area"] }
    """
    cat_map = {
        "Walls":   BuiltInCategory.OST_Walls,
        "Rooms":   BuiltInCategory.OST_Rooms,
        "Doors":   BuiltInCategory.OST_Doors,
        "Windows": BuiltInCategory.OST_Windows,
        "Floors":  BuiltInCategory.OST_Floors,
        "Sheets":  BuiltInCategory.OST_Sheets,
    }
    cat_name   = data.get("category", "Walls")
    cat        = cat_map.get(cat_name, BuiltInCategory.OST_Walls)
    field_names = data.get("fields", ["Type Name", "Length"])

    with Transaction(doc, "Claude — Create Schedule") as t:
        t.Start()
        sched = ViewSchedule.CreateSchedule(doc, ElementId(cat))
        sched.Name = data.get("name", "{} Schedule".format(cat_name))
        defn = sched.Definition
        for sf in defn.GetSchedulableFields():
            if sf.GetName(doc) in field_names:
                try:
                    defn.AddField(sf)
                except:
                    pass
        t.Commit()
    return {"status": "ok", "schedule": sched.Name}


def cmd_set_parameter(doc, data):
    """
    data: { "element_id": 12345, "parameter": "Mark", "value": "W-01" }
    """
    elem_id = ElementId(int(data["element_id"]))
    elem    = doc.GetElement(elem_id)
    if not elem:
        return {"status": "error", "message": "Element not found"}

    param = elem.LookupParameter(data["parameter"])
    if not param:
        return {"status": "error", "message": "Parameter not found: {}".format(data["parameter"])}

    with Transaction(doc, "Claude — Set Parameter") as t:
        t.Start()
        if param.StorageType.ToString() == "String":
            param.Set(str(data["value"]))
        elif param.StorageType.ToString() == "Double":
            param.Set(float(data["value"]))
        elif param.StorageType.ToString() == "Integer":
            param.Set(int(data["value"]))
        t.Commit()
    return {"status": "ok", "set": data["parameter"], "value": data["value"]}


def cmd_delete_elements(doc, data):
    """
    data: { "element_ids": [12345, 67890] }
    """
    ids = [ElementId(int(i)) for i in data.get("element_ids", [])]
    with Transaction(doc, "Claude — Delete Elements") as t:
        t.Start()
        doc.Delete(ids)
        t.Commit()
    return {"status": "ok", "deleted": len(ids)}


def cmd_exec_python(doc, data):
    """
    data: { "code": "python string", "description": "what it does" }
    Full escape hatch — execute arbitrary Python inside valid Revit API context.
    """
    code = data.get("code", "")
    desc = data.get("description", "Claude exec")

    from Autodesk.Revit.DB import *
    ctx = {
        "doc": doc,
        "ft": ft,
        "get_level": get_level,
        "get_wall_type": get_wall_type,
        "__builtins__": __builtins__,
        "Transaction": Transaction,
        "Level": Level, "Wall": Wall, "XYZ": XYZ, "Line": Line,
        "UV": UV, "ViewSheet": ViewSheet, "ViewPlan": ViewPlan,
        "FilteredElementCollector": FilteredElementCollector,
        "BuiltInCategory": BuiltInCategory,
        "BuiltInParameter": BuiltInParameter,
        "ElementId": ElementId,
    }
    exec(compile(code, "<claude>", "exec"), ctx)
    return {"status": "ok", "executed": desc}
