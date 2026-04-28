# -*- coding: utf-8 -*-
__title__ = "Python\nScript"
__doc__ = "Write and run any Python script directly inside Revit. Supports IronPython 2.7. Claude can generate the script from plain English."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (Thickness, HorizontalAlignment, VerticalAlignment,
                             FontWeights, TextWrapping, CornerRadius)
from System.Windows.Controls import (Grid, StackPanel, Border, TextBlock, TextBox,
                                      Button, Orientation, ScrollBarVisibility)
from System.Windows.Media import FontFamily
from System.Windows.Input import Keyboard, Key, ModifierKeys

from wpf_helper import (base_window, title_bar, add_row, add_col, place,
                         label, button, divider, pill,
                         GOLD, BG_MID, BG_CARD, BG_INP, BG_DARK,
                         FG_PRI, FG_SEC, FG_DIM, BORDER, rgb)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, Wall, ViewSheet
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

try:
    walls  = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    model_ctx = "{}  |  Walls:{}  Sheets:{}  Levels:[{}]".format(
        doc.Title, walls, sheets, ", ".join(l.Name for l in levels))
except Exception:
    model_ctx = doc.Title

STARTER = """\
# ClaudeRevit Python Script  (IronPython 2.7)
# Environment: doc, uidoc, revit, DB, forms, output — all in scope
# Units: decimal feet  (1m = 3.28084 ft)
# Transactions: with revit.Transaction("name"): ...
# String format: "{}".format(x)  — NO f-strings

from Autodesk.Revit.DB import FilteredElementCollector, Level

levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
levels.sort(key=lambda l: l.Elevation)
for lvl in levels:
    output.print_md("- **{}**  @ {:.2f} m".format(lvl.Name, lvl.Elevation * 0.3048))

forms.alert("Listed {} levels.".format(len(levels)), title="Done")
"""


def show_editor():
    result = [None]
    action = ["run"]

    win = base_window("Python Script Editor", doc.Title, width=880, height=660)

    outer = Grid()
    add_row(outer, 44)       # titlebar
    add_row(outer, 1)        # divider
    add_row(outer, 38)       # toolbar
    add_row(outer, 1, True)  # editor (fills)
    add_row(outer, 1)        # divider
    add_row(outer, 50)       # bottom bar

    place(outer, title_bar(doc.Title, "Python Script Editor"), 0)
    d1 = Border(); d1.Background = BORDER; d1.Height = 1
    place(outer, d1, 1)

    toolbar = StackPanel()
    toolbar.Orientation = Orientation.Horizontal
    toolbar.Background  = BG_MID
    toolbar.Margin      = Thickness(14, 5, 14, 5)
    toolbar.Children.Add(pill("IronPython 2.7  |  Full Revit API  |  Ctrl+Enter to run", fg=FG_DIM, bg=BG_CARD))
    place(outer, toolbar, 2)

    editor = TextBox()
    editor.FontFamily = FontFamily("Consolas")
    editor.FontSize   = 13
    editor.Background = rgb(14, 14, 20)
    editor.Foreground = FG_PRI
    editor.CaretBrush = GOLD
    editor.BorderThickness = Thickness(0)
    editor.Padding    = Thickness(18, 14, 18, 14)
    editor.AcceptsReturn = True
    editor.AcceptsTab    = True
    editor.TextWrapping  = TextWrapping.NoWrap
    editor.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
    editor.HorizontalScrollBarVisibility = ScrollBarVisibility.Auto
    editor.Text = STARTER
    place(outer, editor, 3)

    d2 = Border(); d2.Background = BORDER; d2.Height = 1
    place(outer, d2, 4)

    bottom = Grid()
    bottom.Background = BG_MID
    add_col(bottom, 1, True)
    add_col(bottom, 140)
    add_col(bottom, 8)
    add_col(bottom, 150)
    add_col(bottom, 8)
    add_col(bottom, 110)
    add_col(bottom, 14)

    hint = label("Ctrl+Enter: Run  |  Ctrl+G: Ask Claude to generate  |  Esc: Close",
                 size=10, color=FG_DIM)
    hint.VerticalAlignment = VerticalAlignment.Center
    hint.Margin = Thickness(16, 0, 0, 0)
    place(bottom, hint, 0, 0)

    btn_gen = button("Ask Claude", gold=False, width=130, height=34)
    btn_gen.Margin = Thickness(0, 8, 0, 8)
    place(bottom, btn_gen, 0, 1)

    btn_run = button("Run Script", gold=True, width=140, height=34)
    btn_run.Margin = Thickness(0, 8, 0, 8)
    place(bottom, btn_run, 0, 3)

    btn_cancel = button("Close", gold=False, width=100, height=34)
    btn_cancel.Margin = Thickness(0, 8, 0, 8)
    place(bottom, btn_cancel, 0, 5)

    place(outer, bottom, 5)

    def on_run(s, e):
        result[0] = editor.Text; action[0] = "run"; win.Close()

    def on_gen(s, e):
        result[0] = editor.Text; action[0] = "generate"; win.Close()

    def on_cancel(s, e):
        win.Close()

    def on_key(s, e):
        if e.Key == Key.Return and Keyboard.Modifiers == ModifierKeys.Control:
            result[0] = editor.Text; action[0] = "run"; win.Close()
        elif e.Key == Key.G and Keyboard.Modifiers == ModifierKeys.Control:
            result[0] = editor.Text; action[0] = "generate"; win.Close()
        elif e.Key == Key.Escape:
            win.Close()

    btn_run.Click    += on_run
    btn_gen.Click    += on_gen
    btn_cancel.Click += on_cancel
    editor.KeyDown   += on_key

    win.Loaded += lambda s, e: (editor.Focus(), Keyboard.Focus(editor),
                                 setattr(editor, "CaretIndex", len(editor.Text)))
    win.Content = outer
    win.ShowDialog()
    return result[0], action[0]


code_text, user_action = show_editor()
if not code_text or not code_text.strip():
    script.exit()

if user_action == "generate":
    desc = forms.ask_for_string(
        prompt="Describe what the Python script should do in Revit:",
        title="Ask Claude — Python Generation",
        default=""
    )
    if not desc:
        script.exit()

    SYSTEM = """\
You are a Revit API Python expert. Write IronPython 2.7 code for pyRevit.

ENVIRONMENT (already in scope — do NOT import these):
  doc, uidoc, revit, DB, forms, output
  All DB classes: XYZ, Line, Wall, Level, Floor, ViewSheet, FilteredElementCollector, etc.

STRICT RULES:
  - "{}".format() ONLY. Zero f-strings.
  - No type hints, no walrus :=, no match/case
  - forms.alert("msg", title="X") only — no ok_btn, no warn_icon
  - output.print_code(code) — 1 argument only
  - with revit.Transaction("name"): for ALL model changes
  - Return ONLY executable Python. No markdown. No explanation.
  - End with forms.alert("Done: ...", title="Script")
MODEL: """ + model_ctx

    output.print_md("# Python Script — Claude generating...")
    try:
        code_text = strip_fences(ask_claude(desc, system=SYSTEM, max_tokens=1500))
    except Exception as e:
        forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
        script.exit()

    output.print_md("**Generated code:**")
    output.print_code(code_text)
    if not forms.alert("Review code above.\nRun it?", title="Run Script?", cancel=True):
        script.exit()

output.print_md("# Python Script — Running")
ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code_text, ctx)
if ok:
    output.print_md("**Script completed.**")
else:
    output.print_md("**Error:**\n```\n{}\n```".format(err))
    forms.alert("Script error:\n\n{}".format(err[:600]), title="Python Script Error")
