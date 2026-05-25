"""Shadow Control — example OBS logic block plugin.

Calculates a blind/shading position from sun elevation and indoor temperature,
with a manual override input.

This file is the entry point for your plugin. Edit it freely, then save —
OBS picks up the change automatically (hot-reload, no restart needed).

Rename this file and update docker-compose.yml + pyproject.toml accordingly
when you are ready to distribute your plugin as a pip package.
"""

from __future__ import annotations

from typing import Any

from obs.logic.plugin_api import LogicNodePlugin, NodeTypeDef, NodeTypePort, register_node_type


@register_node_type
class ShadowControl(LogicNodePlugin):
    type_name = "shadow_control"

    @classmethod
    def node_type_def(cls) -> NodeTypeDef:
        return NodeTypeDef(
            type="shadow_control",
            label="Shadow Control",
            category="integration",
            description="Calculates blind position from sun elevation and indoor temperature.",
            inputs=[
                NodeTypePort(id="sun_elevation", label="Sun elevation (°)"),
                NodeTypePort(id="indoor_temp", label="Indoor temperature"),
                NodeTypePort(id="override", label="Override active"),
                NodeTypePort(id="override_pos", label="Override position"),
            ],
            outputs=[
                NodeTypePort(id="position", label="Position (0–100)"),
                NodeTypePort(id="active", label="Auto active"),
            ],
            config_schema={
                "threshold_elevation": {
                    "type": "number",
                    "default": 20,
                    "min": 0,
                    "max": 90,
                    "label": "Min sun elevation (°)",
                },
                "temp_threshold": {
                    "type": "number",
                    "default": 22,
                    "min": 10,
                    "max": 40,
                    "label": "Activate above indoor temp (°C)",
                },
            },
            color="#d97706",
        )

    @classmethod
    def evaluate(
        cls,
        node_id: str,
        inputs: dict[str, Any],
        config: dict[str, Any],
        state: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if _to_bool(inputs.get("override")):
            pos = _to_num(inputs.get("override_pos"), default=0.0)
            return {"position": pos, "active": False}, state

        elevation = _to_num(inputs.get("sun_elevation"))
        indoor = _to_num(inputs.get("indoor_temp"), default=999.0)
        threshold = float(config.get("threshold_elevation") or 20)
        temp_th = float(config.get("temp_threshold") or 22)

        if elevation < threshold or indoor < temp_th:
            return {"position": 0.0, "active": False}, state

        position = min(100.0, (elevation - threshold) * 2)
        return {"position": round(position, 1), "active": True}, state


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_num(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "no", "off", "")
    return bool(v)
