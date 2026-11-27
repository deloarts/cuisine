"""
Turns format dataclasses into JSON values and back, and describes them as
JSON Schema.

A format dataclass is frozen and keyword only, and its fields use a small
set of types: `str`, `int`, `float`, `bool`, `Any`, `Literal[...]`, another
format dataclass, `list[X]`, `dict[str, X]` and `X | None`. A field without
a default is required; every field added to a released version must have
one, so older documents stay readable. The `doc` entry of a field's
metadata becomes its description in the schema.

Reading ignores every key a dataclass does not declare, so a document from a
newer release of the same format version still reads. A wrong type or a
missing required field raises `FormatError` with the path of the value.
"""

import inspect
import types
from dataclasses import MISSING
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Any
from typing import Literal
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class FormatError(ValueError):
    """A document that does not have the shape its format version says."""


def to_json(value: Any) -> Any:
    """The value as plain JSON data, dataclass fields in declaration order."""
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_json(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, list | tuple):
        return [to_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    return value


def read[T](cls: type[T], data: Any) -> T:
    """`data` read as an instance of the format dataclass `cls`."""
    result: T = _read(cls, data, "$")
    return result


def _optional(tp: Any) -> Any | None:
    """X for `X | None`, None for any other type."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) != 1 or len(get_args(tp)) != 2:
            raise TypeError(f"Format fields support only `X | None` unions, not {tp}.")
        return args[0]
    return None


def _describe(value: Any) -> str:
    return "null" if value is None else type(value).__name__


def _read(tp: Any, value: Any, path: str) -> Any:
    if tp is Any:
        return value
    inner = _optional(tp)
    if inner is not None:
        return None if value is None else _read(inner, value, path)
    if is_dataclass(tp) and isinstance(tp, type):
        if not isinstance(value, dict):
            raise FormatError(f"{path} should be an object, not {_describe(value)}.")
        hints = get_type_hints(tp)
        values: dict[str, Any] = {}
        for f in fields(tp):
            if f.name in value:
                values[f.name] = _read(hints[f.name], value[f.name], f"{path}.{f.name}")
            elif f.default is MISSING and f.default_factory is MISSING:
                raise FormatError(f"{path} lacks the required field {f.name!r}.")
        return tp(**values)
    origin = get_origin(tp)
    if origin is Literal:
        if value not in get_args(tp) or isinstance(value, bool):
            allowed = ", ".join(repr(a) for a in get_args(tp))
            raise FormatError(f"{path} should be {allowed}, not {value!r}.")
        return value
    if origin is list:
        if not isinstance(value, list):
            raise FormatError(f"{path} should be a list, not {_describe(value)}.")
        (item,) = get_args(tp)
        return [_read(item, v, f"{path}[{i}]") for i, v in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise FormatError(f"{path} should be an object, not {_describe(value)}.")
        _, item = get_args(tp)
        return {str(k): _read(item, v, f"{path}.{k}") for k, v in value.items()}
    if tp is bool:
        if not isinstance(value, bool):
            raise FormatError(f"{path} should be true or false, not {_describe(value)}.")
        return value
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise FormatError(f"{path} should be a whole number, not {_describe(value)}.")
        return value
    if tp is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise FormatError(f"{path} should be a number, not {_describe(value)}.")
        return float(value)
    if tp is str:
        if not isinstance(value, str):
            raise FormatError(f"{path} should be a text, not {_describe(value)}.")
        return value
    raise TypeError(f"Format fields do not support the type {tp}.")


def _doc(cls: type) -> str | None:
    """The class docstring, unless it is the signature dataclass generates."""
    doc = inspect.getdoc(cls)
    if not doc or doc.startswith(f"{cls.__name__}("):
        return None
    return " ".join(doc.split())


def json_schema(root: type, *, schema_id: str, title: str) -> dict[str, Any]:
    """The JSON Schema (draft 2020-12) of the format dataclass `root`. Unknown
    properties are allowed everywhere, as readers ignore them."""
    defs: dict[str, dict[str, Any]] = {}

    def of(tp: Any) -> dict[str, Any]:
        if tp is Any:
            return {}
        inner = _optional(tp)
        if inner is not None:
            return {"anyOf": [of(inner), {"type": "null"}]}
        if is_dataclass(tp) and isinstance(tp, type):
            name = tp.__name__
            if name not in defs:
                defs[name] = {}
                hints = get_type_hints(tp)
                properties: dict[str, Any] = {}
                required: list[str] = []
                for f in fields(tp):
                    described = of(hints[f.name])
                    if f.metadata.get("doc"):
                        described = {"description": f.metadata["doc"], **described}
                    properties[f.name] = described
                    if f.default is MISSING and f.default_factory is MISSING:
                        required.append(f.name)
                body: dict[str, Any] = {"type": "object"}
                if doc := _doc(tp):
                    body["description"] = doc
                body["properties"] = properties
                if required:
                    body["required"] = required
                defs[name] = body
            return {"$ref": f"#/$defs/{name}"}
        origin = get_origin(tp)
        if origin is Literal:
            options = list(get_args(tp))
            return {"const": options[0]} if len(options) == 1 else {"enum": options}
        if origin is list:
            (item,) = get_args(tp)
            return {"type": "array", "items": of(item)}
        if origin is dict:
            _, item = get_args(tp)
            return {"type": "object", "additionalProperties": of(item)}
        simple = {str: "string", int: "integer", float: "number", bool: "boolean"}
        if tp in simple:
            return {"type": simple[tp]}
        raise TypeError(f"Format fields do not support the type {tp}.")

    of(root)
    top = defs.pop(root.__name__)
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "$id": schema_id,
        "title": title,
        **top,
        "$defs": dict(sorted(defs.items())),
    }
