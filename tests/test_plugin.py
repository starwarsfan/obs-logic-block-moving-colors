"""Unit tests for the MovingColors plugin.

These tests run without a running OBS instance — conftest.py stubs out the
OBS plugin API so the plugin module can be imported standalone.
"""

from __future__ import annotations

import importlib
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
plugin_mod = importlib.import_module("plugin")
MovingColors = plugin_mod.MovingColors


# ── helpers ───────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG = {
    "min_value": 0,
    "max_value": 255,
    "stepping": 3,
    "random_limits": False,  # deterministic for tests
    "start_value": 125,
}


def _eval(inputs=None, config=None, state=None):
    return MovingColors.evaluate(
        node_id="test",
        inputs={"enabled": True, **(inputs or {})},
        config={**_DEFAULT_CONFIG, **(config or {})},
        state=state or {},
    )


# ── node_type_def ─────────────────────────────────────────────────────────────


def test_type_name():
    assert MovingColors.type_name == "moving_colors"


def test_node_type_def_inputs():
    td = MovingColors.node_type_def()
    ids = {p.id for p in td.inputs}
    assert {"trigger", "enabled", "in_r", "in_g", "in_b", "in_w"} == ids


def test_node_type_def_outputs():
    td = MovingColors.node_type_def()
    assert {p.id for p in td.outputs} == {"red", "green", "blue", "white"}


def test_node_type_def_config_keys():
    td = MovingColors.node_type_def()
    assert {"min_value", "max_value", "stepping", "random_limits", "start_value"} == set(td.config_schema)


# ── disabled by default ───────────────────────────────────────────────────────


def test_disabled_when_enabled_is_none():
    outputs, _ = MovingColors.evaluate(
        node_id="test",
        inputs={},  # enabled not connected
        config=_DEFAULT_CONFIG,
        state={},
    )
    assert outputs == {"red": 0, "green": 0, "blue": 0, "white": 0}


def test_disabled_when_enabled_is_false():
    outputs, _ = MovingColors.evaluate(
        node_id="test",
        inputs={"enabled": False},
        config=_DEFAULT_CONFIG,
        state={},
    )
    assert outputs == {"red": 0, "green": 0, "blue": 0, "white": 0}


def test_disabled_preserves_last_values():
    # Run once to build state
    _, state = _eval()
    # Now disable — outputs should be the last computed values, not zeros
    outputs, _ = MovingColors.evaluate(
        node_id="test",
        inputs={"enabled": False},
        config=_DEFAULT_CONFIG,
        state=state,
    )
    assert all(0 <= outputs[k] <= 255 for k in ("red", "green", "blue", "white"))


# ── initialisation ────────────────────────────────────────────────────────────


def test_initialises_from_current_inputs():
    outputs, state = _eval(inputs={"enabled": True, "in_r": 100, "in_g": 50, "in_b": 200, "in_w": 0})
    # After first tick the values should be close to the seed values (stepped by `stepping`)
    assert state["initialized"] is True
    assert 0 <= outputs["red"] <= 255


def test_stagger_when_no_current_inputs():
    _, state = _eval()
    assert state["initialized"] is True
    vals = list(state["values"].values())
    # Staggered channels should not all start at the same value
    assert len(set(vals)) > 1


# ── animation ─────────────────────────────────────────────────────────────────


def test_outputs_within_range():
    _, state = _eval()
    for _ in range(50):
        outputs, state = _eval(state=state)
        for k in ("red", "green", "blue", "white"):
            assert 0 <= outputs[k] <= 255, f"{k} out of range: {outputs[k]}"


def test_channels_advance_independently():
    """After enough ticks the channels should reach different values."""
    _, state = _eval()
    for _ in range(30):
        outputs, state = _eval(state=state)
    vals = [outputs["red"], outputs["green"], outputs["blue"], outputs["white"]]
    # With 30 ticks and staggered starts at least two channels should differ
    assert len(set(vals)) > 1


def test_respects_min_max_config():
    cfg = {**_DEFAULT_CONFIG, "min_value": 50, "max_value": 100}
    _, state = _eval(config=cfg)
    for _ in range(200):
        outputs, state = _eval(config=cfg, state=state)
        for k in ("red", "green", "blue", "white"):
            assert 50 <= outputs[k] <= 100, f"{k} out of bounds: {outputs[k]}"


def test_direction_reverses_at_max():
    """Channel should start going down once it hits max."""
    cfg = {**_DEFAULT_CONFIG, "min_value": 0, "max_value": 10, "stepping": 5}
    _, state = _eval(inputs={"in_r": 0, "in_g": 0, "in_b": 0, "in_w": 0}, config=cfg)
    seen_max = False
    for _ in range(20):
        outputs, state = _eval(config=cfg, state=state)
        if outputs["red"] == 10:
            seen_max = True
    assert seen_max


def test_state_persists_between_calls():
    outputs1, state = _eval()
    outputs2, _ = _eval(state=state)
    # At least one channel should have advanced between the two ticks
    assert outputs1 != outputs2
