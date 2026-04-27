# -*- coding: utf-8 -*-
"""
claude_client.py
Shared Claude API caller for all ClaudeRevit pyRevit scripts.
Model: claude-sonnet-4-6
"""

import os
import json
import sys

try:
    import requests
except ImportError:
    raise ImportError("'requests' not available. Install via pyRevit's bundled Python or pip.")

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config.json"
)


def _cfg():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def ask_claude(prompt, system=None, max_tokens=None):
    """
    Send a prompt to Claude and return the text response.
    Raises on API error so callers can handle gracefully.
    """
    cfg = _cfg()
    key = cfg.get("anthropic_api_key", "")
    if not key or key.startswith("YOUR_"):
        return "[ERROR] Anthropic API key not set in config.json"

    payload = {
        "model": cfg.get("model", "claude-sonnet-4-6"),
        "max_tokens": max_tokens or cfg.get("max_tokens", 4096),
        "messages": [{"role": "user", "content": prompt}]
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def strip_fences(code):
    """Remove markdown code fences Claude sometimes adds."""
    if "```" not in code:
        return code
    lines = code.split("\n")
    return "\n".join(l for l in lines if not l.strip().startswith("```"))


def exec_claude_code(code_str, context_dict):
    """
    Execute a string of Python code in the given context dict.
    Returns (success: bool, error: str or None)
    """
    import traceback
    try:
        exec(compile(code_str, "<claude>", "exec"), context_dict)
        return True, None
    except Exception:
        return False, traceback.format_exc()


def revit_exec_context(doc, uidoc, revit_module, DB_module, forms_module, output_obj):
    """
    Build a safe execution context dict for Claude-generated Revit code.
    Exposes all Autodesk.Revit.DB classes plus pyRevit helpers.
    """
    ctx = {
        "doc": doc,
        "uidoc": uidoc,
        "revit": revit_module,
        "DB": DB_module,
        "forms": forms_module,
        "output": output_obj,
        "__builtins__": __builtins__,
    }
    # Expose every DB class at top level so Claude can use XYZ, Line, Wall etc directly
    for name in dir(DB_module):
        if not name.startswith("_"):
            ctx[name] = getattr(DB_module, name)
    return ctx
