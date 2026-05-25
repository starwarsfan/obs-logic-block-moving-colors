"""Unit tests for the Shadow Control plugin.

These tests run without a running OBS instance — conftest.py stubs out the
OBS plugin API so the plugin module can be imported standalone.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# Import the plugin module from the repo root (not installed as a package).
# conftest.py already injected the OBS stubs before this runs.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
plugin_mod = importlib.import_module("plugin")
ShadowControl = plugin_mod.ShadowControl


# ── node_type_def ─────────────────────────────────────────────────────────────


def test_type_name():
    assert ShadowControl.type_name == "shadow_control"


def test_node_type_def_ports():
    td = ShadowControl.node_type_def()
    input_ids = {p.id for p in td.inputs}
    output_ids = {p.id for p in td.outputs}
    assert {"sun_elevation", "indoor_temp", "override", "override_pos"} == input_ids
    assert {"position", "active"} == output_ids


def test_node_type_def_config_schema():
    td = ShadowControl.node_type_def()
    assert "threshold_elevation" in td.config_schema
    assert "temp_threshold" in td.config_schema


# ── evaluate — automation mode ────────────────────────────────────────────────


def _eval(inputs=None, config=None, state=None):
    return ShadowControl.evaluate(
        node_id="test",
        inputs=inputs or {},
        config=config or {},
        state=state or {},
    )


def test_below_elevation_threshold_returns_zero():
    outputs, _ = _eval(
        inputs={"sun_elevation": 10, "indoor_temp": 25},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    assert outputs["position"] == 0.0
    assert outputs["active"] is False


def test_below_temp_threshold_returns_zero():
    outputs, _ = _eval(
        inputs={"sun_elevation": 30, "indoor_temp": 18},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    assert outputs["position"] == 0.0
    assert outputs["active"] is False


def test_above_both_thresholds_returns_position():
    outputs, _ = _eval(
        inputs={"sun_elevation": 30, "indoor_temp": 25},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    # (30 - 20) * 2 = 20.0
    assert outputs["position"] == 20.0
    assert outputs["active"] is True


def test_position_capped_at_100():
    outputs, _ = _eval(
        inputs={"sun_elevation": 90, "indoor_temp": 30},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    assert outputs["position"] == 100.0


def test_none_inputs_treated_as_zero():
    outputs, _ = _eval(
        inputs={"sun_elevation": None, "indoor_temp": None},
        config={"threshold_elevation": 20},
    )
    assert outputs["position"] == 0.0


# ── evaluate — override mode ──────────────────────────────────────────────────


def test_override_active_uses_override_position():
    outputs, _ = _eval(
        inputs={"override": True, "override_pos": 75, "sun_elevation": 50, "indoor_temp": 30},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    assert outputs["position"] == 75.0
    assert outputs["active"] is False


def test_override_string_true():
    outputs, _ = _eval(inputs={"override": "true", "override_pos": 50})
    assert outputs["position"] == 50.0
    assert outputs["active"] is False


def test_override_false_uses_automation():
    outputs, _ = _eval(
        inputs={"override": False, "sun_elevation": 30, "indoor_temp": 25},
        config={"threshold_elevation": 20, "temp_threshold": 22},
    )
    assert outputs["active"] is True


# ── state passthrough ─────────────────────────────────────────────────────────


def test_state_passed_through_unchanged():
    state = {"counter": 42}
    _, returned_state = _eval(state=state)
    assert returned_state["counter"] == 42
