"""
Per-repo pydantic configuration: loading a repo's ``config.py``, building an
editor schema from it, merging a previous ``last_run.json`` against a changed
schema, and validating the result.
This module is UI-free. The ImGui editor (``interface/components/config_editor.py``)
and the launcher wiring (``docker.py`` / ``interface/main.py``) both build on it.
Cache layout (survives ``tmp/`` cleanup)::
    cache/<repo_name>/config.py       # copy of the repo's config.py
    cache/<repo_name>/last_run.json   # last saved, schema-valid config
NOTE: a repo's ``config.py`` is *executed* to load it. Only point this at repos
you already trust enough to build and run.
"""
from __future__ import annotations

import collections.abc
import importlib.util
import json
import os
import shutil
import sys
import types
import typing
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from config.settings import (
    ROOT,
    CONFIG_CACHE_FOLDER,
    CONFIG_PY_NAME,
    REPO_CONFIG_RELPATH,
    LAST_RUN_NAME,
    sanitize_image_name,
)

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
# Cache paths
# --------------------------------------------------------------------------- #
def repo_cache_key(repo_name: str) -> str:
    """Folder-safe key for a repo. Reuses the image-name sanitizer so the key
    is stable and free of spaces/uppercase."""
    return sanitize_image_name(repo_name)


def cache_dir(repo_name: str) -> Path:
    return Path(ROOT) / CONFIG_CACHE_FOLDER / repo_cache_key(repo_name)


def cached_config_py_path(repo_name: str) -> Path:
    return cache_dir(repo_name) / CONFIG_PY_NAME


def cached_last_run_path(repo_name: str) -> Path:
    return cache_dir(repo_name) / LAST_RUN_NAME


def has_cached_config(repo_name: str) -> bool:
    return cached_config_py_path(repo_name).is_file()


def sync_cached_config_from_repo(repo_name: str, repo_root: Path) -> bool:
    """Called after a clone: copy ``<repo_root>/src/helios_pydantic_config.py``
    into the cache if it exists, or delete the cache entirely if it no longer
    does.
    Returns True if the repo has a pydantic config (and it is now cached).
    """
    src = Path(repo_root) / REPO_CONFIG_RELPATH
    dst = cached_config_py_path(repo_name)
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        return True
    # The config was removed from the repo: drop the whole cache for this repo
    # so we don't keep a stale config / last_run.json around.
    if cache_dir(repo_name).exists():
        shutil.rmtree(cache_dir(repo_name), ignore_errors=True)
    return False


# --------------------------------------------------------------------------- #
# Loading the Config class from a file path
# --------------------------------------------------------------------------- #
def load_config_class(path: str | Path, class_name: str = "Config") -> type[BaseModel]:
    """Import ``path`` as an isolated module and return ``class_name`` from it."""
    path = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    module_name = f"_dyn_config_{abs(hash(path))}"
    sys.modules.pop(module_name, None)  # force a fresh import on every load

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    # pydantic resolves forward refs through sys.modules[cls.__module__]
    sys.modules[module_name] = module

    # Appended (not prepended) so the repo can't shadow the launcher's modules.
    repo_dir = os.path.dirname(path)
    sys.path.append(repo_dir)
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    finally:
        try:
            sys.path.remove(repo_dir)
        except ValueError:
            pass

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(f"{path} has no class named '{class_name}'")
    if not (isinstance(cls, type) and issubclass(cls, BaseModel)):
        raise TypeError(f"'{class_name}' in {path} is not a pydantic BaseModel")
    return cls


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


# --------------------------------------------------------------------------- #
# High-level: build the initial editor state for a repo
# --------------------------------------------------------------------------- #
def initial_state_for_repo(root_spec: Spec, last_run: Any | None) -> dict:
    """Editor state to open with: the merged last_run.json if we have one, else
    the schema defaults. ``last_run`` is the parsed JSON (a dict) or None."""
    if last_run is None:
        return blank_state(root_spec)
    return merge_value(root_spec, last_run, True)


def load_last_run(repo_name: str) -> Any | None:
    """Parse cache/<repo>/last_run.json, or None if absent/unreadable."""
    path = cached_last_run_path(repo_name)
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def save_last_run(repo_name: str, payload: dict) -> Path:
    """Atomically write the generated config to cache/<repo>/last_run.json."""
    path = cached_last_run_path(repo_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    os.replace(tmp, path)
    return path


def last_run_is_valid(repo_name: str, class_name: str = "Config") -> bool:
    """True if the repo either has no config.py (nothing to configure), or has a
    last_run.json that validates against the current cached config.py.
    Used to gate launch: a repo with a config.py but no valid last_run.json is
    not launchable until the user fills in and saves its config.
    """
    cfg = cached_config_py_path(repo_name)
    if not cfg.is_file():
        return True  # no config required -> automatically valid

    last = cached_last_run_path(repo_name)
    if not last.is_file():
        return False

    try:
        model_cls = load_config_class(cfg, class_name)
        with open(last, "r", encoding="utf-8") as fh:
            model_cls.model_validate_json(fh.read())
        return True
    except Exception:
        return False