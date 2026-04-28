# -*- coding: utf-8 -*-
"""
wpf_helper.py
Shared WPF UI building blocks for all ClaudeRevit scripts.
IronPython 2.7 compatible — uses named WPF enums only, never integers.
"""
import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (
    Window, Thickness, GridLength, GridUnitType,
    WindowStartupLocation, ResizeMode, TextWrapping,
    HorizontalAlignment, VerticalAlignment, FontWeights, FontStyles
)
from System.Windows.Controls import (
    Grid, RowDefinition, ColumnDefinition, StackPanel, Border,
    TextBlock, TextBox, Button, ComboBox, ComboBoxItem,
    CheckBox, ListBox, ListBoxItem, ScrollViewer, Label,
    ScrollBarVisibility, Orientation, Separator
)
from System.Windows import CornerRadius
from System.Windows.Input import Keyboard, Key, ModifierKeys
from System.Windows.Media import SolidColorBrush, Color, FontFamily


# ── Colour helpers ────────────────────────────────────────────
def rgb(r, g, b, a=255):
    return SolidColorBrush(Color.FromArgb(a, r, g, b))

GOLD    = rgb(200, 169, 110)
BG_DARK = rgb(18,  18,  22)
BG_MID  = rgb(26,  26,  34)
BG_CARD = rgb(34,  34,  44)
BG_INP  = rgb(28,  28,  38)
FG_PRI  = rgb(235, 235, 245)
FG_SEC  = rgb(160, 160, 175)
FG_DIM  = rgb(90,  90, 110)
BORDER  = rgb(55,  55,  72)
ERR     = rgb(230,  80,  80)
OK      = rgb(80,  210, 100)


def add_row(grid, val, star=False):
    rd = RowDefinition()
    rd.Height = GridLength(val, GridUnitType.Star if star else GridUnitType.Pixel)
    grid.RowDefinitions.Add(rd)


def add_col(grid, val, star=False):
    cd = ColumnDefinition()
    cd.Width = GridLength(val, GridUnitType.Star if star else GridUnitType.Pixel)
    grid.ColumnDefinitions.Add(cd)


def place(grid, ctrl, row=0, col=0, rowspan=1, colspan=1):
    Grid.SetRow(ctrl, row)
    Grid.SetColumn(ctrl, col)
    if rowspan > 1:
        Grid.SetRowSpan(ctrl, rowspan)
    if colspan > 1:
        Grid.SetColumnSpan(ctrl, colspan)
    grid.Children.Add(ctrl)


def label(text, size=12, color=None, bold=False, wrap=False):
    tb = TextBlock()
    tb.Text = text
    tb.FontSize = size
    tb.Foreground = color if color else FG_SEC
    if bold:
        tb.FontWeight = FontWeights.SemiBold
    if wrap:
        tb.TextWrapping = TextWrapping.Wrap
    return tb


def textbox(height=34, multiline=False, size=13):
    tb = TextBox()
    tb.FontSize = size
    tb.Background  = BG_INP
    tb.Foreground  = FG_PRI
    tb.CaretBrush  = GOLD
    tb.BorderBrush = BORDER
    tb.BorderThickness = Thickness(1)
    tb.Padding = Thickness(10, 6, 10, 6)
    if multiline:
        tb.AcceptsReturn = True
        tb.TextWrapping  = TextWrapping.Wrap
        tb.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
        tb.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
        tb.Height = height
    else:
        tb.Height = height
    return tb


def button(text, gold=True, width=None, height=34):
    btn = Button()
    btn.Content = text
    btn.Height  = height
    btn.FontSize = 12
    btn.FontWeight = FontWeights.SemiBold
    btn.BorderThickness = Thickness(0)
    if gold:
        btn.Background = GOLD
        btn.Foreground = BG_DARK
    else:
        btn.Background = BG_CARD
        btn.Foreground = FG_PRI
    if width:
        btn.Width = width
    return btn


def divider():
    b = Border()
    b.Height     = 1
    b.Background = BORDER
    b.Margin     = Thickness(0, 8, 0, 8)
    return b


def pill(text, fg=None, bg=None):
    b = Border()
    b.Background   = bg if bg else BG_CARD
    b.CornerRadius = CornerRadius(4)
    b.Padding      = Thickness(8, 3, 8, 3)
    b.HorizontalAlignment = HorizontalAlignment.Left
    t = TextBlock()
    t.Text       = text
    t.FontSize   = 10
    t.Foreground = fg if fg else FG_DIM
    b.Child = t
    return b


def title_bar(doc_title, panel_name):
    """Titlebar with traffic-light dots + panel name."""
    bg = Border()
    bg.Background = BG_MID
    bg.Padding    = Thickness(16, 0, 16, 0)

    row = Grid()
    row.Height = 44

    dots = StackPanel()
    dots.Orientation = Orientation.Horizontal
    dots.VerticalAlignment = VerticalAlignment.Center
    for col in [(220, 80, 80), (240, 180, 60), (80, 200, 100)]:
        d = Border()
        d.Width  = 10
        d.Height = 10
        d.CornerRadius = CornerRadius(5)
        d.Background = rgb(*col)
        d.Margin = Thickness(0, 0, 6, 0)
        dots.Children.Add(d)
    row.Children.Add(dots)

    t = TextBlock()
    t.Text = "{}  —  {}".format(panel_name, doc_title)
    t.Foreground = GOLD
    t.FontSize   = 13
    t.FontWeight = FontWeights.SemiBold
    t.HorizontalAlignment = HorizontalAlignment.Center
    t.VerticalAlignment   = VerticalAlignment.Center
    row.Children.Add(t)

    bg.Child = row
    return bg


def base_window(title, doc_title, width=760, height=580):
    """Standard ClaudeRevit window with dark theme."""
    win = Window()
    win.Title  = title
    win.Width  = width
    win.Height = height
    win.MinWidth  = 520
    win.MinHeight = 380
    win.WindowStartupLocation = WindowStartupLocation.CenterScreen
    win.ResizeMode  = ResizeMode.CanResizeWithGrip
    win.Background  = BG_DARK
    win.BorderBrush = BORDER
    win.BorderThickness = Thickness(1)
    return win
