# -*- coding: utf-8 -*-
__title__ = "Start\nListener"
__doc__ = "Start the Claude listener. Revit watches for commands from Claude Desktop."

import sys, os, json, time

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from command_dispatcher import dispatch, BRIDGE_CMD, BRIDGE_RESULT


class ClaudeExternalEventHandler(IExternalEventHandler):

    def Execute(self, uiapp):
        doc = uiapp.ActiveUIDocument.Document
        if not doc or not os.path.exists(BRIDGE_CMD):
            return
        try:
            with open(BRIDGE_CMD, "r") as f:
                raw = f.read().strip()
            if not raw or raw == "{}":
                return
            data = json.loads(raw)
        except Exception as e:
            _write_result({"status": "error", "message": "Read error: {}".format(str(e))})
            _clear_command()
            return

        _clear_command()

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
    except Exception:
        pass


def _clear_command():
    try:
        with open(BRIDGE_CMD, "w") as f:
            f.write("{}")
    except Exception:
        pass


_handler    = ClaudeExternalEventHandler()
_ext_event  = ExternalEvent.Create(_handler)
_last_check = [0.0]
_INTERVAL   = 0.5   # poll at most twice per second — prevents Revit lag


def _on_idling(sender, args):
    now = time.time()
    if now - _last_check[0] < _INTERVAL:
        return
    _last_check[0] = now
    try:
        if not os.path.exists(BRIDGE_CMD):
            return
        with open(BRIDGE_CMD, "r") as f:
            raw = f.read().strip()
        if raw and raw != "{}":
            _ext_event.Raise()
    except Exception:
        pass


# Ensure bridge directory and seed files exist
bridge_dir = os.path.dirname(BRIDGE_CMD)
try:
    if not os.path.exists(bridge_dir):
        os.makedirs(bridge_dir)
    for fpath in [BRIDGE_CMD, BRIDGE_RESULT]:
        if not os.path.exists(fpath):
            with open(fpath, "w") as f:
                f.write("{}")
except Exception as e:
    forms.alert(
        "Cannot create bridge folder:\n{}\n\n{}".format(bridge_dir, str(e)),
        title="Listener Error"
    )
    script.exit()

try:
    __revit__.Idling += _on_idling
    forms.alert(
        "Claude Listener is ACTIVE\n\n"
        "Revit checks for commands every 0.5 seconds.\n\n"
        "Commands : {}\n"
        "Results  : {}\n\n"
        "Use Claude Command button or Claude Desktop to send commands.".format(
            BRIDGE_CMD, BRIDGE_RESULT),
        title="Listener Started",
    )
except Exception as e:
    forms.alert("Failed to start listener:\n{}".format(str(e)), title="Error")
