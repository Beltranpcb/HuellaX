#!/usr/bin/env python3
"""Static checks for the HuellaX cover/docs integration.

No third-party dependencies, no build, no network. Run from anywhere:

    python3 scripts/check_docs.py

Checks:
  1. UTF-8 decodability of the cover and documentation files.
  2. Local links in index.html (href/src) resolve to existing paths.
  3. Local links in README.md / README.es.md / INTEGRATION.md resolve.
  4. README language switch is present and Chinese is labelled legacy.
  5. index.html i18n key coverage: every data-i18n* key exists in both
     the EN and ES dictionaries; dictionary key sets match.
  6. index.html supports ?lang=en|es, localStorage, and English default.
  7. Required honesty statements are present.
  8. Basic HTML tag balance and duplicate id detection.

Exit code 0 means all checks passed; 1 means at least one failure.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

UTF8_FILES = [
    "index.html",
    "README.md",
    "README.es.md",
    "README.zh-CN.md",
    "INTEGRATION.md",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "REFERENCES.md",
]

MARKDOWN_FILES = ["README.md", "README.es.md", "INTEGRATION.md", "REFERENCES.md", "THIRD_PARTY_NOTICES.md", "README.zh-CN.md"]

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "ftp:", "data:", "javascript:")

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

failures: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def ok(message: str) -> None:
    notes.append(message)


def read_text(rel: str) -> str:
    path = ROOT / rel
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing file: {rel}")
        return ""
    except UnicodeDecodeError as exc:
        fail(f"not valid UTF-8: {rel} ({exc})")
        return ""


# --------------------------------------------------------------------------- UTF-8

for rel in UTF8_FILES:
    text = read_text(rel)
    if text:
        ok(f"UTF-8: {rel}")

for rel in MARKDOWN_FILES + ["index.html"]:
    if not (ROOT / rel).exists():
        fail(f"required deliverable missing: {rel}")

# ---------------------------------------------------------------- local link checks

def local_target_exists(source_rel: str, raw_target: str) -> tuple[bool, str]:
    target = raw_target.strip()
    if not target:
        return True, ""
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    else:
        target = target.split()[0] if target.split() else target
    if target.startswith("#"):
        return True, ""
    if target.lower().startswith(EXTERNAL_PREFIXES):
        return True, ""
    if target.startswith("//"):
        return True, ""

    parts = urlsplit(target)
    path_part = unquote(parts.path)
    if not path_part:
        return True, ""

    source = ROOT / source_rel
    if path_part.startswith("/"):
        resolved = (ROOT / path_part.lstrip("/")).resolve()
    else:
        resolved = (source.parent / path_part).resolve()

    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return False, f"escapes repository: {raw_target}"
    return resolved.exists(), f"missing: {raw_target}"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.links.append((key, value))


def check_html_links(rel: str) -> int:
    text = read_text(rel)
    if not text:
        return 0
    parser = LinkParser()
    parser.feed(text)
    count = 0
    for attr, target in parser.links:
        exists, problem = local_target_exists(rel, target)
        count += 1
        if not exists:
            fail(f"{rel}: {attr}={target!r} -> {problem}")
    ok(f"HTML local links: {rel} ({count} checked)")
    return count


def strip_markdown_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def check_markdown_links(rel: str) -> int:
    text = strip_markdown_code(read_text(rel))
    count = 0
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        raw = match.group(1).strip()
        exists, problem = local_target_exists(rel, raw)
        count += 1
        if not exists:
            fail(f"{rel}: markdown link {raw!r} -> {problem}")
    ok(f"Markdown local links: {rel} ({count} checked)")
    return count


check_html_links("index.html")
for rel in MARKDOWN_FILES:
    check_markdown_links(rel)

# --------------------------------------------------------------- README language

readme_en = read_text("README.md")
readme_es = read_text("README.es.md")

head_en = "\n".join(readme_en.splitlines()[:45])
head_es = "\n".join(readme_es.splitlines()[:45])

if re.search(r"\*\*English\*\*\s*\|\s*\[Español\]\(README\.es\.md\)", head_en):
    ok("README.md language switch: English | Español")
else:
    fail("README.md: top 'English | Español' switch missing or malformed")

if re.search(r"\[English\]\(README\.md\)\s*\|\s*\*\*Español\*\*", head_es):
    ok("README.es.md language switch: English | Español")
else:
    fail("README.es.md: top 'English | Español' switch missing or malformed")

if "[中文](README.zh-CN.md)" in readme_en and re.search(
    r"legacy[^\n]*README\.zh-CN\.md|README\.zh-CN\.md[^\n]*legacy", readme_en, re.I
):
    ok("README.md: Chinese README linked as legacy")
else:
    fail("README.md: Chinese README is not linked explicitly as legacy")

if "[中文](README.zh-CN.md)" in readme_es and re.search(
    r"legacy[^\n]*README\.zh-CN\.md|README\.zh-CN\.md[^\n]*legacy", readme_es, re.I
):
    ok("README.es.md: Chinese README linked as legacy")
else:
    fail("README.es.md: Chinese README is not linked explicitly as legacy")

if re.search(r"\|\s*\*\*中文\*\*", readme_en) or re.search(r"\|\s*\*\*中文\*\*", readme_es):
    fail("a README still presents Chinese as a primary language choice")
else:
    ok("Chinese is not presented as a primary README language")

# -------------------------------------------------------------------- index i18n

index = read_text("index.html")

used_keys = set(
    re.findall(r'data-i18n(?:-html|-aria|-alt)?="([^"]+)"', index)
)
match = re.search(
    r"var I18N = \{\s*en: \{(.*?)\n    \},\s*es: \{(.*?)\n    \}\s*\};",
    index,
    re.S,
)
if not match:
    fail("index.html: could not parse the EN/ES I18N dictionaries")
    en_keys: set[str] = set()
    es_keys: set[str] = set()
else:
    def dict_keys(block: str) -> set[str]:
        return set(re.findall(r"^\s*([A-Za-z0-9_]+):", block, re.M))

    en_keys = dict_keys(match.group(1))
    es_keys = dict_keys(match.group(2))

    missing_en = used_keys - en_keys
    missing_es = used_keys - es_keys
    if missing_en:
        fail(f"index.html: data-i18n keys missing from EN dict: {sorted(missing_en)}")
    if missing_es:
        fail(f"index.html: data-i18n keys missing from ES dict: {sorted(missing_es)}")
    if en_keys != es_keys:
        fail(
            "index.html: EN/ES dictionary key sets differ: "
            f"EN-only={sorted(en_keys - es_keys)}, ES-only={sorted(es_keys - en_keys)}"
        )
    if not missing_en and not missing_es and en_keys == es_keys:
        ok(f"index.html i18n: {len(used_keys)} keys covered in EN and ES")
    if len(used_keys) < 100:
        fail(f"index.html: suspiciously few i18n keys ({len(used_keys)})")

    # The two dictionaries must have no empty values.
    for lang, block in (("EN", match.group(1)), ("ES", match.group(2))):
        for key, value in re.findall(r'^\s*([A-Za-z0-9_]+):\s*"([^"]*)"', block, re.M):
            if not value.strip():
                fail(f"index.html: empty {lang} translation for {key}")

# Required language machinery.
for needle, description in [
    ("URLSearchParams", "URL query parsing"),
    ("localStorage", "localStorage persistence"),
    ('searchParams.set("lang"', "?lang= URL update"),
    ('document.documentElement.lang = lang', "<html lang> update"),
    ("data-set-lang", "language selector buttons"),
]:
    if needle in index:
        ok(f"index.html language machinery: {description}")
    else:
        fail(f"index.html: missing language machinery: {description}")

if re.search(r'<html\s+lang="en"', index):
    ok("index.html: English is the default document language")
else:
    fail("index.html: <html lang=\"en\"> default missing")

if 'return "en";' in index:
    ok("index.html: English fallback in initial language resolution")
else:
    fail("index.html: English fallback missing in initial language resolution")

# ------------------------------------------------------------ required statements

def require(rel: str, text: str, pattern: str, description: str) -> None:
    if re.search(pattern, text, re.I):
        ok(f"{rel}: {description}")
    else:
        fail(f"{rel}: missing required statement: {description}")


require(
    "README.md",
    readme_en,
    r"SQL is the primary data source",
    "SQL is the primary data source",
)
require(
    "README.es.md",
    readme_es,
    r"SQL es la fuente de datos principal",
    "SQL es la fuente de datos principal",
)
require("README.md", readme_en, r"AstroNova[^\n]*legacy|legacy[^\n]*AstroNova", "AstroNova is legacy")
require(
    "README.es.md",
    readme_es,
    r"AstroNova[^\n]*legacy|legacy[^\n]*AstroNova",
    "AstroNova es legacy",
)
require(
    "README.md",
    readme_en,
    r"candidate, not a discovery",
    "candidate, not a discovery",
)
require(
    "README.es.md",
    readme_es,
    r"candidato, no un descubrimiento|candidato, no descubrimiento",
    "candidato, no descubrimiento",
)
require("README.md", readme_en, r"Planet X", "Planet X boundary is mentioned")
require("README.es.md", readme_es, r"Planeta X", "Planeta X boundary is mentioned")
require(
    "README.md",
    readme_en,
    r"discovery_claim",
    "discovery_claim boundary",
)
require("INTEGRATION.md", read_text("INTEGRATION.md"), r"candidate, not a discovery", "candidate, not a discovery")
require("INTEGRATION.md", read_text("INTEGRATION.md"), r"SQL is the primary data source", "SQL is the primary data source")
require("INTEGRATION.md", read_text("INTEGRATION.md"), r"1253925ab13419b5d44db323548784c939a93a6e", "upstream SHA")

require("index.html", index, r"SQL is the primary data source", "EN SQL primary statement")
require("index.html", index, r"SQL es la fuente de datos principal", "ES SQL primary statement")
require("index.html", index, r"Candidate, not discovery", "EN candidate-not-discovery")
require("index.html", index, r"Candidato, no descubrimiento", "ES candidate-not-discovery")
require("index.html", index, r"AstroNova static data is legacy/demo", "EN AstroNova legacy/demo")
require(
    "index.html",
    index,
    r"Los datos estáticos de AstroNova son legacy/demostración",
    "ES AstroNova legacy/demo",
)

# ------------------------------------------------------- HTML structure checks

class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if "id" in attr_map and attr_map["id"]:
            self.ids.append(attr_map["id"])
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        attr_map = dict(attrs)
        if "id" in attr_map and attr_map["id"]:
            self.ids.append(attr_map["id"])

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"unexpected closing </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.errors.append(
                f"mis-nested </{tag}>; open stack tail={self.stack[-4:]}"
            )
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"closing </{tag}> with no matching open tag")


if index:
    parser = StructureParser()
    parser.feed(index)
    if parser.errors:
        for error in parser.errors[:8]:
            fail(f"index.html structure: {error}")
    if parser.stack:
        fail(f"index.html structure: unclosed tags {parser.stack[-8:]}")
    if not parser.errors and not parser.stack:
        ok("index.html: HTML tag balance")
    duplicates = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if duplicates:
        fail(f"index.html: duplicate ids: {duplicates}")
    else:
        ok(f"index.html: unique ids ({len(parser.ids)} checked)")

# ------------------------------------------------------------------------- report

print("HuellaX cover/docs static checks")
print(f"root: {ROOT}")
for message in notes:
    print(f"  PASS  {message}")
if failures:
    print()
    for message in failures:
        print(f"  FAIL  {message}")
    print(f"\nRESULT: FAIL ({len(failures)} problem(s))")
    sys.exit(1)

print(f"\nRESULT: PASS ({len(notes)} checks)")
