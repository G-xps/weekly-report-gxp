#!/usr/bin/env python3
"""Member alias resolution shared by weekly report scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_members(path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    members = data.get("members", data if isinstance(data, list) else [])
    result: dict[str, dict[str, Any]] = {}
    for member in members:
        name = str(member.get("name", "")).strip()
        if not name:
            continue
        aliases = {name, f"@{name}"}
        aliases.update(str(item).strip() for item in member.get("aliases", []) if str(item).strip())
        result[name] = {"name": name, "aliases": sorted(aliases)}
    return result


def alias_index(members: dict[str, dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for name, member in members.items():
        for alias in member.get("aliases", []):
            normalized = normalize_identity(alias)
            if normalized:
                index[normalized] = name
    return index


def normalize_identity(value: str | None) -> str:
    if not value:
        return ""
    value = str(value).strip()
    value = value.removeprefix("@").strip()
    return value.lower()


def resolve_member(value: str | None, members: dict[str, dict[str, Any]]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    index = alias_index(members)
    normalized = normalize_identity(raw)
    if normalized in index:
        return index[normalized]
    email_match = re.search(r"<([^>]+)>", raw)
    if email_match and normalize_identity(email_match.group(1)) in index:
        return index[normalize_identity(email_match.group(1))]
    return raw.removeprefix("@").strip()


def find_member_mentions(text: str, members: dict[str, dict[str, Any]]) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for name, member in members.items():
        for alias in member.get("aliases", []):
            alias_text = str(alias).strip()
            if alias_text and alias_text in text and name not in found:
                found.append(name)
                break
    if found:
        return found
    for match in re.findall(r"@([\w\u4e00-\u9fff.-]+)", text):
        candidate = resolve_member(match, members)
        if candidate and candidate not in found:
            found.append(candidate)
    return found


def parse_member_list(value: str | None, members: dict[str, dict[str, Any]]) -> list[str]:
    if not value:
        return []
    names: list[str] = []
    for part in re.split(r"[,，、\s]+", value):
        part = part.strip()
        if not part:
            continue
        name = resolve_member(part, members)
        if name and name not in names:
            names.append(name)
    return names


def related_to_targets(owners: list[str] | str | None, targets: list[str]) -> bool:
    if not targets:
        return True
    if owners is None:
        return False
    if isinstance(owners, str):
        owner_list = [owners]
    else:
        owner_list = owners
    return any(owner in targets for owner in owner_list)
