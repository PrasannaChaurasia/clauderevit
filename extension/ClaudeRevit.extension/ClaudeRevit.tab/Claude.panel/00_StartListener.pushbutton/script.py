# -*- coding: utf-8 -*-
__title__ = "Start\nListener"
__doc__ = "Start the Claude listener. Revit will watch for commands from Claude and execute them automatically."

import sys
import os
import json
import clr

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from command_dispatcher import dispatch, BRIDGE_CMD, BRIDGE_RESULT

# ──────────────────────────────────────────────
# ExternalEventHandler — runs inside valid API context
# ──────────────────────────────────────────────
class ClaudeExternalEventHandler(IExternalEventHandler):

    def Execute(self, uiapp):
        doc = uiapp.ActiveUIDocument.Document
        if not doc:
            return

        if not os.path.exists(BRIDGE_CMD):
            return

        # Read command
        try:
            with open(BRIDGE_CMD, "r") as f:
                raw = f.read().strip()
            if not raw or raw == "{}":
                return
            data = json.loads(raw)
        except Exception as e:
            _write_result({"status": "error", "message": "Failed to read command.json: {}".format(str(e))})
            _clear_command()
            return

        # Clear command file immediately to prevent re-execution
        _clear_command()

        # Dispatch
        try:
            result = dispatch(doc, data)
        except Exception as e:
            result = {"status": "error", "message": str(e)}

        _write_result(result)

    def GetName(self):
        return "ClaudeCommandHandler"


def _write_result(result):
    try:
        with open(BRIDGE_RESULT, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        pass  # Can't do much if result write fails


def _clear_command():
    try:
        with open(BRIDGE_CMD, "w") as f:
            f.write("{}")
    except:
        pass


# ──────────────────────────────────────────────
# Idling handler — polls bridge, raises ExternalEvent
# ──────────────────────────────────────────────
_handler   = ClaudeExternalEventHandler()
_ext_event = ExternalEvent.Create(_handler)


def _on_idling(sender, args):
    try:
        if not os.path.exists(BRIDGE_CMD):
            return
        with open(BRIDGE_CMD, "r") as f:
            raw = f.read().strip()
        if raw and raw != "{}":
            _ext_event.Raise()
    except:
        pass


# ──────────────────────────────────────────────
# Register Idling event
# ──────────────────────────────────────────────
try:
    __revit__.Idling += _on_idling
    forms.alert(
        "Claude Listener is ACTIVE\n\n"
        "Revit is now watching:\n{}\n\n"
        "Commands from Claude will execute automatically.\n"
        "Results written to:\n{}".format(BRIDGE_CMD, BRIDGE_RESULT),
        title="Claude Listener Started",
        warn_icon=False
    )
except Exception as e:
    forms.alert("Failed to start listener:\n{}".format(str(e)), title="Error")
