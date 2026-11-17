
import collections.abc
import types
import typing
import json

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePath
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

# --------------------------------------------------------------------------- #
# A required list/dict (no default) with zero entries is flagged invalid, since
# an empty one is almost never intended (e.g. a required "subscriptions" list).
# --------------------------------------------------------------------------- #
REQUIRE_NONEMPTY_REQUIRED_COLLECTIONS = True

# Spec kinds
STR, INT, FLOAT, BOOL, ENUM, JSON = "str", "int", "float", "bool", "enum", "json"
MODEL, LIST, DICT, OPTIONAL = "model", "list", "dict", "optional"
INLINE_KINDS = {STR, INT, FLOAT, BOOL, ENUM, JSON}
# Scalar/leaf kinds whose "type changed" is decided by the kind alone.
PRIMITIVE_KINDS = {STR, INT, FLOAT, BOOL, ENUM, JSON}

# --------------------------------------------------------------------------- #
# Schema ("spec") built from type annotations
# --------------------------------------------------------------------------- #
class _Missing:
    """Sentinel: a required value the user hasn't provided yet."""

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = _Missing()
_ABSENT = object()


@dataclass
class Spec:
    kind: str
    model: type[BaseModel] | None = None
    fields: list["FieldSpec"] = field(default_factory=list)   # MODEL
    item: "Spec | None" = None                                # LIST / DICT / OPTIONAL
    choices: list = field(default_factory=list)               # ENUM
    enum_cls: type | None = None                              # ENUM (None for Literal)


@dataclass
class FieldSpec:
    name: str
    key: str                 # key used in the data (alias if one exists)
    spec: Spec
    required: bool
    description: str | None
    info: Any                # pydantic FieldInfo

    def initial(self) -> Any:
        """Initial editor state: the default if there is one, else 'blank'."""
        has_default, default = _field_default(self.info)
        if has_default:
            return from_value(self.spec, default)
        return blank_state(self.spec)


def _field_default(info) -> tuple[bool, Any]:
    if info.default_factory is not None:
        try:
            return True, info.default_factory()
        except TypeError:  # pydantic >= 2.10: factory may take validated data
            try:
                return True, info.default_factory({})
            except Exception:
                return False, None
    if info.default is not PydanticUndefined:
        return True, info.default
    return False, None


_LIST_ORIGINS = (list, set, frozenset, collections.abc.Sequence,
                 collections.abc.MutableSequence, collections.abc.Set)
_DICT_ORIGINS = (dict, collections.abc.Mapping, collections.abc.MutableMapping)


def build_spec(annotation: Any, _stack: tuple = ()) -> Spec:
    ann = annotation
    while get_origin(ann) is typing.Annotated:
        ann = get_args(ann)[0]
    origin, args = get_origin(ann), get_args(ann)

    if ann is Any:
        return Spec(JSON)

    if origin in (Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == len(args):          # a real union -> edit as JSON
            return Spec(JSON)
        inner = build_spec(non_none[0], _stack) if len(non_none) == 1 else Spec(JSON)
        return Spec(OPTIONAL, item=inner)

    if origin is Literal:
        return Spec(ENUM, choices=list(args))

    if origin in _LIST_ORIGINS:
        return Spec(LIST, item=build_spec(args[0], _stack) if args else Spec(JSON))
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return Spec(LIST, item=build_spec(args[0], _stack))
        return Spec(JSON)

    if origin in _DICT_ORIGINS:
        if len(args) == 2 and args[0] is str:
            return Spec(DICT, item=build_spec(args[1], _stack))
        return Spec(JSON)

    if isinstance(ann, type):
        if issubclass(ann, Enum):
            return Spec(ENUM, choices=list(ann), enum_cls=ann)
        if issubclass(ann, BaseModel):
            if ann in _stack:                   # recursive model -> JSON fallback
                return Spec(JSON)
            spec = Spec(MODEL, model=ann)
            for name, info in ann.model_fields.items():
                spec.fields.append(FieldSpec(
                    name=name,
                    key=info.alias or name,
                    spec=build_spec(info.annotation, _stack + (ann,)),
                    required=info.is_required(),
                    description=info.description,
                    info=info,
                ))
            return spec
        if issubclass(ann, bool):               # before int: bool is an int subclass
            return Spec(BOOL)
        if issubclass(ann, int):
            return Spec(INT)
        if issubclass(ann, float):
            return Spec(FLOAT)
        if issubclass(ann, (str, PurePath)):
            return Spec(STR)

    return Spec(JSON)


# --------------------------------------------------------------------------- #
# Editor state helpers
#
#    MODEL    -> dict[field name, state]
#    LIST     -> list[state]
#    DICT     -> list[[key, state]]      (ordered, keys editable)
#    OPTIONAL -> None | state
#    ENUM     -> enum member / literal value / MISSING
#    JSON     -> str (JSON text) / MISSING
#    STR/INT/FLOAT/BOOL -> value / MISSING
# --------------------------------------------------------------------------- #
def blank_state(spec: Spec, filled: bool = False) -> Any:
    """State for a value with no default. Primitives are MISSING (rendered red)
    unless ``filled`` (used when the user ticks an Optional on)."""
    k = spec.kind
    if k == MODEL:
        return {f.name: f.initial() for f in spec.fields}
    if k in (LIST, DICT):
        return []
    if k == OPTIONAL:
        return None
    if not filled:
        return MISSING
    if k == STR:
        return ""
    if k == INT:
        return 0
    if k == FLOAT:
        return 0.0
    if k == BOOL:
        return False
    if k == JSON:
        return "null"
    return spec.choices[0] if spec.choices else MISSING


def from_value(spec: Spec, value: Any) -> Any:
    """Convert a real Python value (a default, or a loaded model) to editor state."""
    k = spec.kind
    try:
        if k == MODEL:
            state = {}
            for f in spec.fields:
                if isinstance(value, dict):
                    v = value.get(f.key, value.get(f.name, _ABSENT))
                else:
                    v = getattr(value, f.name, _ABSENT)
                state[f.name] = f.initial() if v is _ABSENT else from_value(f.spec, v)
            return state
        if k == LIST:
            assert spec.item is not None
            return [from_value(spec.item, v) for v in value]
        if k == DICT:
            assert spec.item is not None
            return [[str(key), from_value(spec.item, v)] for key, v in value.items()]
        if k == OPTIONAL:
            assert spec.item is not None
            return None if value is None else from_value(spec.item, value)
        if k == ENUM:
            if value in spec.choices:
                return value
            if spec.enum_cls is not None:
                return spec.enum_cls(value)
            return MISSING
        if k == JSON:
            return json.dumps(value, default=str)
        if value is None:
            return MISSING
        return {STR: str, INT: int, FLOAT: float, BOOL: bool}[k](value)
    except Exception:
        return MISSING


def to_data(spec: Spec, state: Any) -> Any:
    """Convert editor state to plain data suitable for ``model_validate``."""
    k = spec.kind
    if k == MODEL:
        return {f.key: to_data(f.spec, state[f.name])
                for f in spec.fields if state[f.name] is not MISSING}
    if k == LIST:
        assert spec.item is not None
        return [to_data(spec.item, s) for s in state]
    if k == DICT:
        assert spec.item is not None
        return {key: to_data(spec.item, s) for key, s in state}
    if k == OPTIONAL:
        assert spec.item is not None
        return None if state is None else to_data(spec.item, state)
    if k == ENUM:
        return state.value if isinstance(state, Enum) else state
    if k == JSON:
        return json.loads(state)
    return state


def is_invalid(spec: Spec, state: Any, required: bool = True) -> bool:
    """True if this value, or anything beneath it, is a missing/bad required value."""
    k = spec.kind
    if k == MODEL:
        return any(is_invalid(f.spec, state[f.name], f.required) for f in spec.fields)
    if k == LIST:
        if required and REQUIRE_NONEMPTY_REQUIRED_COLLECTIONS and not state:
            return True
        assert spec.item is not None
        return any(is_invalid(spec.item, s, True) for s in state)
    if k == DICT:
        if required and REQUIRE_NONEMPTY_REQUIRED_COLLECTIONS and not state:
            return True
        keys = [key for key, _ in state]
        if any(key == "" or keys.count(key) > 1 for key in keys):
            return True
        assert spec.item is not None
        return any(is_invalid(spec.item, s, True) for _, s in state)
    if k == OPTIONAL:
        assert spec.item is not None
        return state is not None and is_invalid(spec.item, state, True)
    if state is MISSING:
        return True
    if k == STR:
        return required and state == ""
    if k == JSON:
        try:
            json.loads(state)
            return False
        except Exception:
            return True
    return False
