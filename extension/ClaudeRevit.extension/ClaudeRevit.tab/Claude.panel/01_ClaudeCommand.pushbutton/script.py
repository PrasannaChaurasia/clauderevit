# -*- coding: utf-8 -*-
__title__ = "Claude\nCommand"
__doc__ = "Type any instruction. Claude writes and executes the Revit API code live."

import sys
import os
import clr

_lib = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(_lib))

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import Window, Thickness, GridLength, GridUnitType
from System.Windows.Controls import (Grid, RowDefinition, StackPanel, TextBlock,
                                      TextBox, Button, Orientation,
                                      ScrollBarVisibility)
from System.Windows.Input import Keyboard
from System.Windows.Media import SolidColorBrush, Color
from System.Windows import FontWeights, HorizontalAlignment, VerticalAlignment

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Wall, Floor, ViewSheet, Level
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# ---- Model context ----
try:
    walls  = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    floors = FilteredElementCollector(doc).OfClass(Floor).GetElementCount()
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    level_names = ", ".join(l.Name for l in levels)
    model_ctx = "Model: {} | Walls:{} Floors:{} Sheets:{} Levels:[{}]".format(
        doc.Title, walls, floors, sheets, level_names)
except Exception as e:
    model_ctx = "Model: {} (context error: {})".format(doc.Title, e)


def _brush(r, g, b):
    return SolidColorBrush(Color.FromRgb(r, g, b))


def show_prompt_dialog(model_ctx_text):
    """Large WPF prompt window. Returns instruction string or None."""
    result = [None]
    tb_ref = [None]

    win = Window()
    win.Title = "Claude Command"
    win.Width = 740
    win.Height = 560
    win.MinWidth = 520
    win.MinHeight = 400
    win.WindowStartupLocation = 1   # CenterScreen
    win.ResizeMode = 1              # CanResizeWithGrip
    win.Background = _brush(24, 24, 24)

    # --- Root Grid: 5 rows ---
    root = Grid()
    root.Margin = Thickness(20)

    def add_row(height_val, unit=GridUnitType.Pixel):
        rd = RowDefinition()
        rd.Height = GridLength(height_val, unit)
        root.RowDefinitions.Add(rd)

    add_row(32)          # row 0 — header
    add_row(20)          # row 1 — context line
    add_row(16)          # row 2 — label
    add_row(1, GridUnitType.Star)  # row 3 — text box (stretches)
    add_row(50)          # row 4 — examples + buttons

    def place(ctrl, row, col=0, colspan=1):
        Grid.SetRow(ctrl, row)
        Grid.SetColumn(ctrl, col)
        if colspan > 1:
            Grid.SetColumnSpan(ctrl, colspan)
        root.Children.Add(ctrl)

    # Header
    header = TextBlock()
    header.Text = "Claude Command  —  {}".format(doc.Title)
    header.Foreground = _brush(200, 169, 110)
    header.FontSize = 15
    header.FontWeight = FontWeights.Bold
    header.VerticalAlignment = VerticalAlignment.Center
    place(header, 0)

    # Context
    ctx_block = TextBlock()
    ctx_block.Text = model_ctx_text
    ctx_block.Foreground = _brush(130, 130, 130)
    ctx_block.FontSize = 11
    ctx_block.TextWrapping = 3
    ctx_block.VerticalAlignment = VerticalAlignment.Center
    place(ctx_block, 1)

    # Label
    lbl = TextBlock()
    lbl.Text = "Instruction  (Ctrl+Enter to run)"
    lbl.Foreground = _brush(180, 180, 180)
    lbl.FontSize = 11
    lbl.VerticalAlignment = VerticalAlignment.Bottom
    lbl.Margin = Thickness(0, 0, 0, 2)
    place(lbl, 2)

    # Text box — fills row 3
    tb = TextBox()
    tb.AcceptsReturn = True
    tb.TextWrapping = 3                             # Wrap
    tb.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
    tb.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
    tb.FontSize = 13
    tb.Background = _brush(36, 36, 36)
    tb.Foreground = _brush(235, 235, 235)
    tb.CaretBrush = _brush(200, 169, 110)
    tb.BorderBrush = _brush(70, 70, 70)
    tb.BorderThickness = Thickness(1)
    tb.Padding = Thickness(10)
    tb.VerticalAlignment = VerticalAlignment.Stretch
    tb.Margin = Thickness(0, 0, 0, 8)
    tb_ref[0] = tb
    place(tb, 3)

    # Bottom row: examples left, buttons right
    bottom = Grid()
    bc = Grid()
    bottom.Children.Add(bc)

    eg = TextBlock()
    eg.Text = (
        "e.g.  Create 5 levels at 4m spacing  •  "
        "Build a 12x8m floor plan with 200mm walls  •  "
        "Create sheets A101-A110 with floor plan views"
    )
    eg.Foreground = _brush(90, 90, 90)
    eg.FontSize = 10
    eg.TextWrapping = 3
    eg.VerticalAlignment = VerticalAlignment.Center
    eg.HorizontalAlignment = HorizontalAlignment.Left
    eg.Margin = Thickness(0, 0, 140, 0)
    bottom.Children.Add(eg)

    # Run button
    btn_run = Button()
    btn_run.Content = "Run with Claude"
    btn_run.Width = 130
    btn_run.Height = 32
    btn_run.Background = _brush(200, 169, 110)
    btn_run.Foreground = _brush(18, 18, 18)
    btn_run.FontSize = 12
    btn_run.FontWeight = FontWeights.Bold
    btn_run.HorizontalAlignment = HorizontalAlignment.Right
    btn_run.Margin = Thickness(0, 0, 0, 0)

    # Cancel button
    btn_cancel = Button()
    btn_cancel.Content = "Cancel"
    btn_cancel.Width = 80
    btn_cancel.Height = 32
    btn_cancel.Background = _brush(50, 50, 50)
    btn_cancel.Foreground = _brush(200, 200, 200)
    btn_cancel.FontSize = 12
    btn_cancel.HorizontalAlignment = HorizontalAlignment.Right
    btn_cancel.Margin = Thickness(0, 0, 136, 0)

    bottom.Children.Add(btn_run)
    bottom.Children.Add(btn_cancel)
    place(bottom, 4)

    # Key binding: Ctrl+Enter triggers Run
    def on_key(s, e):
        from System.Windows.Input import Key, ModifierKeys
        if e.Key == Key.Return and (Keyboard.Modifiers == ModifierKeys.Control):
            result[0] = tb.Text.strip()
            win.Close()

    tb.KeyDown += on_key

    def on_run(s, e):
        result[0] = tb.Text.strip()
        win.Close()

    def on_cancel(s, e):
        win.Close()

    btn_run.Click += on_run
    btn_cancel.Click += on_cancel

    # Force focus to text box as soon as window loads
    def on_loaded(s, e):
        tb.Focus()
        Keyboard.Focus(tb)

    win.Loaded += on_loaded
    win.Content = root
    win.ShowDialog()
    return result[0] if result[0] else None


# ---- Show dialog ----
instruction = show_prompt_dialog(model_ctx)

if not instruction:
    script.exit()

# ---- System prompt ----
SYSTEM = """\
You are a Revit API Python expert writing code for pyRevit (IronPython 2.7).

ENVIRONMENT — already available, do NOT re-import:
  doc   -> Autodesk.Revit.DB.Document
  uidoc -> Autodesk.Revit.UI.UIDocument
  revit -> pyrevit.revit module
  DB    -> Autodesk.Revit.DB module
  forms -> pyrevit.forms module
  output -> pyrevit script output
  All DB classes (XYZ, Line, Wall, Level, ViewSheet, etc.) are in scope directly.

UNITS: Revit internal = decimal feet. Always convert: 1m = 3.28084 ft, 1mm = 1/304.8 ft.

TRANSACTIONS: Wrap ALL model changes in:
  with revit.Transaction("description"):
      ...

STRICT RULES (IronPython 2.7):
  - Use "{}".format() ONLY -- NO f-strings whatsoever
  - No type hints, no walrus operator, no match/case
  - forms.alert("msg", title="X") only -- NO ok_btn, NO warn_icon params
  - output.print_code(code) -- 1 argument only, never 2
  - Return ONLY executable Python code -- no markdown, no explanation, no fences
  - Handle exceptions with try/except and surface via forms.alert()
  - End every script with: forms.alert("Done: <summary>", title="Claude")

MODEL CONTEXT: """ + model_ctx

# ---- Call Claude ----
output.print_md("# Claude Command")
output.print_md("**Instruction:** " + instruction)
output.print_md("Calling Claude (claude-sonnet-4-6)...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM, max_tokens=1200))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("**Generated code:**")
output.print_code(code)

# ---- Confirm ----
go = forms.alert(
    "Code shown in output window.\n\nAll changes are undoable with Ctrl+Z.\n\nProceed?",
    title="Execute Claude Code?",
    cancel=True
)
if not go:
    output.print_md("*Cancelled.*")
    script.exit()

# ---- Execute ----
ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Execution error:**\n```\n{}\n```".format(err))
    forms.alert("Execution failed. See output window.\n\n{}".format(err[:500]),
                title="Claude Command Error")
