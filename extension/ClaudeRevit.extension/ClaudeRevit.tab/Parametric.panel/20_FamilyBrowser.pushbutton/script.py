# -*- coding: utf-8 -*-
__title__ = "Family\nBrowser"
__doc__ = "Browse, search, and place all loaded families in the model. View family types, instance parameters, and place instances at clicked locations. Supports parametric, adaptive, and standard families."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (Thickness, HorizontalAlignment, VerticalAlignment,
                             FontWeights, TextWrapping, CornerRadius)
from System.Windows.Controls import (Grid, StackPanel, Border, TextBlock, TextBox,
                                      Button, ListBox, ListBoxItem, ScrollViewer,
                                      Orientation, ScrollBarVisibility, Label)
from System.Windows.Input import Keyboard, Key, ModifierKeys
from System.Windows.Media import FontFamily
from wpf_helper import (base_window, title_bar, add_row, add_col, place,
                         label, button, divider, pill,
                         GOLD, BG_MID, BG_CARD, BG_INP, BG_DARK,
                         FG_PRI, FG_SEC, FG_DIM, BORDER, rgb)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import (
    FilteredElementCollector, Family, FamilySymbol, FamilyInstance,
    Level, XYZ, ElementId, BuiltInCategory, BuiltInParameter,
    AdaptiveComponentInstanceUtils, StructuralType
)

doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

# ── Collect all loaded families ───────────────────────────────
all_families = list(FilteredElementCollector(doc).OfClass(Family).ToElements())
all_families.sort(key=lambda f: f.Name)

# Build a rich index: family → [symbols]
fam_index = {}
for fam in all_families:
    sym_ids = fam.GetFamilySymbolIds()
    if sym_ids:
        syms = []
        for sid in sym_ids:
            sym = doc.GetElement(sid)
            if sym:
                syms.append(sym)
        fam_index[fam.Name] = {"family": fam, "symbols": syms, "is_tag": fam.IsTagFamily}

non_tag_families = [name for name, d in fam_index.items() if not d["is_tag"]]
non_tag_families.sort()


def show_browser():
    """Family browser window. Returns (family_name, symbol_name) or (None, None)."""
    sel_fam = [None]
    sel_sym = [None]
    action  = ["place"]

    win = base_window("Family Browser", doc.Title, width=820, height=640)

    outer = Grid()
    add_row(outer, 44)       # titlebar
    add_row(outer, 1)        # div
    add_row(outer, 44)       # search bar
    add_row(outer, 1, True)  # content
    add_row(outer, 1)        # div
    add_row(outer, 52)       # bottom

    place(outer, title_bar(doc.Title, "Family Browser"), 0)
    d1 = Border(); d1.Background = BORDER; d1.Height = 1
    place(outer, d1, 1)

    # Search bar
    search_row = StackPanel()
    search_row.Orientation = Orientation.Horizontal
    search_row.Background  = BG_MID
    search_row.Margin      = Thickness(16, 6, 16, 6)

    search_lbl = label("Search: ", size=12, color=FG_SEC)
    search_lbl.VerticalAlignment = VerticalAlignment.Center
    search_lbl.Margin = Thickness(0, 0, 8, 0)
    search_row.Children.Add(search_lbl)

    search_tb = TextBox()
    search_tb.Width = 320
    search_tb.Height = 30
    search_tb.FontSize = 12
    search_tb.Background = BG_INP
    search_tb.Foreground = FG_PRI
    search_tb.CaretBrush = GOLD
    search_tb.BorderBrush = BORDER
    search_tb.BorderThickness = Thickness(1)
    search_tb.Padding = Thickness(8, 4, 8, 4)
    search_row.Children.Add(search_tb)

    count_lbl = label("  {} families loaded".format(len(non_tag_families)), size=10, color=FG_DIM)
    count_lbl.VerticalAlignment = VerticalAlignment.Center
    count_lbl.Margin = Thickness(12, 0, 0, 0)
    search_row.Children.Add(count_lbl)

    place(outer, search_row, 2)

    # Split: family list | symbol list + info
    content = Grid()
    add_col(content, 1, True)
    add_col(content, 1)
    add_col(content, 1, True)
    content.Margin = Thickness(0)

    # Family list
    fam_list = ListBox()
    fam_list.Background = BG_DARK
    fam_list.Foreground = FG_PRI
    fam_list.FontSize   = 12
    fam_list.BorderThickness = Thickness(0)
    fam_list.Margin = Thickness(16, 8, 0, 8)
    for name in non_tag_families:
        item = ListBoxItem()
        item.Content = name
        item.Padding = Thickness(8, 4, 8, 4)
        fam_list.Items.Add(item)
    place(content, fam_list, 0, 0)

    # Divider
    vdiv = Border(); vdiv.Background = BORDER; vdiv.Width = 1
    place(content, vdiv, 0, 1)

    # Right panel: symbol list + info
    right = StackPanel()
    right.Orientation = Orientation.Vertical
    right.Margin      = Thickness(12, 8, 16, 8)

    sym_header = label("Select a family →", size=11, color=GOLD)
    right.Children.Add(sym_header)

    sym_list = ListBox()
    sym_list.Background = BG_DARK
    sym_list.Foreground = FG_PRI
    sym_list.FontSize   = 12
    sym_list.BorderThickness = Thickness(0)
    sym_list.Height     = 200
    right.Children.Add(sym_list)

    right.Children.Add(divider())

    info_block = TextBlock()
    info_block.Text       = "Select a family and type to see details."
    info_block.Foreground = FG_DIM
    info_block.FontSize   = 11
    info_block.TextWrapping = TextWrapping.Wrap
    right.Children.Add(info_block)

    place(content, right, 0, 2)
    place(outer, content, 3)

    d2 = Border(); d2.Background = BORDER; d2.Height = 1
    place(outer, d2, 4)

    # Bottom
    bottom = Grid()
    bottom.Background = BG_MID
    add_col(bottom, 1, True)
    add_col(bottom, 160)
    add_col(bottom, 8)
    add_col(bottom, 120)
    add_col(bottom, 14)

    btn_place  = button("Place Instance", gold=True,  width=150, height=34)
    btn_cancel = button("Close",          gold=False, width=110, height=34)
    btn_place.Margin  = Thickness(0, 9, 0, 9)
    btn_cancel.Margin = Thickness(0, 9, 0, 9)
    place(bottom, btn_place,  0, 1)
    place(bottom, btn_cancel, 0, 3)
    place(outer, bottom, 5)

    # ── Event handlers ────────────────────────────────────────
    def refresh_family_list(filter_text=""):
        fam_list.Items.Clear()
        for name in non_tag_families:
            if not filter_text or filter_text.lower() in name.lower():
                item = ListBoxItem()
                item.Content = name
                item.Padding = Thickness(8, 4, 8, 4)
                fam_list.Items.Add(item)

    def on_search_changed(s, e):
        refresh_family_list(search_tb.Text)

    def on_fam_selected(s, e):
        item = fam_list.SelectedItem
        if not item:
            return
        fname = item.Content
        sel_fam[0] = fname
        sym_list.Items.Clear()
        sym_header.Text = fname
        fam_data = fam_index.get(fname)
        if fam_data:
            for sym in fam_data["symbols"]:
                si = ListBoxItem()
                si.Content = sym.Name
                si.Padding = Thickness(8, 3, 8, 3)
                sym_list.Items.Add(si)
            if sym_list.Items.Count > 0:
                sym_list.SelectedIndex = 0

    def on_sym_selected(s, e):
        fam_item = fam_list.SelectedItem
        sym_item = sym_list.SelectedItem
        if not fam_item or not sym_item:
            return
        fname = fam_item.Content
        sname = sym_item.Content
        sel_sym[0] = sname
        fam_data = fam_index.get(fname)
        if not fam_data:
            return
        sym = next((s for s in fam_data["symbols"] if s.Name == sname), None)
        if not sym:
            return
        # Show info
        lines = [
            "Family:   {}".format(fname),
            "Type:     {}".format(sname),
            "Category: {}".format(sym.Category.Name if sym.Category else "?"),
            "Family is tag: {}".format(fam_data["is_tag"]),
        ]
        # Count instances
        try:
            instances = list(FilteredElementCollector(doc)
                             .OfClass(FamilyInstance)
                             .ToElements())
            inst_count = sum(1 for i in instances if i.Symbol.Id == sym.Id)
            lines.append("Instances in model: {}".format(inst_count))
        except Exception:
            pass
        info_block.Text = "\n".join(lines)

    def on_place(s, e):
        if sel_fam[0] and sel_sym[0]:
            action[0] = "place"
            win.Close()

    def on_cancel(s, e):
        sel_fam[0] = None
        win.Close()

    search_tb.TextChanged  += on_search_changed
    fam_list.SelectionChanged += on_fam_selected
    sym_list.SelectionChanged += on_sym_selected
    btn_place.Click  += on_place
    btn_cancel.Click += on_cancel

    win.Loaded += lambda s, e: (search_tb.Focus(), Keyboard.Focus(search_tb))
    win.Content = outer
    win.ShowDialog()
    return sel_fam[0], sel_sym[0]


fname, sname = show_browser()
if not fname or not sname:
    script.exit()

# ── Activate symbol and place ─────────────────────────────────
fam_data = fam_index.get(fname)
if not fam_data:
    forms.alert("Family not found.", title="Family Browser")
    script.exit()

sym = next((s for s in fam_data["symbols"] if s.Name == sname), None)
if not sym:
    forms.alert("Type '{}' not found.".format(sname), title="Family Browser")
    script.exit()

output.print_md("# Family Browser")
output.print_md("**Selected:** {} : {}".format(fname, sname))

# Activate if not active
if not sym.IsActive:
    with revit.Transaction("Activate Family"):
        sym.Activate()
        doc.Regenerate()

# Place at origin on first level
try:
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    levels.sort(key=lambda l: l.Elevation)
    place_level = levels[0] if levels else None

    with revit.Transaction("Place Family Instance"):
        inst = doc.Create.NewFamilyInstance(
            XYZ(0, 0, place_level.Elevation if place_level else 0),
            sym,
            place_level,
            DB.Structure.StructuralType.NonStructural
        )

    output.print_md("**Placed** {} : {} at origin on {}.".format(
        fname, sname, place_level.Name if place_level else "Level 0"))
    output.print_md("*Use Move (MV) to reposition. Instance ID: {}*".format(inst.Id))

    forms.alert(
        "Placed: {} : {}\nOn level: {}\n\nInstance placed at project origin.\n"
        "Use Move (MV) in Revit to reposition it.".format(
            fname, sname, place_level.Name if place_level else "?"),
        title="Family Placed"
    )

except Exception as ex:
    import traceback
    err = traceback.format_exc()
    output.print_md("**Error placing family:**\n```\n{}\n```".format(err))
    forms.alert("Could not place family:\n\n{}".format(str(ex)[:400]), title="Error")
