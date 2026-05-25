"""Moving Colors — animates RGB/W light channels with independently bouncing values.

Each of the four output channels (red, green, blue, white) bounces between a
configurable min and max value, advancing by `stepping` on every trigger tick.
Connect any output to any dimmable data point:
  - RGBW fixture   → connect all four
  - RGB fixture    → connect red, green, blue
  - Single dimmer  → connect white (or any single channel)
  - Four dimmers   → connect one channel per light for independent animation

Timing: connect a timer_pulse block set to your desired interval (2–10 s typical).
Enable: wire an OBS data point or a constant `true` to the `enabled` input.
        The block is disabled by default and will not animate until enabled.
"""

from __future__ import annotations

import random
from typing import Any

from obs.logic.plugin_api import LogicNodePlugin, NodeTypeDef, NodeTypePort, register_node_type

_CHANNELS = ("r", "g", "b", "w")


@register_node_type
class MovingColors(LogicNodePlugin):
    type_name = "moving_colors"

    @classmethod
    def node_type_def(cls) -> NodeTypeDef:
        return NodeTypeDef(
            type="moving_colors",
            label="Moving Colors",
            category="lighting",
            description="Animiert RGB/W-Lichtkanäle mit unabhängig springenden Werten.",
            inputs=[
                NodeTypePort(id="trigger",  label="Trigger",          type="trigger"),
                NodeTypePort(id="enabled",  label="Enabled"),
                NodeTypePort(id="in_r",     label="Current Red"),
                NodeTypePort(id="in_g",     label="Current Green"),
                NodeTypePort(id="in_b",     label="Current Blue"),
                NodeTypePort(id="in_w",     label="Current White/Brightness"),
            ],
            outputs=[
                NodeTypePort(id="red",   label="Red"),
                NodeTypePort(id="green", label="Green"),
                NodeTypePort(id="blue",  label="Blue"),
                NodeTypePort(id="white", label="White / Brightness"),
            ],
            config_schema={
                "min_value": {
                    "type": "number",
                    "default": 0,
                    "label": "Min value (0–255)",
                },
                "max_value": {
                    "type": "number",
                    "default": 255,
                    "label": "Max value (0–255)",
                },
                "stepping": {
                    "type": "number",
                    "default": 3,
                    "label": "Step size",
                },
                "random_limits": {
                    "type": "boolean",
                    "default": True,
                    "label": "Randomise sub-boundaries",
                },
                "start_value": {
                    "type": "number",
                    "default": 125,
                    "label": "Start value (fallback if current inputs unconnected)",
                },
            },
            color="#6366f1",
        )

    @classmethod
    def evaluate(
        cls,
        node_id: str,
        inputs: dict[str, Any],
        config: dict[str, Any],
        state: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # ── Guard: block is off by default ────────────────────────────────
        enabled = inputs.get("enabled")
        if not _to_bool(enabled, default=False):
            return _current_outputs(state), state

        # ── Config ────────────────────────────────────────────────────────
        abs_min   = int(config.get("min_value") or 0)
        abs_max   = int(config.get("max_value") or 255)
        stepping  = max(1, int(config.get("stepping") or 3))
        use_rand  = bool(config.get("random_limits", True))
        start_val = int(config.get("start_value") or 125)

        # Clamp and normalise range
        abs_min = max(0, min(255, abs_min))
        abs_max = max(0, min(255, abs_max))
        if abs_min > abs_max:
            abs_min, abs_max = abs_max, abs_min

        # ── Initialise on first enabled tick ──────────────────────────────
        if not state.get("initialized"):
            current_inputs = {
                "r": inputs.get("in_r"),
                "g": inputs.get("in_g"),
                "b": inputs.get("in_b"),
                "w": inputs.get("in_w"),
            }
            state = _init_state(current_inputs, abs_min, abs_max, start_val)

        # ── Advance each channel one step ─────────────────────────────────
        values    = state["values"]
        act_min   = state["active_min"]
        act_max   = state["active_max"]
        count_up  = state["count_up"]

        new_values = dict(values)
        for ch in _CHANNELS:
            val = values[ch]
            up  = count_up[ch]

            if up:
                val += stepping
                if val >= act_max[ch]:
                    val = act_max[ch]
                    count_up[ch] = False
                    act_min[ch] = random.randint(abs_min, val) if use_rand else abs_min
            else:
                val -= stepping
                if val <= act_min[ch]:
                    val = act_min[ch]
                    count_up[ch] = True
                    act_max[ch] = random.randint(val, abs_max) if use_rand else abs_max

            new_values[ch] = max(0, min(255, val))

        state["values"]    = new_values
        state["active_min"] = act_min
        state["active_max"] = act_max
        state["count_up"]   = count_up

        return {
            "red":   new_values["r"],
            "green": new_values["g"],
            "blue":  new_values["b"],
            "white": new_values["w"],
        }, state


# ── Helpers ───────────────────────────────────────────────────────────────────


def _init_state(
    current_inputs: dict[str, Any],
    abs_min: int,
    abs_max: int,
    start_val: int,
) -> dict[str, Any]:
    """Build initial state, seeding from current light values when available."""
    value_range = abs_max - abs_min
    n = len(_CHANNELS)

    values: dict[str, int]  = {}
    act_min: dict[str, int] = {}
    act_max: dict[str, int] = {}
    count_up: dict[str, bool] = {}

    for i, ch in enumerate(_CHANNELS):
        raw = current_inputs.get(ch)
        if raw is not None:
            val = max(abs_min, min(abs_max, int(float(raw))))
        else:
            # No current value — stagger across the range so channels diverge immediately
            val = int(abs_min + (value_range * i / n))
            val = max(abs_min, min(abs_max, val))

        values[ch]   = val
        act_min[ch]  = abs_min
        act_max[ch]  = abs_max
        # Start going up if in the lower half, down otherwise
        count_up[ch] = val < (abs_min + abs_max) / 2

    return {
        "initialized": True,
        "values":      values,
        "active_min":  act_min,
        "active_max":  act_max,
        "count_up":    count_up,
    }


def _current_outputs(state: dict[str, Any]) -> dict[str, Any]:
    """Return the last computed values (used while block is disabled)."""
    vals = state.get("values", {})
    return {
        "red":   vals.get("r", 0),
        "green": vals.get("g", 0),
        "blue":  vals.get("b", 0),
        "white": vals.get("w", 0),
    }


def _to_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "no", "off", "")
    return bool(v)
