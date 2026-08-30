"""
test_tool_compiler.py
=====================
Tests for the dynamic schema compiler.

Runs with no API keys, no network and no google-adk install, which is the point
of keeping tool_compiler.py free of heavy imports.

    python test_tool_compiler.py
    python -m pytest test_tool_compiler.py -q
"""

import sys
from typing import Optional

from tool_compiler import compile_groq_tools, json_type


# --- sample tools, standing in for the real integrations -------------------

def send_message(channel_id: str, text: str) -> dict:
    """Post a message to a channel."""
    return {"ok": True}


def get_recent_messages(channel_id: str, limit: int = 50) -> list:
    """Pull recent messages from a channel."""
    return []


def sync_inventory(base_id: str, fields: dict, dry_run: bool = False) -> dict:
    """Patch record fields."""
    return {}


def report(base_id: str, filter_by_formula: Optional[str] = None, page: int | None = None) -> list:
    """Fetch rows, optionally filtered."""
    return []


def undocumented(x):
    return x


def _fn(schema, name):
    return next(s["function"] for s in schema if s["function"]["name"] == name)


# --- type mapping ----------------------------------------------------------

def test_scalar_types_map_correctly():
    assert json_type(str) == "string"
    assert json_type(int) == "integer"
    assert json_type(float) == "number"
    assert json_type(bool) == "boolean"
    assert json_type(list) == "array"
    assert json_type(dict) == "object"


def test_optional_unwraps_instead_of_defaulting_to_string():
    """The bug this helper exists for: Optional[int] is an integer, not text."""
    assert json_type(Optional[int]) == "integer"
    assert json_type(Optional[str]) == "string"


def test_pep604_union_unwraps():
    assert json_type(int | None) == "integer"
    assert json_type(dict | None) == "object"


def test_unannotated_parameter_defaults_to_string():
    assert json_type(__import__("inspect").Parameter.empty) == "string"


# --- schema shape ----------------------------------------------------------

def test_every_function_produces_one_tool():
    schema, fmap = compile_groq_tools([send_message, get_recent_messages])
    assert len(schema) == 2
    assert set(fmap) == {"send_message", "get_recent_messages"}
    assert all(s["type"] == "function" for s in schema)


def test_required_tracks_absence_of_a_default():
    schema, _ = compile_groq_tools([get_recent_messages])
    fn = _fn(schema, "get_recent_messages")
    assert fn["parameters"]["required"] == ["channel_id"]
    assert fn["parameters"]["properties"]["limit"]["type"] == "integer"


def test_dict_parameter_compiles_to_object():
    schema, _ = compile_groq_tools([sync_inventory])
    props = _fn(schema, "sync_inventory")["parameters"]["properties"]
    assert props["fields"]["type"] == "object"
    assert props["dry_run"]["type"] == "boolean"


def test_optional_parameters_are_typed_and_not_required():
    schema, _ = compile_groq_tools([report])
    fn = _fn(schema, "report")
    assert fn["parameters"]["required"] == ["base_id"]
    assert fn["parameters"]["properties"]["filter_by_formula"]["type"] == "string"
    # Would have been "string" before Optional unwrapping.
    assert fn["parameters"]["properties"]["page"]["type"] == "integer"


def test_docstring_becomes_the_description():
    schema, _ = compile_groq_tools([send_message])
    assert _fn(schema, "send_message")["description"] == "Post a message to a channel."


def test_missing_docstring_gets_a_fallback():
    schema, _ = compile_groq_tools([undocumented])
    assert _fn(schema, "undocumented")["description"]


def test_function_map_dispatches_to_the_real_callable():
    _, fmap = compile_groq_tools([send_message])
    assert fmap["send_message"]("C1", "hi") == {"ok": True}


def test_compiles_the_real_toolset_if_importable():
    """Best-effort check against the actual integrations."""
    try:
        from Slack import list_channels, get_history, send_message as slack_send
    except Exception:
        return  # credentials or requests missing; the unit tests above still stand
    schema, fmap = compile_groq_tools([list_channels, get_history, slack_send])
    assert len(schema) == 3
    for s in schema:
        assert s["function"]["name"]
        assert isinstance(s["function"]["parameters"]["properties"], dict)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {name}  {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed.")
    sys.exit(1 if failed else 0)
