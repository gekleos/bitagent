#!/usr/bin/env python3
"""Sanitize content for public GitHub publishing.

Scans every file in a directory tree against a deny-list of identifying
strings (real domains, internal IPs, real user handles, internal repo
namespaces). Writes a per-file report and exits non-zero if any deny-list
hit is found.

Usage:
    sanitize.py scan <dir>          # report-only, exits 1 on any hit
    sanitize.py rewrite <dir>       # apply replacements + scan; fails if
                                    # any deny term still present after.

Replacements are intentionally conservative — we replace identifying tokens
with neutral placeholders (`example.com`, `gekleos`, etc.). Anything not in
the replacement map but matching the deny-list causes a hard fail; the
operator must hand-fix.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Skip the scanner itself — it intentionally lists every deny term.
SELF_NAME = "sanitize.py"

# Substring deny — these are unambiguous strings; any presence is a hit.
DENY_LIST_SUBSTR: list[str] = [
    "bitagent.norvi.tech",
    "auth.globalentry.systems",
    ".globalentry.systems",
    "globalentry.systems",
    "git.norvi.tech",
    "registry.norvi.tech",
    "norvi.tech",
    "kleos@norvi.tech",
    "ge-systems-sso",
    "telegram-auth-portal",
    "Spencer Norton",
    "godfather-macbookpro",
    "godfather.systems",
    "100.116.145.127",
    "100.125.93.72",
    "Galactic-QBT",
    "Galactic-Torrent",
    "Plex Squire",
    "Portainer stack 266",
    "Portainer stack 252",
]

# Whole-word deny — terms that often appear as substrings of legitimate
# words (e.g. "kleos" inside "gekleos"). Matched with word boundaries so
# they don't false-positive on the safe form.
DENY_LIST_WORDS: list[str] = [
    "Spencer",
    "Tailscale",
    "Infisical",
    "Apollo",
    "Squire",
    "Atlas",
    "Kleos",
    "kleos",
    "GlobalEntry",
    "globalentry",
    "ge_sso",  # the bare cookie name; accepted in code via SSO_COOKIE_NAME but flagged in docs
    "stack 266",
    "stack 252",
    "stack 273",
    "claude/",
]

# Substring replacements — applied first; deterministic.
REPLACEMENTS_SUBSTR: dict[str, str] = {
    "bitagent.norvi.tech": "bitagent.example.com",
    "auth.globalentry.systems": "auth.example.com",
    ".globalentry.systems": ".example.com",
    "globalentry.systems": "example.com",
    "git.norvi.tech": "github.com",
    "registry.norvi.tech": "ghcr.io/gekleos",
    "norvi.tech": "example.com",
    "kleos@norvi.tech": "bitagent-bot@users.noreply.github.com",
    "ge-systems-sso": "bitagent-sso",
    "telegram-auth-portal": "external-sso",
    "Spencer Norton": "the operator",
    "godfather-macbookpro": "operator workstation",
    "godfather.systems": "example.com",
    "100.116.145.127": "10.0.0.1",
    "100.125.93.72": "10.0.0.2",
    "Galactic-QBT": "qbt",
    "Galactic-Torrent": "indexer service",
    "Plex Squire": "the operator's media stack",
    "Portainer stack 266": "the production stack",
    "Portainer stack 252": "the indexer stack",
}

# Whole-word replacements (regex word boundary).
REPLACEMENTS_WORDS: dict[str, str] = {
    "Spencer": "the operator",
    "Tailscale": "private network",
    "Infisical": "secret store",
    "Apollo": "indexer-host",
    "Squire": "infra-host",
    "Atlas": "infra-host",
    "Kleos": "BitAgent",
    "kleos": "bitagent-dev",
    "GlobalEntry": "BitAgent contributors",
    "globalentry": "bitagent-contrib",
    "ge_sso": "bitagent_session",
    "stack 266": "production stack",
    "stack 252": "indexer stack",
    "stack 273": "automation stack",
    "claude/": "feat/",
}


def _word_re(term: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Za-z0-9_/]){re.escape(term)}(?![A-Za-z0-9_])")


WORD_DENY_RE = {term: _word_re(term) for term in DENY_LIST_WORDS}
WORD_REPL_RE = {term: _word_re(term) for term in REPLACEMENTS_WORDS}


# Files we never scan — binary or generated.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar", ".pyc"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, term, line_content) hits for a file."""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return hits
    for line_no, line in enumerate(text.splitlines(), 1):
        for term in DENY_LIST_SUBSTR:
            if term in line:
                hits.append((line_no, term, line.strip()[:200]))
        for term, pat in WORD_DENY_RE.items():
            if pat.search(line):
                hits.append((line_no, term, line.strip()[:200]))
    return hits


def rewrite_file(path: Path) -> int:
    """Apply replacements in-place. Returns number of substitutions made."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return 0
    original = text
    n = 0
    for old, new in REPLACEMENTS_SUBSTR.items():
        if old in text:
            text = text.replace(old, new)
            n += 1
    for term, replacement in REPLACEMENTS_WORDS.items():
        new_text, count = WORD_REPL_RE[term].subn(replacement, text)
        if count:
            text = new_text
            n += count
    if text != original:
        path.write_text(text, encoding="utf-8")
    return n


def walk(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name == SELF_NAME:
            continue
        if any(seg in SKIP_DIRS for seg in p.parts):
            continue
        if p.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield p


def cmd_scan(root: Path) -> int:
    total_hits = 0
    bad_files = 0
    for f in walk(root):
        hits = scan_file(f)
        if hits:
            bad_files += 1
            print(f"\n[HIT] {f.relative_to(root)}")
            for ln, term, line in hits:
                print(f"  L{ln} term='{term}'  | {line}")
            total_hits += len(hits)
    if total_hits == 0:
        print(f"\nclean: scanned {sum(1 for _ in walk(root))} files; 0 deny-list hits.")
        return 0
    print(f"\n{bad_files} files with {total_hits} deny-list hits. NOT publish-safe.")
    return 1


def cmd_rewrite(root: Path) -> int:
    total = 0
    for f in walk(root):
        n = rewrite_file(f)
        if n:
            print(f"  rewrote {n} occurrence(s) in {f.relative_to(root)}")
            total += n
    print(f"\ntotal substitutions: {total}")
    print("running scan to verify no deny-list term remains...")
    return cmd_scan(root)


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("scan", "rewrite"):
        print("usage: sanitize.py scan|rewrite <dir>", file=sys.stderr)
        return 2
    root = Path(sys.argv[2]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    if sys.argv[1] == "scan":
        return cmd_scan(root)
    return cmd_rewrite(root)


if __name__ == "__main__":
    sys.exit(main())
