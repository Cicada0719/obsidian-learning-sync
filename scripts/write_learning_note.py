#!/usr/bin/env python3
"""Write a learning note into an Obsidian vault and update the project index."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


INVALID_PATH_CHARS = r'<>:"/\|?*'
DEFAULT_VAULT_NAME = "Codex Learning Vault"


def safe_segment(value: str, fallback: str = "untitled", max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    cleaned = []
    for char in normalized:
        if char in INVALID_PATH_CHARS or ord(char) < 32:
            cleaned.append("-")
        else:
            cleaned.append(char)
    segment = "".join(cleaned)
    segment = re.sub(r"\s+", " ", segment)
    segment = re.sub(r"-{2,}", "-", segment)
    segment = segment.strip(" .-")
    if not segment:
        segment = fallback
    return segment[:max_length].rstrip(" .-") or fallback


def safe_slug(value: str) -> str:
    segment = safe_segment(value, fallback="note", max_length=72).lower()
    segment = re.sub(r"\s+", "-", segment)
    segment = re.sub(r"-{2,}", "-", segment)
    return segment.strip("-") or "note"


def safe_folder_path(value: str, vault: Path, fallback: str = "Codex Learning") -> Path:
    raw = (value or fallback).strip()
    folder = Path(raw)
    if folder.is_absolute():
        resolved = folder.expanduser().resolve()
        try:
            folder = resolved.relative_to(vault)
        except ValueError as exc:
            raise ValueError(f"Folder path must be inside the vault: {resolved}") from exc

    safe_parts: list[str] = []
    for part in folder.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Folder path cannot contain '..'")
        safe_parts.append(safe_segment(part, fallback="folder"))

    if not safe_parts:
        safe_parts.append(safe_segment(fallback, fallback="Codex Learning"))
    return Path(*safe_parts)


def unique_note_path(project_dir: Path, timestamp: str, slug: str) -> Path:
    candidate = project_dir / f"{timestamp}-{slug}.md"
    counter = 2
    while candidate.exists():
        candidate = project_dir / f"{timestamp}-{slug}-{counter}.md"
        counter += 1
    return candidate


def candidate_search_roots() -> list[Path]:
    home = Path.home()
    roots = [
        home / "Documents",
        home / "Desktop",
        home / "OneDrive",
        home,
    ]
    seen: set[Path] = set()
    existing: list[Path] = []
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists() or not resolved.is_dir():
            continue
        seen.add(resolved)
        existing.append(resolved)
    return existing


def discover_vault() -> Path | None:
    for root in candidate_search_roots():
        try:
            for obsidian_dir in root.rglob(".obsidian"):
                if obsidian_dir.is_dir():
                    return obsidian_dir.parent.resolve()
        except (OSError, PermissionError):
            continue
    return None


def default_vault_path() -> Path:
    return Path.home() / "Documents" / "Obsidian" / DEFAULT_VAULT_NAME


def resolve_vault(explicit_vault: str | None) -> tuple[Path, str]:
    if explicit_vault:
        vault = Path(explicit_vault).expanduser().resolve()
        if not vault.exists() or not vault.is_dir():
            raise ValueError(f"Vault path does not exist: {vault}")
        return vault, "explicit"

    env_vault = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_vault:
        vault = Path(env_vault).expanduser().resolve()
        if not vault.exists() or not vault.is_dir():
            raise ValueError(f"OBSIDIAN_VAULT_PATH does not exist: {vault}")
        return vault, "env"

    discovered = discover_vault()
    if discovered:
        return discovered, "discovered"

    vault = default_vault_path().resolve()
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    return vault, "created"


def ensure_index(index_path: Path, project: str) -> None:
    if index_path.exists():
        return
    content = (
        f"# {project} 学习索引\n\n"
        "这个索引由 `$obsidian-learning-sync` 维护，用来汇总 Codex 任务后的学习笔记。\n\n"
        "## Notes\n\n"
    )
    index_path.write_text(content, encoding="utf-8", newline="\n")


def append_index_entry(index_path: Path, title: str, note_stem: str, created_at: str) -> str:
    wikilink = f"[[{note_stem}|{title}]]"
    entry = f"- {wikilink} - {created_at}\n"
    existing = index_path.read_text(encoding="utf-8")
    if wikilink not in existing:
        if not existing.endswith("\n"):
            existing += "\n"
        index_path.write_text(existing + entry, encoding="utf-8", newline="\n")
    return wikilink


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a beginner-friendly learning note into an Obsidian vault."
    )
    parser.add_argument(
        "--vault",
        help=(
            "Path to the Obsidian vault root. If omitted, use OBSIDIAN_VAULT_PATH, "
            "discover a vault by .obsidian folders, or create a default learning vault."
        ),
    )
    parser.add_argument("--project", required=True, help="Project name for the learning folder.")
    parser.add_argument("--title", required=True, help="Human-readable note title.")
    parser.add_argument(
        "--content-file",
        required=True,
        help="UTF-8 Markdown file containing the complete note body.",
    )
    parser.add_argument(
        "--folder",
        default="Codex Learning",
        help="Top-level folder inside the vault. Defaults to 'Codex Learning'.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        vault, vault_source = resolve_vault(args.vault)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    content_file = Path(args.content_file).expanduser().resolve()
    if not content_file.exists() or not content_file.is_file():
        print(
            json.dumps({"error": f"Content file does not exist: {content_file}"}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2

    try:
        folder_path = safe_folder_path(args.folder, vault)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    project_segment = safe_segment(args.project, fallback="Project")
    project_dir = vault / folder_path / project_segment
    project_dir.mkdir(parents=True, exist_ok=True)

    now = dt.datetime.now().astimezone()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    created_at = now.strftime("%Y-%m-%d %H:%M:%S %z")
    slug = safe_slug(args.title)

    note_path = unique_note_path(project_dir, timestamp, slug)
    note_content = content_file.read_text(encoding="utf-8-sig")
    if not note_content.endswith("\n"):
        note_content += "\n"
    note_path.write_text(note_content, encoding="utf-8", newline="\n")

    index_path = project_dir / "Index.md"
    ensure_index(index_path, args.project)
    wikilink = append_index_entry(index_path, args.title, note_path.stem, created_at)

    result = {
        "vault_path": str(vault),
        "vault_source": vault_source,
        "note_path": str(note_path),
        "index_path": str(index_path),
        "wikilink": wikilink,
        "project_folder": str(project_dir),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
