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
    ScrollBarVisibility, Orientation, Separator, WrapPanel
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


def chat_prompt(title, message, placeholder="Type your instruction...",
                default="", context=None, width=760, height=520):
    """Large chat-style prompt dialog. Returns entered string or None if cancelled."""
    result = [None]

    win = base_window(title, "", width=width, height=height)

    outer = Grid()
    add_row(outer, 44)
    add_row(outer, 1)
    add_row(outer, 1, True)
    add_row(outer, 1)
    add_row(outer, 54)

    place(outer, title_bar("ClaudeRevit", title), 0)
    d1 = Border(); d1.Background = BORDER; d1.Height = 1
    place(outer, d1, 1)

    content = Grid()
    content.Background = BG_DARK
    content.Margin = Thickness(24, 16, 24, 0)
    if context:
        add_row(content, 1, True)
        add_row(content, 30)
    else:
        add_row(content, 1, True)

    inner = StackPanel()
    inner.Orientation = Orientation.Vertical

    msg_tb = TextBlock()
    msg_tb.Text = message
    msg_tb.Foreground = FG_SEC
    msg_tb.FontSize = 12
    msg_tb.TextWrapping = TextWrapping.Wrap
    msg_tb.Margin = Thickness(0, 0, 0, 14)
    inner.Children.Add(msg_tb)

    inp = TextBox()
    inp.FontSize = 13
    inp.Background = BG_INP
    inp.Foreground = FG_PRI
    inp.CaretBrush = GOLD
    inp.BorderBrush = GOLD
    inp.BorderThickness = Thickness(1)
    inp.Padding = Thickness(12, 10, 12, 10)
    inp.AcceptsReturn = True
    inp.TextWrapping = TextWrapping.Wrap
    inp.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
    inp.HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled
    inp.MinHeight = 130
    inp.MaxHeight = 300
    inp.Text = default if default else ""
    inner.Children.Add(inp)

    sv = ScrollViewer()
    sv.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
    sv.Content = inner
    place(content, sv, 0)

    if context:
        ctx_tb = TextBlock()
        ctx_tb.Text = context
        ctx_tb.Foreground = FG_DIM
        ctx_tb.FontSize = 10
        ctx_tb.TextWrapping = TextWrapping.Wrap
        ctx_tb.VerticalAlignment = VerticalAlignment.Center
        place(content, ctx_tb, 1)

    place(outer, content, 2)

    d2 = Border(); d2.Background = BORDER; d2.Height = 1
    place(outer, d2, 3)

    bottom = Grid()
    bottom.Background = BG_MID
    add_col(bottom, 1, True)
    add_col(bottom, 130)
    add_col(bottom, 8)
    add_col(bottom, 110)
    add_col(bottom, 16)

    hint_tb = label("Shift+Enter: new line  |  Enter: confirm  |  Esc: cancel",
                    size=10, color=FG_DIM)
    hint_tb.VerticalAlignment = VerticalAlignment.Center
    hint_tb.Margin = Thickness(16, 0, 0, 0)
    place(bottom, hint_tb, 0, 0)

    btn_ok = button("Confirm", gold=True, width=120, height=34)
    btn_ok.Margin = Thickness(0, 10, 0, 10)
    place(bottom, btn_ok, 0, 1)

    btn_cancel = button("Cancel", gold=False, width=100, height=34)
    btn_cancel.Margin = Thickness(0, 10, 0, 10)
    place(bottom, btn_cancel, 0, 3)

    place(outer, bottom, 4)

    def on_confirm(s, e):
        txt = inp.Text.strip() if inp.Text else ""
        if txt:
            result[0] = txt
        win.Close()

    def on_cancel(s, e):
        win.Close()

    def on_key(s, e):
        if e.Key == Key.Return and Keyboard.Modifiers != ModifierKeys.Shift:
            txt = inp.Text.strip() if inp.Text else ""
            if txt:
                result[0] = txt
            win.Close()
            e.Handled = True
        elif e.Key == Key.Escape:
            win.Close()

    btn_ok.Click += on_confirm
    btn_cancel.Click += on_cancel
    inp.KeyDown += on_key
    win.Loaded += lambda s, e: (inp.Focus(), Keyboard.Focus(inp),
                                setattr(inp, "CaretIndex", len(inp.Text) if inp.Text else 0))
    win.Content = outer
    win.ShowDialog()
    return result[0]


def switch_dialog(choices, message, title="Select"):
    """Dark tile-based choice dialog replacing CommandSwitchWindow. Returns selected string or None."""
    result = [None]
    n = len(choices)
    est_height = 44 + 1 + max(140, 52 * ((n + 1) // 2) + 80) + 1 + 54
    win = base_window(title, "", width=680, height=min(est_height, 520))

    outer = Grid()
    add_row(outer, 44)
    add_row(outer, 1)
    add_row(outer, 1, True)
    add_row(outer, 1)
    add_row(outer, 54)

    place(outer, title_bar("ClaudeRevit", title), 0)
    d1 = Border(); d1.Background = BORDER; d1.Height = 1
    place(outer, d1, 1)

    inner = StackPanel()
    inner.Orientation = Orientation.Vertical
    inner.Margin = Thickness(24, 16, 24, 0)

    msg_tb = TextBlock()
    msg_tb.Text = message
    msg_tb.Foreground = FG_SEC
    msg_tb.FontSize = 12
    msg_tb.TextWrapping = TextWrapping.Wrap
    msg_tb.Margin = Thickness(0, 0, 0, 16)
    inner.Children.Add(msg_tb)

    tiles = WrapPanel()
    tiles.Orientation = Orientation.Horizontal

    def _make_handler(choice):
        def _h(s, e):
            result[0] = choice
            win.Close()
        return _h

    for ch in choices:
        btn = Button()
        btn.Content = ch
        btn.FontSize = 12
        btn.Background = BG_CARD
        btn.Foreground = FG_PRI
        btn.BorderBrush = BORDER
        btn.BorderThickness = Thickness(1)
        btn.Padding = Thickness(16, 10, 16, 10)
        btn.Margin = Thickness(0, 0, 8, 8)
        btn.MinWidth = 160
        btn.MaxWidth = 290
        btn.Click += _make_handler(ch)
        tiles.Children.Add(btn)

    inner.Children.Add(tiles)

    sv = ScrollViewer()
    sv.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
    sv.Content = inner
    place(outer, sv, 2)

    d2 = Border(); d2.Background = BORDER; d2.Height = 1
    place(outer, d2, 3)

    bottom = Grid()
    bottom.Background = BG_MID
    add_col(bottom, 1, True)
    add_col(bottom, 110)
    add_col(bottom, 16)

    btn_cancel = button("Cancel", gold=False, width=100, height=34)
    btn_cancel.Margin = Thickness(0, 10, 0, 10)
    place(bottom, btn_cancel, 0, 1)
    place(outer, bottom, 4)

    def on_cancel(s, e):
        win.Close()

    def on_win_key(s, e):
        if e.Key == Key.Escape:
            win.Close()

    btn_cancel.Click += on_cancel
    win.KeyDown += on_win_key
    win.Content = outer
    win.ShowDialog()
    return result[0]


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
