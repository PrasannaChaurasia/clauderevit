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

from System.Windows import Window, Thickness
from System.Windows.Controls import (StackPanel, TextBlock, TextBox, Button,
                                      ScrollViewer, Orientation)
from System.Windows.Media import SolidColorBrush, Color
from System.Windows import FontWeights

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


def show_prompt_dialog(model_ctx_text):
    """Show a large WPF dialog for entering instructions. Returns text or None."""
    result = [None]

    win = Window()
    win.Title = "Claude Command"
    win.Width = 720
    win.Height = 520
    win.WindowStartupLocation = 1  # CenterScreen
    win.ResizeMode = 1             # CanResizeWithGrip
    win.Background = SolidColorBrush(Color.FromRgb(30, 30, 30))

    root = StackPanel()
    root.Margin = Thickness(18)
    root.Orientation = Orientation.Vertical

    # Header
    header = TextBlock()
    header.Text = "Claude Command  —  {}".format(doc.Title)
    header.Foreground = SolidColorBrush(Color.FromRgb(200, 169, 110))
    header.FontSize = 15
    header.FontWeight = FontWeights.Bold
    header.Margin = Thickness(0, 0, 0, 6)
    root.Children.Add(header)

    # Model context info
    ctx_block = TextBlock()
    ctx_block.Text = model_ctx_text
    ctx_block.Foreground = SolidColorBrush(Color.FromRgb(160, 160, 160))
    ctx_block.FontSize = 11
    ctx_block.TextWrapping = 3  # Wrap
    ctx_block.Margin = Thickness(0, 0, 0, 10)
    root.Children.Add(ctx_block)

    # Label
    lbl = TextBlock()
    lbl.Text = "Instruction:"
    lbl.Foreground = SolidColorBrush(Color.FromRgb(220, 220, 220))
    lbl.FontSize = 12
    lbl.Margin = Thickness(0, 0, 0, 4)
    root.Children.Add(lbl)

    # Large text box
    tb = TextBox()
    tb.Height = 240
    tb.AcceptsReturn = True
    tb.TextWrapping = 3  # Wrap
    tb.VerticalScrollBarVisibility = 2  # Auto
    tb.FontSize = 13
    tb.Background = SolidColorBrush(Color.FromRgb(45, 45, 45))
    tb.Foreground = SolidColorBrush(Color.FromRgb(230, 230, 230))
    tb.CaretBrush = SolidColorBrush(Color.FromRgb(200, 169, 110))
    tb.BorderBrush = SolidColorBrush(Color.FromRgb(80, 80, 80))
    tb.Padding = Thickness(8)
    tb.Margin = Thickness(0, 0, 0, 10)
    root.Children.Add(tb)

    # Examples
    eg = TextBlock()
    eg.Text = (
        "Examples:\n"
        "  Create 5 storeys at 4m spacing\n"
        "  Build a 12m x 8m rectangular floor plan with 200mm walls on Level 0\n"
        "  Create sheets A101-A110 and place one floor plan view per level\n"
        "  Rename all rooms on Level 1 with prefix 'L1-'\n"
        "  Create a wall schedule showing Type, Length, Area"
    )
    eg.Foreground = SolidColorBrush(Color.FromRgb(120, 120, 120))
    eg.FontSize = 11
    eg.Margin = Thickness(0, 0, 0, 14)
    root.Children.Add(eg)

    # Buttons row
    btn_row = StackPanel()
    btn_row.Orientation = Orientation.Horizontal

    btn_run = Button()
    btn_run.Content = "Run with Claude"
    btn_run.Width = 160
    btn_run.Height = 34
    btn_run.Margin = Thickness(0, 0, 10, 0)
    btn_run.Background = SolidColorBrush(Color.FromRgb(200, 169, 110))
    btn_run.Foreground = SolidColorBrush(Color.FromRgb(20, 20, 20))
    btn_run.FontSize = 13
    btn_run.FontWeight = FontWeights.Bold

    btn_cancel = Button()
    btn_cancel.Content = "Cancel"
    btn_cancel.Width = 100
    btn_cancel.Height = 34
    btn_cancel.Background = SolidColorBrush(Color.FromRgb(60, 60, 60))
    btn_cancel.Foreground = SolidColorBrush(Color.FromRgb(200, 200, 200))
    btn_cancel.FontSize = 13

    def on_run(s, e):
        result[0] = tb.Text.strip()
        win.Close()

    def on_cancel(s, e):
        win.Close()

    btn_run.Click += on_run
    btn_cancel.Click += on_cancel

    btn_row.Children.Add(btn_run)
    btn_row.Children.Add(btn_cancel)
    root.Children.Add(btn_row)

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
  doc   → Autodesk.Revit.DB.Document
  uidoc → Autodesk.Revit.UI.UIDocument
  revit → pyrevit.revit module
  DB    → Autodesk.Revit.DB module
  forms → pyrevit.forms module
  output → pyrevit script output
  All DB classes (XYZ, Line, Wall, Level, ViewSheet, etc.) are in scope directly.

UNITS: Revit internal = decimal feet. Always convert: 1m = 3.28084 ft, 1mm = 1/304.8 ft.

TRANSACTIONS: Wrap ALL model changes in:
  with revit.Transaction("description"):
      ...

STRICT RULES (IronPython 2.7):
  - Use "{}".format() — NO f-strings
  - No type hints, no walrus operator, no match/case
  - forms.alert("msg", title="X") only — NO ok_btn, NO warn_icon params
  - output.print_code(code) — 1 argument only
  - Return ONLY executable Python code — no markdown, no explanation
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
    "Code is shown in the output window.\n\nEverything is undoable with Ctrl+Z.\n\nProceed?",
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
