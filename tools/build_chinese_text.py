from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import re
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Chinese text build requires Pillow: python -m pip install pillow") from exc


ROOT = Path(__file__).resolve().parents[1]
FONT_VERSION = "v2026.05.07"
FONT_RELEASE_TAG = FONT_VERSION.removeprefix("v")
FONT_PACKAGE_SIZE = 12
FONT_ARCHIVE = f"fusion-pixel-font-{FONT_PACKAGE_SIZE}px-monospaced-bdf-{FONT_VERSION}.zip"
FONT_URL = f"https://github.com/TakWolf/fusion-pixel-font/releases/download/{FONT_RELEASE_TAG}/{FONT_ARCHIVE}"
DEFAULT_FONT_DIR = ROOT / "tools" / f"fusion-pixel-font-{FONT_PACKAGE_SIZE}px-monospaced-bdf-{FONT_VERSION}"
DEFAULT_FONT = DEFAULT_FONT_DIR / f"fusion-pixel-{FONT_PACKAGE_SIZE}px-monospaced-zh_hans.bdf"
DEFAULT_OUT = ROOT / "build" / "chinese"
DEFAULT_MAP = ROOT / "tools" / "translation_map.tsv"
DEFAULT_TRANSLATIONS = ROOT / "translations" / "zh-Hans" / "text.tsv"
MANIFEST = ROOT / "gfx" / "font" / "chinese_chars.tsv"
ASM_SUFFIX = ".asm"
GLYPH_SIZE = 16
TILE_SIZE = 8
MAX_CHINESE_CHARS = 1024
CHINESE_FONT_BANK_CHARS = 512
TOKEN_PREFIX = "CN"
INCLUDE_RE = re.compile(r'^(\s*INCLUDE\s+")([^"]+)(".*)$')
STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
CHARMAP_RE = re.compile(r'^\s*charmap\s+"((?:[^"\\]|\\.)*)"')


def read_base_charmap_chars() -> set[str]:
    chars: set[str] = set()
    charmap_path = ROOT / "constants" / "charmap.asm"
    for line in charmap_path.read_text(encoding="utf-8").splitlines():
        match = CHARMAP_RE.match(line)
        if not match:
            continue
        text = match.group(1)
        if len(text) == 1 and ord(text) >= 0x80:
            chars.add(text)
    return chars


BASE_CHARMAP_CHARS = read_base_charmap_chars()


@dataclass(frozen=True)
class BdfGlyph:
    width: int
    height: int
    x_offset: int
    y_offset: int
    bitmap: tuple[str, ...]


@dataclass(frozen=True)
class BdfFont:
    width: int
    height: int
    ascent: int
    descent: int
    glyphs: dict[int, BdfGlyph]


def uses_chinese_font(char: str) -> bool:
    return ord(char) >= 0x80 and char not in BASE_CHARMAP_CHARS


def iter_asm_files(root: Path) -> list[Path]:
    ignored = {".git", "build", "tools"}
    result: list[Path] = []
    for path in root.rglob(f"*{ASM_SUFFIX}"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in ignored:
            continue
        result.append(path)
    return sorted(result)


def collect_font_chars_from_texts(texts) -> list[str]:
	chars: list[str] = []
	seen: set[str] = set()
	for text in texts:
		for char in text:
			if uses_chinese_font(char) and char not in seen:
				seen.add(char)
				chars.append(char)
	return chars


def read_existing_chars() -> list[str]:
    if not MANIFEST.exists():
        return []
    chars: list[str] = []
    seen: set[str] = set()
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1] not in seen:
            seen.add(parts[1])
            chars.append(parts[1])
    return chars


def merge_chars(existing: list[str], discovered: list[str]) -> list[str]:
	chars: list[str] = []
	seen: set[str] = set()
	for char in existing:
		if char in discovered and char not in seen:
			seen.add(char)
			chars.append(char)
	for char in discovered:
		if char not in seen:
			seen.add(char)
			chars.append(char)
	return chars


def read_tsv(path: Path) -> list[dict[str, str]]:
	with path.open("r", encoding="utf-8-sig", newline="") as handle:
		return list(csv.DictReader(handle, delimiter="\t"))


def ensure_font(path: Path) -> Path:
    if path.exists():
        return path

    if path != DEFAULT_FONT:
        raise SystemExit(f"Chinese font not found: {path}")

    archive_path = ROOT / "tools" / "downloads" / FONT_ARCHIVE
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        print(f"Downloading Fusion Pixel Font {FONT_PACKAGE_SIZE}px package from {FONT_URL}")
        try:
            urllib.request.urlretrieve(FONT_URL, archive_path)
        except urllib.error.URLError as exc:
            raise SystemExit(f"Could not download Fusion Pixel Font {FONT_PACKAGE_SIZE}px package: {exc}") from exc

    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(DEFAULT_FONT_DIR)

    if not path.exists():
        raise SystemExit(f"Fusion Pixel Font {FONT_PACKAGE_SIZE}px archive did not contain {path.name}")
    return path


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


def read_translations(path: Path) -> dict[str, str]:
	translations: dict[str, str] = {}
	for row in read_tsv(path):
		text_id = row.get("id", "").strip()
		translation = row.get("translation", "")
		if text_id and translation:
			translations[text_id] = translation
	return translations


def normalize_translation(text: str, source: str = "") -> str:
    text = text.replace(r"\n", "<LF>")
    if source.endswith("@") and text and not text.endswith("@"):
        text += "@"
    return text


def build_line_translations(rows: list[dict[str, str]]) -> dict[tuple[Path, int, int], str]:
    translations: dict[tuple[Path, int, int], str] = {}
    for row in rows:
        translation = row.get("translation", "")
        if not translation:
            continue
        file_path = row.get("file", "").strip()
        line_number = row.get("line", "").strip()
        string_index = row.get("string_index", "").strip()
        if not file_path or not line_number or not string_index:
            continue
        try:
            key = (Path(file_path), int(line_number), int(string_index))
        except ValueError:
            continue
        translations[key] = normalize_translation(translation, row.get("source", ""))
    return translations


def build_source_translation_queues(rows: list[dict[str, str]]) -> tuple[dict[Path, dict[str, Deque[str]]], int]:
    translations: dict[Path, dict[str, Deque[str]]] = defaultdict(lambda: defaultdict(deque))
    count = 0
    for row in rows:
        translation = row.get("translation", "")
        file_path = row.get("file", "").strip()
        source = row.get("source", "")
        if not translation or not file_path:
            continue
        translations[Path(file_path)][source].append(normalize_translation(translation, source))
        count += 1
    return {path: dict(source_map) for path, source_map in translations.items()}, count


def display_width(text: str) -> int:
	return sum(2 if uses_chinese_font(char) else 1 for char in text)


def asm_string(text: str) -> str:
	return text.replace("\\", "\\\\").replace('"', '\\"')


def translation_lines(text: str, terminator: str, text_id: str) -> list[str]:
	lines: list[str] = []
	for paragraph_index, paragraph in enumerate(text.split(r"\p")):
		for line_index, line in enumerate(paragraph.split(r"\n")):
			if display_width(line) > 18:
				raise SystemExit(f"{text_id}: line is wider than the 18-tile textbox: {line}")
			if paragraph_index == 0 and line_index == 0:
				macro = "text"
			elif line_index == 0:
				macro = "para"
			else:
				macro = "line"
			lines.append(f'\t{macro} "{asm_string(line)}"\n')
	lines.append(f"\t{terminator}\n")
	return lines


def build_replacements(map_path: Path, translations: dict[str, str]) -> dict[Path, dict[str, list[str]]]:
	replacements: dict[Path, dict[str, list[str]]] = {}
	for row in read_tsv(map_path):
		text_id = row.get("id", "").strip()
		translation = translations.get(text_id)
		if not translation:
			continue
		file_path = Path(row["file"])
		label = row["label"].strip()
		terminator = row["terminator"].strip()
		replacements.setdefault(file_path, {})[label] = translation_lines(translation, terminator, text_id)
	return replacements


def apply_replacements(rel: Path, lines: list[str], replacements: dict[Path, dict[str, list[str]]]) -> list[str]:
	file_replacements = replacements.get(rel)
	if not file_replacements:
		return lines

	result: list[str] = []
	index = 0
	while index < len(lines):
		stripped = lines[index].strip()
		if stripped.endswith("::") and stripped[:-2] in file_replacements:
			label = stripped[:-2]
			result.append(lines[index])
			result.extend(file_replacements[label])
			index += 1
			while index < len(lines) and lines[index].strip() not in {"done", "prompt", "text_end"}:
				index += 1
			if index < len(lines):
				index += 1
			continue
		result.append(lines[index])
		index += 1
	return result


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def iter_string_chars(line: str):
    in_string = False
    escaped = False
    for char in line:
        if char == ";" and not in_string:
            return
        if char == '"' and not escaped:
            in_string = not in_string
        elif in_string:
            yield char
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False


def load_bdf_font(path: Path) -> BdfFont:
    width = FONT_PACKAGE_SIZE
    height = FONT_PACKAGE_SIZE
    ascent = FONT_PACKAGE_SIZE
    descent = 0
    glyphs: dict[int, BdfGlyph] = {}
    encoding: int | None = None
    bbx: tuple[int, int, int, int] | None = None
    bitmap: list[str] = []
    in_bitmap = False

    for raw_line in path.read_text(encoding="ascii", errors="strict").splitlines():
        line = raw_line.strip()
        parts = line.split()
        if not parts:
            continue
        keyword = parts[0]

        if keyword == "FONTBOUNDINGBOX" and len(parts) >= 5:
            width, height = int(parts[1]), int(parts[2])
            continue
        if keyword == "FONT_ASCENT" and len(parts) >= 2:
            ascent = int(parts[1])
            continue
        if keyword == "FONT_DESCENT" and len(parts) >= 2:
            descent = int(parts[1])
            continue
        if keyword == "STARTCHAR":
            encoding = None
            bbx = None
            bitmap = []
            in_bitmap = False
            continue
        if keyword == "ENCODING" and len(parts) >= 2:
            encoding = int(parts[1])
            continue
        if keyword == "BBX" and len(parts) >= 5:
            bbx = (int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
            continue
        if keyword == "BITMAP":
            bitmap = []
            in_bitmap = True
            continue
        if keyword == "ENDCHAR":
            if encoding is not None and encoding >= 0 and bbx is not None:
                glyphs[encoding] = BdfGlyph(*bbx, tuple(bitmap))
            in_bitmap = False
            continue
        if in_bitmap:
            bitmap.append(line)

    return BdfFont(width, max(height, ascent + descent), ascent, descent, glyphs)


def render_bdf_glyph(font: BdfFont, char: str) -> Image.Image:
    glyph = font.glyphs.get(ord(char))
    if glyph is None:
        raise SystemExit(f"{DEFAULT_FONT.name} does not contain glyph U+{ord(char):04X} ({char})")

    glyph_image = Image.new("L", (glyph.width, glyph.height), 255)
    pixels = glyph_image.load()
    for y, row in enumerate(glyph.bitmap[:glyph.height]):
        bits = int(row, 16)
        bit_count = len(row) * 4
        for x in range(glyph.width):
            if bits & (1 << (bit_count - 1 - x)):
                pixels[x, y] = 0

    em_image = Image.new("L", (font.width, font.height), 255)
    x = max(0, glyph.x_offset)
    y = font.ascent - glyph.y_offset - glyph.height
    x = max(0, min(font.width - glyph.width, x))
    y = max(0, min(font.height - glyph.height, y))
    em_image.paste(glyph_image, (x, y))

    image = Image.new("L", (GLYPH_SIZE, GLYPH_SIZE), 255)
    image.paste(em_image, ((GLYPH_SIZE - font.width) // 2, GLYPH_SIZE - font.height))
    return image


def glyph_to_1bpp_tiles(image: Image.Image) -> bytes:
    data = bytearray()
    pixels = image.load()
    for tile_y in (0, TILE_SIZE):
        for tile_x in (0, TILE_SIZE):
            for y in range(TILE_SIZE):
                value = 0
                for x in range(TILE_SIZE):
                    if pixels[tile_x + x, tile_y + y] < 128:
                        value |= 1 << (7 - x)
                data.append(value)
    return bytes(data)


def blank_glyph_bytes() -> bytes:
    return bytes(TILE_SIZE * 4)


def write_font(font_path: Path, chars: list[str]) -> bool:
    font = load_bdf_font(font_path)
    font_banks = [bytearray(), bytearray()]
    preview = Image.new("L", (max(1, len(chars)) * GLYPH_SIZE, GLYPH_SIZE), 255)

    for index, char in enumerate(chars):
        glyph = render_bdf_glyph(font, char)
        bank = index // CHINESE_FONT_BANK_CHARS
        font_banks[bank].extend(glyph_to_1bpp_tiles(glyph))
        preview.paste(glyph, (index * GLYPH_SIZE, 0))

    for bank_data in font_banks:
        if not bank_data:
            bank_data.extend(blank_glyph_bytes())

    changed = False
    for bank, bank_data in enumerate(font_banks):
        changed |= write_bytes_if_changed(ROOT / "gfx" / "font" / f"chinese_{bank}.1bpp", bytes(bank_data))
    preview_path = ROOT / "gfx" / "font" / "chinese_preview.png"
    old_preview = preview_path.read_bytes() if preview_path.exists() else None
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.resize((preview.width * 8, preview.height * 8), Image.Resampling.NEAREST).save(preview_path)
    if old_preview == preview_path.read_bytes():
        return changed
    return True


def write_generated_includes(chars: list[str]) -> bool:
    charmap_lines = [
        "; Generated by tools/build_chinese_text.py. Do not edit by hand.",
        "",
    ]
    for index, char in enumerate(chars):
        token = f"<{TOKEN_PREFIX}{index:03X}>"
        low = index & 0xff
        high = index >> 8
        charmap_lines.append(f'\tcharmap "{token}", $17, ${low:02x}, ${high:02x} ; {char}')
    changed = write_text_if_changed(ROOT / "constants" / "chinese_charmap.asm", "\n".join(charmap_lines) + "\n")

    constants = [
        "; Generated by tools/build_chinese_text.py. Do not edit by hand.",
        f"DEF CHINESE_FONT_CHARS EQU {max(1, len(chars))}",
        f"DEF CHINESE_FONT_MAX_CHARS EQU {MAX_CHINESE_CHARS}",
    ]
    changed |= write_text_if_changed(ROOT / "constants" / "chinese_font_constants.asm", "\n".join(constants) + "\n")

    manifest = [f"{index:02X}\t{char}" for index, char in enumerate(chars)]
    changed |= write_text_if_changed(MANIFEST, "\n".join(manifest) + "\n")
    return changed


def replace_line_strings(line: str, source_translations: dict[str, Deque[str]]) -> str:
    if not source_translations:
        return line

    result: list[str] = []
    last_end = 0
    for start, end, source in iter_string_spans(line):
        result.append(line[last_end:start])
        queue = source_translations.get(source)
        text = queue.popleft() if queue else source
        result.append(asm_string(text))
        last_end = end
    result.append(line[last_end:])
    return "".join(result)


def convert_line(
    line: str,
    char_to_token: dict[str, str],
    out_root: Path,
    source_translations: dict[str, Deque[str]] | None = None,
) -> str:
    ending = ""
    if line.endswith("\r\n"):
        line, ending = line[:-2], "\r\n"
    elif line.endswith("\n"):
        line, ending = line[:-1], "\n"

    include_match = INCLUDE_RE.match(line)
    if include_match:
        include_path = include_match.group(2)
        if include_path.endswith(ASM_SUFFIX) and not include_path.startswith(str(out_root).replace("\\", "/")):
            return f'{include_match.group(1)}{out_root.as_posix()}/{include_path}{include_match.group(3)}{ending}'

    line = replace_line_strings(line, source_translations or {})
    result: list[str] = []
    in_string = False
    escaped = False
    for offset, char in enumerate(line):
        if char == ";" and not in_string:
            result.append(char)
            result.append(line[offset + 1 :])
            break
        if char == '"' and not escaped:
            in_string = not in_string
            result.append(char)
            continue
        if in_string and char in char_to_token:
            result.append(char_to_token[char])
        else:
            result.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return "".join(result) + ending


def write_preprocessed_sources(
    files: list[Path],
    out_root: Path,
    chars: list[str],
    replacements: dict[Path, dict[str, list[str]]],
    source_translations: dict[Path, dict[str, Deque[str]]],
) -> bool:
    if out_root.exists():
        for stale in out_root.rglob(f"*{ASM_SUFFIX}"):
            stale.unlink()
    out_root.mkdir(parents=True, exist_ok=True)

    changed = False
    char_to_token = {char: f"<{TOKEN_PREFIX}{index:03X}>" for index, char in enumerate(chars)}
    for path in files:
        rel = path.relative_to(ROOT)
        out_path = out_root / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        lines = apply_replacements(rel, lines, replacements)
        file_source_translations = {
            source: deque(translations)
            for source, translations in source_translations.get(rel, {}).items()
        }
        converted_lines: list[str] = []
        for line in lines:
            converted_lines.append(convert_line(line, char_to_token, out_root, file_source_translations))
        converted = "".join(converted_lines)
        changed |= write_text_if_changed(out_path, converted)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", default=DEFAULT_FONT, type=Path)
    parser.add_argument("--map", default=DEFAULT_MAP, type=Path)
    parser.add_argument("--translations", default=DEFAULT_TRANSLATIONS, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()

    translation_rows = read_tsv(args.translations)
    translations = {
        row.get("id", "").strip(): row.get("translation", "")
        for row in translation_rows
        if row.get("id", "").strip() and row.get("translation", "")
    }
    source_translations, source_translation_count = build_source_translation_queues(translation_rows)
    replacements = build_replacements(args.map, translations)
    chars = merge_chars(read_existing_chars(), collect_font_chars_from_texts(translations.values()))
    if len(chars) > MAX_CHINESE_CHARS:
        raise SystemExit(
            f"Chinese font contains {len(chars)} unique generated characters; "
            f"the current VRAM-bank-1 renderer supports {MAX_CHINESE_CHARS}."
        )

    changed = False
    changed |= write_font(ensure_font(args.font), chars)
    changed |= write_generated_includes(chars)
    files = iter_asm_files(ROOT)
    changed |= write_preprocessed_sources(files, args.out, chars, replacements, source_translations)
    stamp = args.out / "stamp"
    if changed or not stamp.exists():
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text("ok\n", encoding="utf-8")
    print(
        f"Chinese text build: {len(chars)} generated chars, "
        f"{source_translation_count} string(s) translated, "
        f"{len(replacements)} asm file(s) patched, {len(files)} asm files"
    )


if __name__ == "__main__":
    main()
