# Translation Workflow

Translators edit only files under `translations/`. Do not edit `.asm` files for
translation work; those are source/generated build files maintained by the build
system.

For Simplified Chinese, edit `translations/zh-Hans/text.tsv` with a normal UTF-8 text editor.

- `id`: stable text identifier.
- `source`: reference English text.
- `translation`: translated text. Use `\n` for a new line and `\p` for a new paragraph.

During `make`, `tools/build_chinese_text.py` injects translations into a generated `build/chinese/` ASM tree, converts official Fusion Pixel 12px BDF Chinese glyphs into GB 2x2 tile cells, and emits the charmap used by the ROM build.

Build requirements:

- Python with Pillow installed.
- Internet access on the first build, or a local copy of
  `fusion-pixel-12px-monospaced-zh_hans.bdf` passed with
  `tools/build_chinese_text.py --font`.

Generated files, downloaded fonts, toolchains, ROMs, save files, and smoke-test
screenshots are ignored by git.
