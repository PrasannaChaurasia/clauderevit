# -*- coding: utf-8 -*-
__title__ = "Stop\nListener"
__doc__ = "Stop the Claude listener. Revit will no longer watch for commands."

import sys
import os

_lib = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "lib"))
sys.path.insert(0, _lib)

from pyrevit import forms

# The Idling handler was registered in a different script instance.
# Best we can do from here is clear the bridge and inform the user
# to reload pyRevit to fully stop the event loop.

BRIDGE_CMD = r"C:\tools\revit-bridge\command.json"

try:
    with open(BRIDGE_CMD, "w") as f:
        f.write("{}")
except:
    pass

forms.alert(
    "Bridge cleared.\n\n"
    "To fully stop the listener, reload pyRevit:\n"
    "pyRevit tab → pyRevit → Reload\n\n"
    "This unregisters all Idling handlers.",
    title="Claude Listener",
)
