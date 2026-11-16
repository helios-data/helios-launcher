"""
ConfigEditor: an ImGui popup that edits a repo's pydantic ``Config`` and saves
the result to ``cache/<repo>/last_run.json``.
The schema (and the fields' defaults) come from the repo's cached ``config.py``.
When a previous ``last_run.json`` exists, it is merged into the current schema
(see ``utils.pydantic_config.merge_value``) so as much of the old config as
still fits is kept, and only what changed is reset to defaults.
Usage (one editor per node, held by the EditorComponent):
    editor = ConfigEditor(repo_name="Logging")
    if imgui.button("Edit Config"):
        editor.open()          # (re)loads config.py + merges last_run.json
    editor.render()            # call every frame, outside any style pushes
The rendering code is adapted from the demo; the lifecycle (load/merge/save) is
wired to the per-repo cache and the shared merge engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from imgui_bundle import imgui
from pydantic import ValidationError

from utils.pydantic.spec import (
    Spec, FieldSpec, MISSING,
    STR, INT, FLOAT, BOOL, ENUM, JSON, MODEL, LIST, DICT, OPTIONAL, INLINE_KINDS,
    build_spec, blank_state, to_data, is_invalid,
)
from utils.pydantic.config import (
    initial_state_for_repo, load_last_run, load_config_class,
    cached_config_py_path, has_cached_config, save_last_run,
)

RED_TEXT = (1.0, 0.35, 0.35, 1.0)
RED_FRAME = (0.50, 0.12, 0.12, 1.0)
LABEL_W = 230.0
KEY_W = 180.0
REMOVE_W = 26.0


def _choice_text(choice: Any) -> str:
    return str(choice.value) if isinstance(choice, Enum) else str(choice)


def _summary(spec: Spec, state: Any) -> str:
    if spec.kind == MODEL:
        for f in spec.fields:
            v = state.get(f.name)
            if f.spec.kind == STR and isinstance(v, str) and v:
                return v if len(v) <= 40 else v[:37] + "..."
    return ""


class ConfigEditor:
    def __init__(
        self,
        repo_name: str,
        class_name: str = "Config",
        popup_title: str = "Edit Configuration",
        on_saved: Callable[[], None] | None = None,
    ):
        self.repo_name = repo_name
        self.class_name = class_name
        # Unique popup id so multiple editors (one per node) don't collide.
        self.popup_title = f"{popup_title}##{repo_name}"
        self.on_saved = on_saved

        self.is_open = False
        self.load_error = ""
        self.notice = ""
        self.errors: list[str] = []

        self.model_cls = None
        self.root_spec: Spec | None = None
        self.state: dict = {}
        self._want_open = False

    # ----- lifecycle ------------------------------------------------------- #
    def has_config(self) -> bool:
        return has_cached_config(self.repo_name)

    def open(self) -> None:
        """Reload the schema from the cached config.py and open the popup,
        merging any previous last_run.json into the current schema."""
        self.errors, self.notice, self.load_error = [], "", ""
        try:
            cfg = cached_config_py_path(self.repo_name)
            self.model_cls = load_config_class(cfg, self.class_name)
            self.root_spec = build_spec(self.model_cls)
        except Exception as e:
            self.model_cls = self.root_spec = None
            self.load_error = f"{type(e).__name__}: {e}"
        else:
            last_run = load_last_run(self.repo_name)
            self.state = initial_state_for_repo(self.root_spec, last_run)
            if last_run is not None:
                self.notice = ("Loaded your previous configuration; any fields that "
                               "changed in config.py were reset to their defaults.")
        self.is_open = True
        self._want_open = True

    def _save(self) -> bool:
        assert self.model_cls is not None
        assert self.root_spec is not None
        try:
            instance = self.model_cls.model_validate(to_data(self.root_spec, self.state))
        except ValidationError as e:
            self.errors = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                           for err in e.errors()]
            return False
        except Exception as e:
            self.errors = [f"{type(e).__name__}: {e}"]
            return False

        payload = instance.model_dump(mode="json", by_alias=True)
        save_last_run(self.repo_name, payload)
        self.errors = []
        if self.on_saved:
            self.on_saved()
        return True

    # ----- popup ----------------------------------------------------------- #
    def render(self) -> None:
        """Call once per frame. Draws nothing unless the popup is open."""
        if self._want_open:
            imgui.open_popup(self.popup_title)
            self._want_open = False
        if not self.is_open:
            return

        vp = imgui.get_main_viewport()
        imgui.set_next_window_size((vp.size.x * 0.70, vp.size.y * 0.85), imgui.Cond_.appearing)
        imgui.set_next_window_pos(vp.get_center(), imgui.Cond_.appearing, (0.5, 0.5))

        visible, _ = imgui.begin_popup_modal(
            self.popup_title, None, imgui.WindowFlags_.no_saved_settings)
        if not visible:
            self.is_open = False
            return
        try:
            if self.load_error:
                self._render_load_error()
            else:
                self._render_editor()
        finally:
            imgui.end_popup()

    def _render_load_error(self) -> None:
        imgui.text_colored(RED_TEXT, f"Could not load {self.class_name} from:")
        imgui.text_wrapped(str(cached_config_py_path(self.repo_name)))
        imgui.spacing()
        imgui.text_wrapped(self.load_error)
        imgui.spacing()
        if imgui.button("Close", (120, 0)):
            self.is_open = False
            imgui.close_current_popup()

    def _render_editor(self) -> None:
        assert self.root_spec is not None
        footer_h = imgui.get_frame_height_with_spacing() + 12
        invalid = is_invalid(self.root_spec, self.state, True)

        if imgui.begin_child("##config_form", (0, -footer_h)):
            if self.notice:
                imgui.text_wrapped(self.notice)
                imgui.spacing()
            if invalid:
                imgui.text_colored(RED_TEXT, "Settings marked in red are required.")
                imgui.spacing()
            for err in self.errors:
                imgui.text_colored(RED_TEXT, "- " + err)
            if self.errors:
                imgui.spacing()

            for f in self.root_spec.fields:
                self.state[f.name] = self._render_field(f, self.state[f.name], f.name, 0)
        imgui.end_child()

        imgui.separator()
        imgui.begin_disabled(invalid)
        if imgui.button("Save", (120, 0)):
            if self._save():
                self.is_open = False
                imgui.close_current_popup()
        imgui.end_disabled()
        imgui.same_line()
        if imgui.button("Cancel", (120, 0)):
            self.is_open = False
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Reset to defaults"):
            self.state = blank_state(self.root_spec)
            self.errors = []

    # ----- field rendering ------------------------------------------------- #
    def _render_field(self, f: FieldSpec, state: Any, path: str, depth: int) -> Any:
        label = f.name + (" *" if f.required else "")
        return self._render_value(f.spec, state, label, path, f.description, f.required, depth)

    def _render_value(self, spec: Spec, state: Any, label: str, path: str,
                      desc: str | None, required: bool, depth: int) -> Any:
        imgui.push_id(path)
        try:
            k = spec.kind
            if k in INLINE_KINDS:
                return self._inline_row(spec, state, label, desc, required)
            if k == OPTIONAL:
                return self._render_optional(spec, state, label, path, desc, depth)
            if k == MODEL:
                return self._render_model(spec, state, label, path, desc, required, depth)
            if k == LIST:
                return self._render_list(spec, state, label, path, desc, required, depth)
            if k == DICT:
                return self._render_dict(spec, state, label, path, desc, required, depth)
            return state
        finally:
            imgui.pop_id()

    # -- layout helpers
    def _label(self, label: str, desc: str | None, bad: bool) -> None:
        x0 = imgui.get_cursor_pos_x()
        imgui.align_text_to_frame_padding()
        if bad:
            imgui.push_style_color(imgui.Col_.text, RED_TEXT)
        imgui.text(label)
        if bad:
            imgui.pop_style_color()
        if desc and imgui.is_item_hovered():
            imgui.set_tooltip(desc)
        offset = max(LABEL_W, imgui.calc_text_size(label).x + 12.0)
        imgui.same_line(x0 + offset)

    def _section(self, title: str, desc: str | None, bad: bool, depth: int, default_open: bool) -> bool:
        flags = imgui.TreeNodeFlags_.none
        if depth == 0:
            flags |= imgui.TreeNodeFlags_.framed
        if default_open:
            flags |= imgui.TreeNodeFlags_.default_open
        if bad:
            imgui.push_style_color(imgui.Col_.text, RED_TEXT)
        opened = imgui.tree_node_ex(title + "###hdr", flags)
        if bad:
            imgui.pop_style_color()
        if desc and imgui.is_item_hovered():
            imgui.set_tooltip(desc)
        return opened

    # -- inline (single-widget) kinds
    def _inline_row(self, spec: Spec, state: Any, label: str, desc: str | None,
                    required: bool, trailing: float = 0.0) -> Any:
        bad = is_invalid(spec, state, required)
        self._label(label, desc, bad)
        return self._draw_inline(spec, state, bad, required, trailing)

    def _draw_inline(self, spec: Spec, state: Any, bad: bool, required: bool,
                     trailing: float) -> Any:
        spacing = imgui.get_style().item_spacing.x
        width = -(trailing + spacing) if trailing else -1.0
        fill = imgui.get_content_region_avail().x - ((trailing + spacing) if trailing else 0.0)
        k = spec.kind

        if bad:
            imgui.push_style_color(imgui.Col_.frame_bg, RED_FRAME)
            imgui.push_style_color(imgui.Col_.button, RED_FRAME)
        try:
            if k in (INT, FLOAT, BOOL) and state is MISSING:
                # A required number/bool: make the user explicitly choose a value.
                if imgui.button("required - click to set##set", (fill, 0)):
                    return blank_state(spec, filled=True)
                return state

            imgui.set_next_item_width(width)
            if k == STR or k == JSON:
                text = "" if state is MISSING else state
                hint = "JSON" if k == JSON else ("required" if required else "")
                changed, v = imgui.input_text_with_hint("##v", hint, text)
                return v if changed else state
            if k == INT:
                changed, v = imgui.input_int("##v", int(state))
                return v if changed else state
            if k == FLOAT:
                changed, v = imgui.input_double("##v", float(state), 0.0, 0.0, "%.6g")
                return v if changed else state
            if k == BOOL:
                changed, v = imgui.checkbox("##v", bool(state))
                return v if changed else state
            if k == ENUM:
                preview = "-- select --" if state is MISSING else _choice_text(state)
                if imgui.begin_combo("##v", preview):
                    for i, choice in enumerate(spec.choices):
                        picked, _ = imgui.selectable(f"{_choice_text(choice)}##{i}", choice == state)
                        if picked:
                            state = choice
                    imgui.end_combo()
                return state
            return state
        finally:
            if bad:
                imgui.pop_style_color(2)

    # -- Optional[T]
    def _render_optional(self, spec: Spec, state: Any, label: str, path: str,
                         desc: str | None, depth: int) -> Any:
        assert spec.item is not None
        inner = spec.item
        self._label(label, desc, is_invalid(spec, state, False))
        changed, enabled = imgui.checkbox("##enabled", state is not None)
        if changed:
            state = blank_state(inner, filled=True) if enabled else None

        if state is None:
            imgui.same_line()
            imgui.text_disabled("not set")
        elif inner.kind in INLINE_KINDS:
            imgui.same_line()
            state = self._draw_inline(inner, state, is_invalid(inner, state, True), True, 0.0)
        else:
            imgui.indent()
            state = self._render_value(inner, state, "value", path + ".value", None, True, depth + 1)
            imgui.unindent()
        return state

    # -- nested object
    def _render_model(self, spec: Spec, state: dict, label: str, path: str,
                      desc: str | None, required: bool, depth: int) -> dict:
        bad = is_invalid(spec, state, required)
        if self._section(label, desc, bad, depth, default_open=(depth == 0 or required)):
            for f in spec.fields:
                state[f.name] = self._render_field(f, state[f.name], f"{path}.{f.name}", depth + 1)
            imgui.tree_pop()
        if depth == 0:
            imgui.spacing()
        return state

    # -- list[T]
    def _render_list(self, spec: Spec, state: list, label: str, path: str,
                     desc: str | None, required: bool, depth: int) -> list:
        bad = is_invalid(spec, state, required)
        if self._section(f"{label}  ({len(state)})", desc, bad, depth,
                         default_open=(depth == 0 or required)):
            assert spec.item is not None
            item_spec = spec.item
            remove_idx = None
            for i, item in enumerate(state):
                ipath = f"{path}[{i}]"
                imgui.push_id(ipath)
                if item_spec.kind in INLINE_KINDS:
                    state[i] = self._inline_row(item_spec, item, f"[{i}]", None, True, REMOVE_W)
                    imgui.same_line()
                    if imgui.button("X##rm", (REMOVE_W, 0)):
                        remove_idx = i
                else:
                    summary = _summary(item_spec, item)
                    title = f"[{i}]  {summary}" if summary else f"[{i}]"
                    ibad = is_invalid(item_spec, item, True)
                    if ibad:
                        imgui.push_style_color(imgui.Col_.text, RED_TEXT)
                    opened = imgui.tree_node_ex(title + "###item", imgui.TreeNodeFlags_.default_open)
                    if ibad:
                        imgui.pop_style_color()
                    imgui.same_line()
                    if imgui.button("Remove##rm"):
                        remove_idx = i
                    if opened:
                        state[i] = self._render_item_body(item_spec, item, ipath, depth + 1)
                        imgui.tree_pop()
                imgui.pop_id()

            if remove_idx is not None:
                del state[remove_idx]
            if imgui.button("+ Add##add"):
                state.append(blank_state(item_spec))
            imgui.tree_pop()
        if depth == 0:
            imgui.spacing()
        return state

    # -- dict[str, T]
    def _render_dict(self, spec: Spec, state: list, label: str, path: str,
                     desc: str | None, required: bool, depth: int) -> list:
        bad = is_invalid(spec, state, required)
        if self._section(f"{label}  ({len(state)})", desc, bad, depth,
                         default_open=(depth == 0 or required)):
            assert spec.item is not None
            item_spec = spec.item
            keys = [p[0] for p in state]
            remove_idx = None
            for i, pair in enumerate(state):
                ipath = f"{path}[{i}]"
                key, val = pair
                key_bad = key == "" or keys.count(key) > 1
                imgui.push_id(ipath)
                if item_spec.kind in INLINE_KINDS:
                    pair[0] = self._key_input(key, key_bad, KEY_W)
                    imgui.same_line()
                    pair[1] = self._draw_inline(item_spec, val, is_invalid(item_spec, val, True),
                                                True, REMOVE_W)
                    imgui.same_line()
                    if imgui.button("X##rm", (REMOVE_W, 0)):
                        remove_idx = i
                else:
                    ibad = key_bad or is_invalid(item_spec, val, True)
                    if ibad:
                        imgui.push_style_color(imgui.Col_.text, RED_TEXT)
                    opened = imgui.tree_node_ex((key or "(empty key)") + "###item",
                                                imgui.TreeNodeFlags_.default_open)
                    if ibad:
                        imgui.pop_style_color()
                    imgui.same_line()
                    if imgui.button("Remove##rm"):
                        remove_idx = i
                    if opened:
                        self._label("key", None, key_bad)
                        pair[0] = self._key_input(key, key_bad, -1.0)
                        pair[1] = self._render_item_body(item_spec, val, ipath, depth + 1)
                        imgui.tree_pop()
                imgui.pop_id()

            if remove_idx is not None:
                del state[remove_idx]
            if imgui.button("+ Add##add"):
                state.append(["", blank_state(item_spec)])
            imgui.tree_pop()
        if depth == 0:
            imgui.spacing()
        return state

    def _key_input(self, key: str, bad: bool, width: float) -> str:
        if bad:
            imgui.push_style_color(imgui.Col_.frame_bg, RED_FRAME)
        imgui.set_next_item_width(width)
        changed, v = imgui.input_text_with_hint("##key", "key", key)
        if bad:
            imgui.pop_style_color()
        return v if changed else key

    def _render_item_body(self, spec: Spec, state: Any, ipath: str, depth: int) -> Any:
        """Contents of an expanded list/dict item that isn't a simple widget."""
        if spec.kind == MODEL:
            for f in spec.fields:
                state[f.name] = self._render_field(f, state[f.name], f"{ipath}.{f.name}", depth + 1)
            return state
        return self._render_value(spec, state, "items", ipath + ".v", None, True, depth)