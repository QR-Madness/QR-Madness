#!/usr/bin/env python3
"""Regenerate the project card blocks in README.md from profile/projects.yml.

Pulls each repo's live description / archived state from GitHub via `gh api`, so
the cards always reflect reality (handles transfers and renames automatically).
Only the content between the <!-- PROJECTS:<category>:START/END --> markers is
touched; the rest of the README is left byte-for-byte intact.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "profile" / "projects.yml"
README = ROOT / "README.md"

ACCENT = "00ff00"


def gh_repo(repo: str) -> dict:
    """Return live metadata for owner/name, following transfers/renames."""
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}", "--jq",
         "{description, archived, url: .html_url, language: .language}"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"gh api failed for {repo}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def badge(label: str, url: str) -> str:
    # shields.io uses '-' and '_' as separators; escape them as '--' / '__'.
    escaped = label.replace("_", "__").replace("-", "--")
    enc = urllib.parse.quote(escaped, safe="")
    src = (f"https://img.shields.io/badge/Repository-{enc}-{ACCENT}"
           "?style=for-the-badge&logo=github")
    return f"[![Repo]({src})]({url})"


def render(entry: dict) -> str:
    name = entry["name"]
    status = entry["status"]
    tagline = entry["tagline"]
    summary = (f"<summary><code>[{status}]</code> <b>{name}</b> "
               f"&mdash; {tagline}</summary>")

    if entry["repo"] == "classified":
        body = " ".join(entry["body"].split())
        return (f"<details>\n{summary}\n<br>\n\n"
                f"`[CLASSIFIED]` &mdash; under active R&D\n\n"
                f"{body}\n\n</details>")

    meta = gh_repo(entry["repo"])
    desc = (meta.get("description") or tagline).strip()
    archived = " `[ARCHIVED]`" if meta.get("archived") else ""
    return (f"<details>\n{summary}\n<br>\n\n"
            f"{badge(name, meta['url'])}\n\n"
            f"{desc}{archived}\n\n</details>")


def block(entries: list[dict]) -> str:
    return "\n\n".join(render(e) for e in entries)


def splice(text: str, category: str, content: str) -> str:
    start = f"<!-- PROJECTS:{category}:START -->"
    end = f"<!-- PROJECTS:{category}:END -->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"Markers for category '{category}' not found in README.")
    return pattern.sub(f"{start}\n\n{content}\n\n{end}", text)


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text())
    text = README.read_text()
    for category, entries in manifest.items():
        text = splice(text, category, block(entries))

    if text == README.read_text():
        print("README already up to date; no changes.")
        return 0
    README.write_text(text)
    print("README project blocks regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
