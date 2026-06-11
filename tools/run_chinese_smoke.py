from __future__ import annotations

import argparse
import io
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYBOY_VENDOR = ROOT / "tools" / "pyboy"


def add_pyboy_path() -> None:
    if PYBOY_VENDOR.exists():
        sys.path.insert(0, str(PYBOY_VENDOR))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", default=str(ROOT / "pokegold.gbc"), type=Path)
    parser.add_argument("--out-dir", default=str(ROOT / "tools" / "screenshots"), type=Path)
    args = parser.parse_args()

    add_pyboy_path()
    try:
        from pyboy import PyBoy
    except ImportError as exc:
        raise SystemExit("Chinese smoke test requires PyBoy: python -m pip install pyboy") from exc

    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = args.out_dir / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    smoke_rom = run_dir / "pokegold_smoke.gbc"
    shutil.copy2(args.rom, smoke_rom)

    for save_file in (
        smoke_rom.with_suffix(".ram"),
        smoke_rom.with_suffix(".rtc"),
        Path(f"{smoke_rom}.ram"),
        Path(f"{smoke_rom}.rtc"),
    ):
        if save_file.exists():
            save_file.unlink()

    empty_ram = io.BytesIO(bytes([0xFF]) * 32768)
    pyboy = PyBoy(str(smoke_rom), ram_file=empty_ram, window="null")
    pyboy.set_emulation_speed(0)

    def step(frames: int) -> None:
        if frames <= 0:
            return
        if frames == 1:
            pyboy.tick(1, True, False)
            return
        pyboy.tick(frames - 1, False, False)
        pyboy.tick(1, True, False)

    def tap(button: str, hold_frames: int = 8, after_frames: int = 30) -> None:
        pyboy.button(button, hold_frames)
        step(hold_frames + after_frames)

    def shot(name: str) -> Path:
        path = args.out_dir / f"{name}.png"
        pyboy.screen.image.save(path)
        print(path, flush=True)
        return path

    try:
        step(600)
        shot("00_after_boot")
        tap("start", after_frames=90)
        shot("01_after_start")
        tap("a", after_frames=700)
        shot("02_main_menu")
        tap("down", hold_frames=12, after_frames=80)
        shot("03_main_menu_option_selected")
        tap("a", hold_frames=12, after_frames=420)
        final_shot = shot("04_options_menu")
        shutil.copy2(final_shot, args.out_dir / "chinese_smoke.png")
    finally:
        pyboy.stop(save=False)


if __name__ == "__main__":
    main()
