#!/usr/bin/env python3
"""轻量 case.yaml 解析器（官方 testcases 子集）。"""

from __future__ import annotations

from typing import Any


def _scalar(s: str) -> Any:
    s = s.strip()
    if s.startswith("0x"):
        return int(s, 16)
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s in ("true", "false"):
        return s == "true"
    try:
        return int(s)
    except ValueError:
        return s


def parse_case_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except Exception:
        pass

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any, str]] = [(-1, root, "dict")]

    for raw in text.splitlines():
        if "#" in raw:
            raw = raw[: raw.index("#")]
        if not raw.strip():
            continue

        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()

        parent, ptype = stack[-1][1], stack[-1][2]

        if line.startswith("- "):
            if ptype != "list":
                raise ValueError(f"列表语法错误: {line}")
            item = line[2:].strip()
            if ":" in item:
                obj: dict[str, Any] = {}
                k, v = item.split(":", 1)
                obj[k.strip()] = _scalar(v)
                parent.append(obj)
                stack.append((indent, obj, "dict"))
            else:
                parent.append(_scalar(item))
            continue

        if ":" not in line:
            continue

        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()

        if ptype == "list":
            if not parent:
                raise ValueError(f"空列表项后续字段: {line}")
            last = parent[-1]
            if not isinstance(last, dict):
                raise ValueError(f"列表项非 dict: {line}")
            if not val:
                child: dict[str, Any] = {}
                last[key] = child
                stack.append((indent, child, "dict"))
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                last[key] = [_scalar(x) for x in inner.split(",")] if inner else []
            else:
                last[key] = _scalar(val)
            continue

        if not val:
            if key in ("memory_init", "memory"):
                child_list: list = []
                parent[key] = child_list
                stack.append((indent, child_list, "list"))
            else:
                child_dict: dict[str, Any] = {}
                parent[key] = child_dict
                stack.append((indent, child_dict, "dict"))
            continue

        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            parent[key] = [_scalar(x) for x in inner.split(",")] if inner else []
        else:
            parent[key] = _scalar(val)

    return root
