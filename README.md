# obs-logic-block-template

Template repository for building custom logic block plugins for [open bridge server](https://github.com/abeggled/openbridgeserver).

Fork this repo, edit `plugin.py`, and your block appears in the OBS logic editor — no OBS source code needed, no restart required while developing.

---

## Quick start

**Prerequisites:** Docker Desktop (or Docker Engine + Compose plugin)

```bash
# 1. Fork this repo on GitHub, then clone your fork
git clone https://github.com/your-name/obs-plugin-shadow-control
cd obs-plugin-shadow-control

# 2. Create your .env (defaults work for local dev)
cp .env.example .env

# 3. Start the stack
docker compose up
```

Open **http://localhost:8080** (login: `admin` / `admin`) and go to **Logic → Node palette** — your block is already listed under the category defined in `plugin.py`.

---

## Hot-reload development loop

The `plugin.py` file is bind-mounted into the OBS container. As soon as you save a change, OBS detects it and reloads:

```
INFO  obs.logic.plugin_loader: Plugin reloaded: plugin.py — types: ['shadow_control']
```

Watch the logs live:

```bash
docker compose logs -f obs
```

If your file has a syntax error or a missing `@register_node_type` decorator, OBS logs a warning and waits for the next save — no crash, no restart needed:

```
WARNING obs.logic.plugin_loader: Plugin reload produced no types: plugin.py
ERROR   obs.logic.plugin_loader: Plugin failed to load: plugin.py
```

Fix the error and save again.

---

## Project layout

```
obs-logic-block-template/
├── plugin.py                  # Your logic block — edit this
├── docker-compose.yml         # Dev stack: OBS + Mosquitto
├── mosquitto/
│   └── mosquitto.conf         # MQTT broker config (no changes needed)
├── pyproject.toml             # Packaging metadata for pip distribution
├── tests/
│   ├── conftest.py            # OBS API stubs (no OBS needed to run tests)
│   └── test_plugin.py        # Unit tests for evaluate()
└── .github/
    └── workflows/
        └── test.yml           # CI: runs pytest on every push
```

---

## Customising the example

`plugin.py` ships with a working **Shadow Control** block (calculates blind position from sun elevation and indoor temperature). Replace it with your own logic:

1. Change `type_name` — must be globally unique across all plugins and built-in blocks.
2. Update `node_type_def()` — adjust `label`, `category`, `inputs`, `outputs`, and `config_schema`.
3. Implement `evaluate()` — receives `inputs` and `config` dicts, returns `(outputs, state)`.

### Multiple blocks in one file

A single `plugin.py` can register any number of types:

```python
@register_node_type
class BlockA(LogicNodePlugin):
    type_name = "block_a"
    ...

@register_node_type
class BlockB(LogicNodePlugin):
    type_name = "block_b"
    ...
```

### Input/output port types

```python
NodeTypePort(id="trigger_in", label="Trigger", type="trigger")  # trigger signal
NodeTypePort(id="value_in",   label="Value")                    # value (default)
```

### Persistent state

The `state` dict survives graph executions and server restarts. Use it for hysteresis, counters, moving averages, etc.:

```python
@classmethod
def evaluate(cls, node_id, inputs, config, state):
    total = state.get("total", 0.0) + float(inputs.get("value") or 0)
    state["total"] = total
    return {"total": total}, state
```

Keep it JSON-serialisable (str, int, float, bool, list, dict only).

---

## Running unit tests

The tests in `tests/` call `evaluate()` directly — no running OBS, no Docker needed. `conftest.py` stubs out the OBS plugin API so `plugin.py` can be imported standalone.

```bash
pip install pytest
pytest tests/ -v
```

Write a test for each behaviour you care about:

```python
def test_my_block():
    outputs, state = MyBlock.evaluate(
        node_id="test",
        inputs={"value": 42},
        config={"multiplier": 2},
        state={},
    )
    assert outputs["result"] == 84
```

---

## Distributing as a pip package

When your block is ready to share, distribute it as a pip package so other OBS users can install it with one command.

### Rename for distribution

1. Rename `plugin.py` to `<your_block_name>.py` (e.g. `shadow_control.py`)
2. Update `docker-compose.yml` — change the volume mount path:
   ```yaml
   - ./shadow_control.py:/plugins/shadow_control.py:ro
   ```
3. Update `pyproject.toml` — rename the package and fix the entry point:
   ```toml
   [project]
   name = "obs-plugin-shadow-control"

   [project.entry-points."obs.logic_blocks"]
   shadow_control = "shadow_control"

   [tool.hatch.build.targets.wheel]
   include = ["shadow_control.py"]
   ```

### Build and publish

```bash
pip install hatch
hatch build
hatch publish          # publishes to PyPI
```

### Install on a running OBS instance

```bash
# LXC / bare-metal
source /opt/obs/venv/bin/activate
pip install obs-plugin-shadow-control
systemctl restart obs

# Docker — exec into the running container
docker exec obs pip install obs-plugin-shadow-control
docker compose restart obs
```

No `OBS_PLUGINS_DIR` configuration is needed for pip-installed entry-point plugins.

---

## Plugin API reference

Full interface documentation, `NodeTypeDef` field reference, type coercion helpers, and more examples live in the OBS source repo:

[`docs/logic-plugin-api.md`](https://github.com/abeggled/openbridgeserver/blob/main/docs/logic-plugin-api.md)

---

## Licence

MIT
