"""
tool_compiler.py
================
Generates OpenAI/Groq function-calling schemas from plain Python functions.

Adding a workspace capability means writing one typed function with a docstring.
The schema follows from the signature, so there is no second hand-maintained
JSON blob per tool to drift out of sync with the code.

Kept free of heavy imports (no google-adk, no network clients, no API keys) so
the compiler can be tested on its own — see test_tool_compiler.py.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Union, get_args, get_origin

try:  # Python 3.10+: the `int | None` spelling produces types.UnionType
    from types import UnionType
except ImportError:  # pragma: no cover
    UnionType = ()


def json_type(annotation: Any) -> str:
    """Map a Python annotation to its JSON Schema type name.

    Optional[X] and `X | None` need unwrapping first: an equality test against
    `int` fails for a Union, so those parameters silently compiled to "string"
    and the model was told a number was text.
    """
    if annotation is inspect.Parameter.empty:
        return "string"

    origin = get_origin(annotation)
    if origin is Union or (UnionType and origin is UnionType):
        members = [a for a in get_args(annotation) if a is not type(None)]
        if not members:
            return "string"
        annotation = members[0]
        origin = get_origin(annotation)

    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is list or origin is list:
        return "array"
    if annotation is dict or origin is dict:
        return "object"
    return "string"


def compile_groq_tools(functions: list[Callable]) -> tuple[list[dict], dict[str, Callable]]:
    """Compile functions into (tool schemas, name -> function map).

    A parameter with no default is required; one with a default is optional.
    `self`/`cls` are skipped so bound methods compile correctly.
    """
    schema: list[dict] = []
    function_map: dict[str, Callable] = {}

    for func in functions:
        sig = inspect.signature(func)
        params: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            # *args / **kwargs have no fixed schema representation.
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue

            params["properties"][name] = {"type": json_type(param.annotation)}
            if param.default is inspect.Parameter.empty:
                params["required"].append(name)

        schema.append({
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": (func.__doc__ or "Executes a workspace action.").strip(),
                "parameters": params,
            },
        })
        function_map[func.__name__] = func

    return schema, function_map
