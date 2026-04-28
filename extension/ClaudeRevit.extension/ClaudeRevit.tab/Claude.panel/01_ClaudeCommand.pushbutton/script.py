# -*- coding: utf-8 -*-
__title__ = "Claude\nCommand"
__doc__ = "Type any instruction. Claude writes and executes the Revit API code live."

import sys, os, clr, time

_lib = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(_lib))

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (Window, Thickness, GridLength, GridUnitType,
                             WindowStartupLocation, ResizeMode,
                             TextWrapping, HorizontalAlignment, VerticalAlignment,
                             FontWeights)
from System.Windows.Controls import (Grid, RowDefinition, ColumnDefinition,
                                      StackPanel, TextBlock, TextBox, Button,
                                      ScrollBarVisibility, Orientation, Border,
                                      CornerRadius)
from System.Windows.Input import Keyboard, Key, ModifierKeys
from System.Windows.Media import SolidColorBrush, Color, LinearGradientBrush, GradientStop

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Wall, Floor, ViewSheet, Level
from claude_client import ask_claude, strip_fences, exec_claude_code, revit_exec_context

doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

# ── Model context ────────────────────────────────────────────
try:
    walls  = FilteredElementCollector(doc).OfClass(Wall).GetElementCount()
    floors = FilteredElementCollector(doc).OfClass(Floor).GetElementCount()
    sheets = FilteredElementCollector(doc).OfClass(ViewSheet).GetElementCount()
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    level_names = ", ".join(l.Name for l in levels)
    model_ctx = "{}  |  Walls: {}   Floors: {}   Sheets: {}   Levels: [{}]".format(
        doc.Title, walls, floors, sheets, level_names)
except Exception as e:
    model_ctx = "{} (context error: {})".format(doc.Title, e)


def _c(r, g, b, a=255):
    return SolidColorBrush(Color.FromArgb(a, r, g, b))


def show_chat_dialog(model_ctx_text):
    """Chat-style WPF prompt window. Returns instruction string or None."""
    result = [None]

    win = Window()
    win.Title = "Claude Command"
    win.Width  = 780
    win.Height = 620
    win.MinWidth  = 560
    win.MinHeight = 440
    win.WindowStartupLocation = WindowStartupLocation.CenterScreen
    win.ResizeMode  = ResizeMode.CanResizeWithGrip
    win.Background  = _c(18, 18, 22)
    win.BorderBrush = _c(50, 50, 65)
    win.BorderThickness = Thickness(1)

    # ── Outer grid: titlebar / body / input bar ──────────────
    outer = Grid()
    for h in [44, 1, 1, 52]:   # title, divider, body(star), input
        rd = RowDefinition()
        rd.Height = GridLength(h, GridUnitType.Pixel if h != 1 else GridUnitType.Pixel)
        outer.RowDefinitions.Add(rd)
    # fix: star row
    outer.RowDefinitions.Clear()

    def add_row(val, star=False):
        rd = RowDefinition()
        rd.Height = GridLength(val, GridUnitType.Star if star else GridUnitType.Pixel)
        outer.RowDefinitions.Add(rd)

    add_row(48)       # 0 titlebar
    add_row(1)        # 1 divider
    add_row(1, True)  # 2 body (stretches)
    add_row(1)        # 3 divider2
    add_row(130)      # 4 input area

    # ── Titlebar ─────────────────────────────────────────────
    title_bg = Border()
    title_bg.Background = _c(24, 24, 32)
    title_row = Grid()

    dot_row = StackPanel()
    dot_row.Orientation = Orientation.Horizontal
    dot_row.VerticalAlignment = VerticalAlignment.Center
    dot_row.Margin = Thickness(16, 0, 0, 0)
    for col in [(220, 80, 80), (240, 180, 60), (80, 200, 100)]:
        d = Border()
        d.Width  = 10
        d.Height = 10
        d.CornerRadius = CornerRadius(5)
        d.Background = _c(*col)
        d.Margin = Thickness(0, 0, 6, 0)
        dot_row.Children.Add(d)
    title_row.Children.Add(dot_row)

    title_lbl = TextBlock()
    title_lbl.Text = "Claude Command  —  " + doc.Title
    title_lbl.Foreground = _c(200, 169, 110)
    title_lbl.FontSize   = 13
    title_lbl.FontWeight = FontWeights.SemiBold
    title_lbl.HorizontalAlignment = HorizontalAlignment.Center
    title_lbl.VerticalAlignment   = VerticalAlignment.Center
    title_row.Children.Add(title_lbl)

    title_bg.Child = title_row
    Grid.SetRow(title_bg, 0)
    outer.Children.Add(title_bg)

    # divider
    div = Border()
    div.Background = _c(50, 50, 70)
    Grid.SetRow(div, 1)
    outer.Children.Add(div)

    # ── Body: context + prompt hint ─────────────────────────
    body = Grid()
    body.Background = _c(18, 18, 22)
    body.Margin = Thickness(24, 16, 24, 8)

    body_rows = Grid()

    def add_body_row(v, star=False):
        rd = RowDefinition()
        rd.Height = GridLength(v, GridUnitType.Star if star else GridUnitType.Pixel)
        body_rows.RowDefinitions.Add(rd)

    add_body_row(26)      # context tag
    add_body_row(10)      # spacer
    add_body_row(1, True) # hint (fills)

    ctx_pill = Border()
    ctx_pill.Background    = _c(35, 35, 50)
    ctx_pill.CornerRadius  = CornerRadius(4)
    ctx_pill.Padding       = Thickness(10, 4, 10, 4)
    ctx_pill.HorizontalAlignment = HorizontalAlignment.Left

    ctx_text = TextBlock()
    ctx_text.Text       = model_ctx_text
    ctx_text.Foreground = _c(120, 120, 150)
    ctx_text.FontSize   = 10
    ctx_text.TextWrapping = TextWrapping.NoWrap
    ctx_pill.Child = ctx_text
    Grid.SetRow(ctx_pill, 0)
    body_rows.Children.Add(ctx_pill)

    hint_block = TextBlock()
    hint_block.Foreground   = _c(55, 55, 75)
    hint_block.FontSize     = 12
    hint_block.TextWrapping = TextWrapping.Wrap
    hint_block.VerticalAlignment = VerticalAlignment.Center
    hint_block.Text = (
        "Try:\n"
        "  Create 5 storeys at 4m spacing\n"
        "  Build a 12m x 8m floor plan with 200mm concrete walls on Level 1\n"
        "  Create sheets A101-A115 with A1 title block, one floor plan per level\n"
        "  Rename all rooms on Level 0 with prefix GF-\n"
        "  Create a room schedule: Number, Name, Area, Level"
    )
    Grid.SetRow(hint_block, 2)
    body_rows.Children.Add(hint_block)

    body.Children.Add(body_rows)
    Grid.SetRow(body, 2)
    outer.Children.Add(body)

    # divider2
    div2 = Border()
    div2.Background = _c(40, 40, 55)
    Grid.SetRow(div2, 3)
    outer.Children.Add(div2)

    # ── Input area ───────────────────────────────────────────
    input_bg = Border()
    input_bg.Background = _c(24, 24, 32)
    input_bg.Padding    = Thickness(16, 12, 16, 12)

    input_grid = Grid()

    col_text = ColumnDefinition()
    col_text.Width = GridLength(1, GridUnitType.Star)
    col_btn  = ColumnDefinition()
    col_btn.Width  = GridLength(110, GridUnitType.Pixel)
    input_grid.ColumnDefinitions.Add(col_text)
    input_grid.ColumnDefinitions.Add(col_btn)

    # TextBox — the actual input
    tb = TextBox()
    tb.AcceptsReturn = True
    tb.TextWrapping  = TextWrapping.Wrap
    tb.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
    tb.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
    tb.FontSize     = 13
    tb.MinHeight    = 70
    tb.MaxHeight    = 90
    tb.Background   = _c(30, 30, 40)
    tb.Foreground   = _c(235, 235, 245)
    tb.CaretBrush   = _c(200, 169, 110)
    tb.BorderBrush  = _c(70, 70, 90)
    tb.BorderThickness = Thickness(1)
    tb.Padding      = Thickness(10, 8, 10, 8)
    tb.VerticalAlignment = VerticalAlignment.Stretch
    tb.Margin       = Thickness(0, 0, 12, 0)
    Grid.SetColumn(tb, 0)
    input_grid.Children.Add(tb)

    # Send button
    send_col = StackPanel()
    send_col.VerticalAlignment = VerticalAlignment.Bottom
    Grid.SetColumn(send_col, 1)

    shortcut_hint = TextBlock()
    shortcut_hint.Text = "Ctrl+Enter"
    shortcut_hint.Foreground = _c(70, 70, 90)
    shortcut_hint.FontSize   = 9
    shortcut_hint.HorizontalAlignment = HorizontalAlignment.Center
    shortcut_hint.Margin = Thickness(0, 0, 0, 4)
    send_col.Children.Add(shortcut_hint)

    btn_send = Button()
    btn_send.Content  = "Run with Claude"
    btn_send.Height   = 40
    btn_send.Background  = _c(200, 169, 110)
    btn_send.Foreground  = _c(18, 18, 22)
    btn_send.FontSize    = 12
    btn_send.FontWeight  = FontWeights.Bold
    btn_send.BorderThickness = Thickness(0)
    send_col.Children.Add(btn_send)

    input_grid.Children.Add(send_col)
    input_bg.Child = input_grid
    Grid.SetRow(input_bg, 4)
    outer.Children.Add(input_bg)

    # ── Events ───────────────────────────────────────────────
    def on_run(s, e):
        t = tb.Text.strip()
        if t:
            result[0] = t
            win.Close()

    def on_key(s, e):
        if e.Key == Key.Return and Keyboard.Modifiers == ModifierKeys.Control:
            t = tb.Text.strip()
            if t:
                result[0] = t
                win.Close()
        elif e.Key == Key.Escape:
            win.Close()

    btn_send.Click += on_run
    tb.KeyDown     += on_key

    def on_loaded(s, e):
        tb.Focus()
        Keyboard.Focus(tb)

    win.Loaded += on_loaded
    win.Content = outer
    win.ShowDialog()
    return result[0]


# ── Show dialog ───────────────────────────────────────────────
instruction = show_chat_dialog(model_ctx)
if not instruction:
    script.exit()

# ── System prompt ─────────────────────────────────────────────
SYSTEM = """\
You are a Revit API Python expert writing code for pyRevit (IronPython 2.7).

ENVIRONMENT (already in scope, do NOT re-import):
  doc, uidoc, revit, DB, forms, output
  All DB classes: XYZ, Line, Wall, Level, ViewSheet, Floor, etc.

UNITS: Revit internal = decimal feet.
  1m = 3.28084 ft  |  1mm = 1/304.8 ft

TRANSACTIONS: wrap ALL model changes in:
  with revit.Transaction("description"):
      ...

STRICT RULES (IronPython 2.7 — no exceptions):
  - "{}".format() ONLY. ZERO f-strings.
  - No type hints, no walrus :=, no match/case
  - forms.alert("msg", title="X") ONLY. Never ok_btn or warn_icon.
  - output.print_code(code) -- 1 argument, never 2
  - Return ONLY executable Python -- no markdown, no fences, no explanation
  - Wrap all code in try/except. Surface errors via forms.alert()
  - End with: forms.alert("Done: <one-line summary>", title="Claude")

MODEL: """ + model_ctx

output.print_md("# Claude Command")
output.print_md("**Instruction:** " + instruction)
output.print_md("Calling Claude...")

try:
    code = strip_fences(ask_claude(instruction, system=SYSTEM, max_tokens=1200))
except Exception as e:
    forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
    script.exit()

output.print_md("**Generated code:**")
output.print_code(code)

go = forms.alert(
    "Code shown above in the output window.\nAll changes are undoable with Ctrl+Z.\n\nProceed?",
    title="Execute?", cancel=True
)
if not go:
    output.print_md("*Cancelled.*")
    script.exit()

ctx = revit_exec_context(doc, uidoc, revit, DB, forms, output)
ok, err = exec_claude_code(code, ctx)
if not ok:
    output.print_md("**Execution error:**\n```\n{}\n```".format(err))
    forms.alert("Execution failed.\n\n{}".format(err[:500]), title="Error")
