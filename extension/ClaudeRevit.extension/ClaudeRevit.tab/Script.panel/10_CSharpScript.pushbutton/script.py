# -*- coding: utf-8 -*-
__title__ = "C# Script"
__doc__ = "Write and execute C# code inside Revit using Roslyn in-memory compilation. Full .NET and Revit API access. Claude can generate the code from a description."

import sys, os, clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("Microsoft.CSharp")
clr.AddReference("System.Core")

from System.Windows import Thickness, HorizontalAlignment, VerticalAlignment, FontWeights, TextWrapping
from System.Windows.Controls import (Grid, StackPanel, Border, TextBlock, TextBox, Button,
                                      Orientation, ScrollBarVisibility, CornerRadius)
from System.Windows.Media import FontFamily
from System.Windows.Input import Keyboard, Key, ModifierKeys
from System import Type, Activator
from System.Reflection import Assembly

from wpf_helper import (base_window, title_bar, add_row, add_col, place,
                         label, button, pill,
                         GOLD, BG_MID, BG_CARD, BG_INP, BG_DARK,
                         FG_PRI, FG_SEC, FG_DIM, BORDER, rgb)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, Level, Wall, ViewSheet
from claude_client import ask_claude, strip_fences

doc   = revit.doc
uidoc = revit.uidoc
output = script.get_output()

try:
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    model_ctx = "{}  |  Levels:[{}]".format(doc.Title, ", ".join(l.Name for l in levels))
except Exception:
    model_ctx = doc.Title

STARTER = """\
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using System.Collections.Generic;
using System.Linq;

public class RevitScript
{
    public static string Execute(Document doc, UIDocument uidoc)
    {
        // Example: count levels and return a summary
        var levels = new FilteredElementCollector(doc)
            .OfClass(typeof(Level))
            .Cast<Level>()
            .OrderBy(l => l.Elevation)
            .ToList();

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Model: {doc.Title}");
        sb.AppendLine($"Levels ({levels.Count}):");
        foreach (var lvl in levels)
            sb.AppendLine($"  {lvl.Name}  @ {lvl.Elevation * 0.3048:F2}m");

        return sb.ToString();
    }
}
"""


def compile_and_run(cs_code, doc_obj, uidoc_obj):
    """Compile C# code in memory using CSharpCodeProvider and invoke Execute."""
    try:
        from System.CodeDom.Compiler import CompilerParameters
        from Microsoft.CSharp import CSharpCodeProvider

        provider = CSharpCodeProvider()
        params   = CompilerParameters()
        params.GenerateInMemory      = True
        params.GenerateExecutable    = False
        params.TreatWarningsAsErrors = False

        # Add required assemblies
        import System
        params.ReferencedAssemblies.Add("System.dll")
        params.ReferencedAssemblies.Add("System.Core.dll")
        params.ReferencedAssemblies.Add("System.Linq.dll")

        # Add Revit API assemblies
        revit_api = Assembly.GetAssembly(Type.GetType("Autodesk.Revit.DB.Document, RevitAPI"))
        if revit_api:
            params.ReferencedAssemblies.Add(revit_api.Location)

        revit_ui = Assembly.GetAssembly(Type.GetType("Autodesk.Revit.UI.UIDocument, RevitAPIUI"))
        if revit_ui:
            params.ReferencedAssemblies.Add(revit_ui.Location)

        results = provider.CompileAssemblyFromSource(params, cs_code)

        if results.Errors.HasErrors:
            errors = []
            for err in results.Errors:
                if not err.IsWarning:
                    errors.append("Line {}: {}".format(err.Line, err.ErrorText))
            return False, "Compilation errors:\n" + "\n".join(errors), None

        asm  = results.CompiledAssembly
        tp   = asm.GetType("RevitScript")
        meth = tp.GetMethod("Execute")
        result = meth.Invoke(None, [doc_obj, uidoc_obj])
        return True, None, str(result) if result else "(Script returned no output)"

    except Exception as e:
        import traceback
        return False, traceback.format_exc(), None


def show_editor():
    result = [None]
    action = ["run"]

    win = base_window("C# Script Editor", doc.Title, width=900, height=660)

    outer = Grid()
    add_row(outer, 44)
    add_row(outer, 1)
    add_row(outer, 36)
    add_row(outer, 1, True)
    add_row(outer, 1)
    add_row(outer, 48)

    place(outer, title_bar(doc.Title, "C# Script"), 0)

    div1 = Border(); div1.Background = BORDER; div1.Height = 1
    place(outer, div1, 1)

    toolbar = StackPanel()
    toolbar.Orientation = Orientation.Horizontal
    toolbar.Background  = BG_MID
    toolbar.Margin      = Thickness(12, 4, 12, 4)
    toolbar.Children.Add(pill("CSharpCodeProvider  |  Full .NET + Revit API", fg=FG_DIM, bg=BG_CARD))
    place(outer, toolbar, 2)

    editor = TextBox()
    editor.FontFamily = FontFamily("Consolas")
    editor.FontSize   = 12
    editor.Background = rgb(14, 14, 20)
    editor.Foreground = FG_PRI
    editor.CaretBrush = GOLD
    editor.BorderThickness = Thickness(0)
    editor.Padding    = Thickness(16, 12, 16, 12)
    editor.AcceptsReturn = True
    editor.AcceptsTab    = True
    editor.TextWrapping  = TextWrapping.NoWrap
    editor.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
    editor.HorizontalScrollBarVisibility = ScrollBarVisibility.Auto
    editor.Text = STARTER
    place(outer, editor, 3)

    div2 = Border(); div2.Background = BORDER; div2.Height = 1
    place(outer, div2, 4)

    bottom = Grid()
    bottom.Background = BG_MID
    add_col(bottom, 1, True)
    add_col(bottom, 140)
    add_col(bottom, 8)
    add_col(bottom, 180)
    add_col(bottom, 8)
    add_col(bottom, 120)

    hint = label("Ctrl+Enter: Compile & Run  |  Ctrl+G: Ask Claude", size=10, color=FG_DIM)
    hint.VerticalAlignment = VerticalAlignment.Center
    hint.Margin = Thickness(16, 0, 0, 0)
    place(bottom, hint, 0, 0)

    btn_gen    = button("Ask Claude", gold=False, width=130, height=32)
    btn_gen.Margin = Thickness(0, 8, 0, 8)
    place(bottom, btn_gen, 0, 1)

    btn_run    = button("Compile & Run", gold=True, width=170, height=32)
    btn_run.Margin = Thickness(0, 8, 0, 8)
    place(bottom, btn_run, 0, 3)

    btn_cancel = button("Close", gold=False, width=110, height=32)
    btn_cancel.Margin = Thickness(0, 8, 16, 8)
    place(bottom, btn_cancel, 0, 5)

    place(outer, bottom, 5)

    def on_run(s, e):
        result[0] = editor.Text
        action[0] = "run"
        win.Close()

    def on_gen(s, e):
        result[0] = editor.Text
        action[0] = "generate"
        win.Close()

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

    def on_loaded(s, e):
        editor.Focus(); Keyboard.Focus(editor)
        editor.CaretIndex = len(editor.Text)

    win.Loaded += on_loaded
    win.Content = outer
    win.ShowDialog()
    return result[0], action[0]


code_text, user_action = show_editor()
if not code_text or not code_text.strip():
    script.exit()

if user_action == "generate":
    description = forms.ask_for_string(
        prompt="Describe what you want the C# script to do in Revit:",
        title="Ask Claude — C# Generation",
        default=""
    )
    if not description:
        script.exit()

    SYSTEM = """\
You are a Revit API C# expert. Write a complete C# class for in-memory compilation via CSharpCodeProvider.

REQUIRED STRUCTURE:
  using Autodesk.Revit.DB;
  using Autodesk.Revit.UI;
  // other using statements

  public class RevitScript
  {
      public static string Execute(Document doc, UIDocument uidoc)
      {
          // your code here
          // Use doc directly — no need to get it from anywhere
          // Wrap changes in Transaction t = new Transaction(doc, "name"); t.Start(); ...; t.Commit();
          return "result summary string";
      }
  }

RULES:
  - Class must be named exactly RevitScript
  - Method must be named exactly Execute with signature (Document doc, UIDocument uidoc) returning string
  - Use full Revit API — FilteredElementCollector, Transaction, XYZ, Level, Wall, etc.
  - Return a summary string describing what was done
  - Return ONLY the C# code. No explanation. No markdown.

MODEL: """ + model_ctx

    output.print_md("# C# Script — Generating...")
    try:
        code_text = strip_fences(ask_claude(description, system=SYSTEM, max_tokens=1500))
    except Exception as e:
        forms.alert("Claude API error:\n{}".format(str(e)), title="Error")
        script.exit()

    output.print_md("**Generated C# code:**")
    output.print_code(code_text)
    go = forms.alert("Compile and run this C# code?", title="Run?", cancel=True)
    if not go:
        script.exit()

output.print_md("# C# Script — Compiling...")
ok, err, result_str = compile_and_run(code_text, doc, uidoc)

if ok:
    output.print_md("**Result:**")
    output.print_md("```\n{}\n```".format(result_str))
    forms.alert("Script completed.\n\n{}".format(result_str[:500]), title="C# Script")
else:
    output.print_md("**Compilation / Runtime Error:**\n```\n{}\n```".format(err))
    forms.alert("Error:\n\n{}".format(err[:600]), title="C# Script Error")
