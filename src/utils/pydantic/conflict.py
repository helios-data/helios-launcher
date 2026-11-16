# --------------------------------------------------------------------------- #
# Part 4: recursive conflict resolution (merge last_run.json into the new schema)
#
# Rules, applied against the *new* schema built from the current config.py:
#   1. Field in last_run but not in config.py  -> dropped (handled by only
#      walking the schema's fields).
#   2. Field in config.py but not in last_run  -> use the schema default.
#   3. Field in both but now a different primitive type -> use the schema
#      default (old value discarded).
#   4. Field in both and it is a complex type  -> recurse, keeping as much of
#      the old value as still fits the new shape.
# --------------------------------------------------------------------------- #
# Sentinel returned by a primitive/enum merge when the old value is discarded
# (rule 3). The owning MODEL field turns this into the field's default, so that
# "use the default from config.py" honors per-field defaults, which live on the
# FieldSpec, not on the Spec.

import json
from typing import Any
from src.utils.pydantic.spec import (
    Spec, FieldSpec, blank_state,
    MODEL, LIST, DICT, OPTIONAL, JSON, ENUM,
    BOOL, INT, FLOAT, STR
)

_DISCARD = object()


def merge_value(spec: Spec, old: Any, has_old: bool) -> Any:
    """Return editor state for ``spec``, reusing ``old`` (a plain JSON value from
    last_run.json) wherever it still fits the new schema, else falling back to
    the schema's blank/default state. For a MODEL field whose old value is
    discarded, the owning MODEL substitutes that field's default (see
    ``_merge_field``).
    ``has_old`` distinguishes "no value was present" from "the value was JSON
    null"; when False we always start from the schema's own blank state.
    """
    result = _merge(spec, old, has_old)
    return blank_state(spec) if result is _DISCARD else result


def _merge_field(f: "FieldSpec", old: Any, present: bool) -> Any:
    """Merge one model field. Rule 2 (field absent from last_run) and rule 3
    (value discarded) both fall back to the field's own default via
    ``f.initial()``."""
    if not present:
        return f.initial()                       # rule 2: field added -> default
    result = _merge(f.spec, old, True)
    if result is _DISCARD:
        return f.initial()                       # rule 3: discarded -> field default
    return result


def _merge(spec: Spec, old: Any, has_old: bool) -> Any:
    """Core merge. May return ``_DISCARD`` to signal the caller should fall back
    to a default (field default if inside a MODEL, else blank_state)."""
    k = spec.kind

    if not has_old:
        return blank_state(spec)

    if k == MODEL:
        # Rule 1 is implicit: we only iterate the schema's fields, so any key in
        # ``old`` that the schema dropped is ignored.
        old_is_map = isinstance(old, dict)
        state: dict = {}
        for f in spec.fields:
            present = old_is_map and (f.key in old or f.name in old)
            child = (old[f.key] if (present and f.key in old)
                     else old[f.name]) if present else None
            state[f.name] = _merge_field(f, child, present)
        return state

    if k == LIST:
        assert spec.item is not None
        if not isinstance(old, list):
            return blank_state(spec)                                # rule 3 (shape changed)
        # Per element: a discarded element falls back to the item's blank state.
        return [merge_value(spec.item, v, True) for v in old]       # rule 4 per element

    if k == DICT:
        assert spec.item is not None
        if not isinstance(old, dict):
            return blank_state(spec)                                # rule 3 (shape changed)
        return [[str(key), merge_value(spec.item, v, True)]         # rule 4 per value
                for key, v in old.items()]

    if k == OPTIONAL:
        assert spec.item is not None
        if old is None:
            return None
        inner = merge_value(spec.item, old, True)
        return inner

    if k == JSON:
        # Free-form: keep whatever was there as its JSON text.
        try:
            return json.dumps(old, default=str)
        except Exception:
            return _DISCARD

    if k == ENUM:
        if old in spec.choices:
            return old
        if spec.enum_cls is not None:
            try:
                return spec.enum_cls(old)
            except Exception:
                return _DISCARD                                     # rule 3 (not a valid member)
        return _DISCARD

    # Remaining primitives: STR / INT / FLOAT / BOOL.
    # Rule 3: a primitive kind only accepts a matching JSON primitive type.
    if _primitive_matches(k, old):
        return old
    return _DISCARD


def _primitive_matches(kind: str, value: Any) -> bool:
    """True if ``value`` (from JSON) is already the right primitive type for
    ``kind``. bool is checked before int because ``bool`` is an ``int`` subclass
    in Python, and we must not silently treat True/False as an int value."""
    if value is None:
        return False
    if kind == BOOL:
        return isinstance(value, bool)
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == FLOAT:
        # JSON has no int/float distinction; accept an int for a float field.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == STR:
        return isinstance(value, str)
    return False