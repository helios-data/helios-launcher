# Per-repo pydantic configuration: loading a repo's ``config.py``, building an
# editor schema from it, merging a previous ``last_run.json`` against a changed
# schema, and validating the result.
# This module is UI-free. The ImGui editor (``interface/components/config_editor.py``)
# and the launcher wiring (``docker.py`` / ``interface/main.py``) both build on it.
# Cache layout (survives ``tmp/`` cleanup)::
#     cache/<repo_name>/config.py       # copy of the repo's config.py
#     cache/<repo_name>/last_run.json   # last saved, schema-valid config
# NOTE: a repo's ``config.py`` is *executed* to load it. Only point this at repos
# you already trust enough to build and run.

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from config.settings import (
    ROOT,
    CONFIG_CACHE_FOLDER,
    CONFIG_PY_NAME,
    REPO_CONFIG_RELPATH,
    LAST_RUN_NAME,
    sanitize_image_name,
)

from src.utils.pydantic.spec import Spec, blank_state
from src.utils.pydantic.conflict import merge_value


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