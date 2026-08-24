"""Document loading and stable CLI output helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

CLI_SCHEMA_VERSION = "mlai.cli.v1"


class CliError(ValueError):
    """Raised for invalid local CLI inputs."""


def load_document(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"input file not found: {source}") from exc
    except yaml.YAMLError as exc:
        raise CliError(f"invalid YAML/JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise CliError(f"input document must contain an object: {source}")
    return value


def envelope(command: str, data: Any, *, ok: bool = True) -> dict[str, Any]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "command": command,
        "ok": ok,
        "data": data,
    }


def emit(command: str, data: Any, *, ok: bool = True, output: str = "json") -> None:
    payload = envelope(command, data, ok=ok)
    if output == "json":
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        return
    print(f"{command}: {'ok' if ok else 'failed'}")
    if isinstance(data, Mapping):
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print(data)
