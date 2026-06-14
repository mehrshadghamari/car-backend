"""Extract Hamrah catalog NDJSON from data.zip into hamrahdata/."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def extract_hamrah_data(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parents[1]
    zip_path = root / "data.zip"
    dest = root / "hamrahdata"
    brands_file = dest / "data" / "hamrahmechanic_brands.ndjson"

    if brands_file.exists():
        return brands_file

    if not zip_path.exists():
        raise FileNotFoundError(f"Missing {zip_path}")

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(dest)

    if not brands_file.exists():
        raise FileNotFoundError(f"Extracted {zip_path.name} but missing {brands_file}")

    print(f"Extracted {zip_path.name} → {dest}/")
    return brands_file


def main() -> None:
    try:
        extract_hamrah_data()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
