# -*- coding: utf-8 -*-
__title__ = "Sheet\nTemplate"
__doc__ = "Create professional drawing sheets with title blocks, auto-placed views, project information, and structured layout. Generates single or multiple sheets from a template."

import sys, os, clr, json

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (Thickness, HorizontalAlignment, VerticalAlignment,
                             FontWeights, TextWrapping, WindowStartupLocation, ResizeMode)
from System.Windows import CornerRadius
from System.Windows.Controls import (Grid, StackPanel, Border, TextBlock, TextBox,
                                      Button, ComboBox, ComboBoxItem, CheckBox,
                                      ScrollBarVisibility, Orientation, ScrollViewer,
                                      Label)
from System.Windows.Input import Keyboard, Key, ModifierKeys
from wpf_helper import (base_window, title_bar, add_row, add_col, place,
                         label as wlabel, textbox, button, divider, pill,
                         GOLD, BG_MID, BG_CARD, BG_INP, BG_DARK,
                         FG_PRI, FG_SEC, FG_DIM, BORDER, rgb)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, FamilySymbol, Family,
    ViewSheet, Viewport, ViewPlan, ViewSection, View3D,
    ViewFamily, ViewFamilyType, Level, ElementId,
    BuiltInParameter, BuiltInCategory, XYZ, BoundingBoxUV, UV,
    Transaction
)
from claude_client import ask_claude

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ── Collect available title blocks ────────────────────────────
tb_symbols = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_TitleBlocks)
    .WhereElementIsElementType()
    .ToElements()
)
tb_names = [t.get_Parameter(BuiltInParameter.SYMBOL_FAMILY_AND_TYPE_NAMES_PARAM).AsString()
            if t.get_Parameter(BuiltInParameter.SYMBOL_FAMILY_AND_TYPE_NAMES_PARAM)
            else t.FamilyName for t in tb_symbols]

if not tb_symbols:
    forms.alert(
        "No title block families loaded in this project.\n\n"
        "Load a title block family first via Insert → Load Family.",
        title="Sheet Template"
    )
    script.exit()

# ── Collect unplaced views ─────────────────────────────────────
all_views = list(FilteredElementCollector(doc).OfClass(View).ToElements())
all_viewports = list(FilteredElementCollector(doc).OfClass(Viewport).ToElements())
placed_ids = set(vp.ViewId for vp in all_viewports)

unplaced = [v for v in all_views
            if not v.IsTemplate
            and v.Id not in placed_ids
            and isinstance(v, (ViewPlan, ViewSection, View3D))]
unplaced.sort(key=lambda v: v.Name)
unplaced_names = [v.Name for v in unplaced]


def show_sheet_dialog():
    """Return dict of sheet parameters or None."""
    result = [None]

    win = base_window("Sheet Template Creator", doc.Title, width=760, height=680)

    outer = Grid()
    add_row(outer, 44)
    add_row(outer, 1)
    add_row(outer, 1, True)
    add_row(outer, 1)
    add_row(outer, 52)

    place(outer, title_bar(doc.Title, "Sheet Template Creator"), 0)
    div1 = Border(); div1.Background = BORDER; div1.Height = 1
    place(outer, div1, 1)

    # Form body
    sv = ScrollViewer()
    sv.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
    sv.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
    sv.Margin = Thickness(24, 16, 24, 8)

    form = StackPanel()
    form.Orientation = Orientation.Vertical

    def section_header(txt):
        t = TextBlock()
        t.Text       = txt
        t.Foreground = GOLD
        t.FontSize   = 12
        t.FontWeight = FontWeights.SemiBold
        t.Margin     = Thickness(0, 14, 0, 6)
        return t

    def field_label(txt):
        t = TextBlock()
        t.Text       = txt
        t.Foreground = FG_SEC
        t.FontSize   = 11
        t.Margin     = Thickness(0, 0, 0, 3)
        return t

    def input_box(default="", height=32):
        tb = TextBox()
        tb.Text       = default
        tb.Height     = height
        tb.FontSize   = 12
        tb.Background = BG_INP
        tb.Foreground = FG_PRI
        tb.CaretBrush = GOLD
        tb.BorderBrush = BORDER
        tb.BorderThickness = Thickness(1)
        tb.Padding    = Thickness(8, 4, 8, 4)
        tb.Margin     = Thickness(0, 0, 0, 8)
        return tb

    # ── Project info ──────────────────────────────────────────
    form.Children.Add(section_header("PROJECT INFORMATION"))

    form.Children.Add(field_label("Project Name"))
    tb_proj = input_box(doc.Title)
    form.Children.Add(tb_proj)

    form.Children.Add(field_label("Project Number"))
    tb_number = input_box("")
    form.Children.Add(tb_number)

    form.Children.Add(field_label("Client Name"))
    tb_client = input_box("")
    form.Children.Add(tb_client)

    form.Children.Add(field_label("Drawn By"))
    tb_drawn = input_box("PRC")
    form.Children.Add(tb_drawn)

    form.Children.Add(field_label("Checked By"))
    tb_checked = input_box("")
    form.Children.Add(tb_checked)

    # ── Sheet setup ───────────────────────────────────────────
    form.Children.Add(divider())
    form.Children.Add(section_header("SHEET SETUP"))

    form.Children.Add(field_label("Starting Sheet Number (e.g. A101)"))
    tb_sheet_num = input_box("A101")
    form.Children.Add(tb_sheet_num)

    form.Children.Add(field_label("Number of Sheets to Create"))
    tb_count = input_box("1")
    form.Children.Add(tb_count)

    form.Children.Add(field_label("Title Block"))
    cb_tb = ComboBox()
    cb_tb.Height = 32
    cb_tb.FontSize = 12
    cb_tb.Margin = Thickness(0, 0, 0, 8)
    for name in tb_names:
        item = ComboBoxItem()
        item.Content = name
        cb_tb.Items.Add(item)
    cb_tb.SelectedIndex = 0
    form.Children.Add(cb_tb)

    # ── View placement ────────────────────────────────────────
    form.Children.Add(divider())
    form.Children.Add(section_header("VIEW PLACEMENT"))

    chk_auto = CheckBox()
    chk_auto.Content   = "  Auto-place one view per sheet (from unplaced views)"
    chk_auto.Foreground = FG_PRI
    chk_auto.FontSize  = 12
    chk_auto.IsChecked = True
    chk_auto.Margin    = Thickness(0, 0, 0, 8)
    form.Children.Add(chk_auto)

    form.Children.Add(field_label("Sheet Name Pattern (e.g. 'Ground Floor Plan')"))
    tb_sheet_name = input_box("Drawing Sheet")
    form.Children.Add(tb_sheet_name)

    sv.Content = form
    place(outer, sv, 2)

    div2 = Border(); div2.Background = BORDER; div2.Height = 1
    place(outer, div2, 3)

    # Bottom
    bottom = Grid()
    bottom.Background = BG_MID
    bottom.Margin = Thickness(24, 10, 24, 10)
    add_col(bottom, 1, True)
    add_col(bottom, 160)
    add_col(bottom, 8)
    add_col(bottom, 120)

    btn_create = button("Create Sheets", gold=True, width=150, height=34)
    place(bottom, btn_create, 0, 1)

    btn_cancel = button("Cancel", gold=False, width=110, height=34)
    place(bottom, btn_cancel, 0, 3)

    place(outer, bottom, 4)

    def on_create(s, e):
        try:
            count = int(tb_count.Text.strip()) if tb_count.Text.strip() else 1
        except Exception:
            count = 1
        result[0] = {
            "project_name":  tb_proj.Text.strip(),
            "project_number": tb_number.Text.strip(),
            "client":        tb_client.Text.strip(),
            "drawn_by":      tb_drawn.Text.strip(),
            "checked_by":    tb_checked.Text.strip(),
            "start_number":  tb_sheet_num.Text.strip(),
            "count":         max(1, count),
            "tb_index":      cb_tb.SelectedIndex,
            "auto_view":     chk_auto.IsChecked,
            "sheet_name":    tb_sheet_name.Text.strip(),
        }
        win.Close()

    def on_cancel(s, e):
        win.Close()

    btn_create.Click += on_create
    btn_cancel.Click += on_cancel
    win.Loaded += lambda s, e: (tb_proj.Focus(), Keyboard.Focus(tb_proj))
    win.Content = outer
    win.ShowDialog()
    return result[0]


params = show_sheet_dialog()
if not params:
    script.exit()

output.print_md("# Sheet Template Creator")

tb_id  = tb_symbols[params["tb_index"]].Id
count  = params["count"]
start  = params["start_number"]
name_t = params["sheet_name"]

# Generate sheet numbers: A101, A102, ...
def next_sheet_num(base, offset):
    prefix = ""
    num_str = ""
    for ch in base:
        if ch.isdigit():
            num_str += ch
        else:
            prefix += ch
    if num_str:
        return "{}{}".format(prefix, str(int(num_str) + offset).zfill(len(num_str)))
    return "{}-{}".format(base, offset + 1)


created_sheets = []

with revit.Transaction("Create Sheets"):
    for i in range(count):
        try:
            sheet = ViewSheet.Create(doc, tb_id)
            sheet_num = next_sheet_num(start, i)
            sheet.SheetNumber = sheet_num
            sheet.Name = "{} {}".format(name_t, i + 1) if count > 1 else name_t

            # Set titleblock parameters
            def _set_param(elem, param_name, value):
                p = elem.LookupParameter(param_name)
                if p and not p.IsReadOnly:
                    try:
                        p.Set(value)
                    except Exception:
                        pass

            _set_param(sheet, "Drawn By",      params["drawn_by"])
            _set_param(sheet, "Checked By",    params["checked_by"])
            _set_param(sheet, "Project Name",  params["project_name"])
            _set_param(sheet, "Project Number", params["project_number"])
            _set_param(sheet, "Client",        params["client"])

            created_sheets.append(sheet)
            output.print_md("  Created: **{}** — {}".format(sheet_num, sheet.Name))

        except Exception as ex:
            output.print_md("  Error creating sheet {}: {}".format(i, str(ex)))

# ── Auto-place views ───────────────────────────────────────────
if params["auto_view"] and unplaced and created_sheets:
    with revit.Transaction("Place Views on Sheets"):
        for i, sheet in enumerate(created_sheets):
            if i >= len(unplaced):
                break
            view = unplaced[i]
            try:
                # Place at sheet centre
                outline = sheet.Outline
                cx = (outline.Min.U + outline.Max.U) / 2.0
                cy = (outline.Min.V + outline.Max.V) / 2.0
                Viewport.Create(doc, sheet.Id, view.Id, XYZ(cx, cy, 0))
                output.print_md("  Placed **{}** on sheet {}".format(view.Name, sheet.SheetNumber))
            except Exception as ex:
                output.print_md("  Could not place view '{}': {}".format(view.Name, str(ex)))

forms.alert(
    "Sheet Template complete.\n\n"
    "Created {} sheet(s) starting at {}.\n"
    "Check the Project Browser — Sheets.".format(len(created_sheets), start),
    title="Sheet Template"
)
