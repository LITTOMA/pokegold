from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "translations" / "zh-Hans" / "text.tsv"
SCAN_ROOTS = ("data", "engine", "home")
ALLOWED_KINDS = {
    "cont",
    "db",
    "dbw",
    "dname",
    "li",
    "line",
    "next",
    "page",
    "para",
    "text",
    "unownword",
}
SKIP_KINDS = {"include", "incbin", "charmap"}
MENU_FILES = {
    "data/battle/stat_names.asm",
    "data/items/pocket_names.asm",
    "data/mon_menu.asm",
    "data/player_names.asm",
    "engine/battle/menu.asm",
    "engine/events/bug_contest/display_stats.asm",
    "engine/events/diploma.asm",
    "engine/events/elevator.asm",
    "engine/events/mom.asm",
    "engine/events/pokecenter_pc.asm",
    "engine/events/print_unown.asm",
    "engine/items/buy_sell_toss.asm",
    "engine/items/mart.asm",
    "engine/items/pack.asm",
    "engine/items/tmhm.asm",
    "engine/menus/delete_save.asm",
    "engine/menus/intro_menu.asm",
    "engine/menus/main_menu.asm",
    "engine/menus/menu_2.asm",
    "engine/menus/menu.asm",
    "engine/menus/naming_screen.asm",
    "engine/menus/options_menu.asm",
    "engine/menus/scrolling_menu.asm",
    "engine/menus/start_menu.asm",
    "engine/menus/trainer_card.asm",
    "engine/overworld/decorations.asm",
    "engine/overworld/select_menu.asm",
    "engine/pokedex/pokedex.asm",
    "engine/pokedex/pokedex_2.asm",
    "engine/pokedex/pokedex_3.asm",
    "engine/pokegear/pokegear.asm",
    "engine/pokegear/radio.asm",
    "engine/pokemon/mon_menu.asm",
    "engine/pokemon/mon_stats.asm",
    "engine/pokemon/mon_submenu.asm",
    "engine/pokemon/move_mon.asm",
    "engine/pokemon/party_menu.asm",
    "engine/pokemon/stats_screen.asm",
    "engine/rtc/print_hours_mins.asm",
    "engine/rtc/reset_password.asm",
    "engine/rtc/restart_clock.asm",
    "engine/rtc/timeset.asm",
    "home/menu.asm",
    "home/names.asm",
    "home/text.asm",
    "home/text_command_strings.asm",
}
MENU_PREFIXES = (
    "engine/link/",
)
TOKEN_RE = re.compile(r"[A-Za-z_.$][A-Za-z0-9_.$]*")
FIELDNAMES = ("id", "category", "file", "line", "string_index", "kind", "source", "translation")


def iter_asm_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        for path in (ROOT / root_name).rglob("*.asm"):
            files.append(path)
    return sorted(files)


def read_existing_translations(
    path: Path,
) -> tuple[
    dict[tuple[str, str, str, str], str],
    dict[tuple[str, str, str], str],
    dict[tuple[str, str, str], str],
]:
    if not path.exists():
        return {}, {}, {}
    translations: dict[tuple[str, str, str, str], str] = {}
    source_translations: dict[tuple[str, str, str], set[str]] = {}
    global_source_translations: dict[tuple[str, str, str], set[str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            translation = row.get("translation", "")
            if not translation:
                continue
            source_key = (
                row.get("file", ""),
                row.get("string_index", ""),
                row.get("source", ""),
            )
            source_translations.setdefault(source_key, set()).add(translation)
            global_source_key = (
                row.get("category", ""),
                row.get("string_index", ""),
                row.get("source", ""),
            )
            global_source_translations.setdefault(global_source_key, set()).add(translation)
            key = (
                row.get("file", ""),
                row.get("line", ""),
                row.get("string_index", ""),
                row.get("source", ""),
            )
            translations[key] = translation
    stable_sources = {
        key: next(iter(values))
        for key, values in source_translations.items()
        if len(values) == 1
    }
    stable_global_sources = {
        key: next(iter(values))
        for key, values in global_source_translations.items()
        if len(values) == 1
    }
    return translations, stable_sources, stable_global_sources


def extract_kind(line: str, first_quote: int) -> str:
    prefix = line[:first_quote]
    prefix = prefix.strip()
    if ":" in prefix:
        prefix = prefix.rsplit(":", 1)[1].strip()
    tokens = TOKEN_RE.findall(prefix)
    if not tokens:
        return ""
    return tokens[0].lower()


def iter_string_spans(line: str):
    index = 0
    while index < len(line):
        char = line[index]
        if char == ";":
            return
        if char != '"':
            index += 1
            continue
        start = index + 1
        index = start
        escaped = False
        while index < len(line):
            char = line[index]
            if char == '"' and not escaped:
                yield start, index, line[start:index]
                index += 1
                break
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
            index += 1


def category_for(rel: str) -> str:
    if rel in MENU_FILES or any(rel.startswith(prefix) for prefix in MENU_PREFIXES):
        return "menu"
    if rel.startswith("engine/debug/"):
        return "debug"
    return "text"


def make_id(rel: str, line_number: int, string_index: int) -> str:
    stem = rel.removesuffix(".asm").replace("/", ".").replace("\\", ".")
    safe = re.sub(r"[^A-Za-z0-9_.]+", "_", stem)
    return f"{safe}:{line_number}:{string_index}"


def export_rows(
    existing: dict[tuple[str, str, str, str], str],
    stable_sources: dict[tuple[str, str, str], str],
    stable_global_sources: dict[tuple[str, str, str], str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in iter_asm_files():
        rel = path.relative_to(ROOT).as_posix()
        category = category_for(rel)
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            spans = list(iter_string_spans(line))
            if not spans:
                continue
            kind = extract_kind(line, spans[0][0] - 1)
            if kind in SKIP_KINDS or kind not in ALLOWED_KINDS:
                continue
            for string_index, (_, _, source) in enumerate(spans):
                key = (rel, str(line_number), str(string_index), source)
                source_key = (rel, str(string_index), source)
                global_source_key = (category, str(string_index), source)
                translation = existing.get(
                    key,
                    stable_sources.get(source_key, stable_global_sources.get(global_source_key, "")),
                )
                rows.append(
                    {
                        "id": make_id(rel, line_number, string_index),
                        "category": category,
                        "file": rel,
                        "line": str(line_number),
                        "string_index": str(string_index),
                        "kind": kind,
                        "source": source,
                        "translation": translation,
                    }
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()

    existing, stable_sources, stable_global_sources = read_existing_translations(args.out)
    rows = export_rows(existing, stable_sources, stable_global_sources)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDNAMES, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} strings to {args.out}")


if __name__ == "__main__":
    main()
