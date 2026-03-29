"""Assemble a reproducible JMLR submission bundle under paper/submission_jmlr/."""

from __future__ import annotations

import shutil
from pathlib import Path


def _ignore_copy(_, names):
    ignored = set()
    for name in names:
        if name in {"__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist", "supplementary_bundle"}:
            ignored.add(name)
        if name.endswith(".egg-info"):
            ignored.add(name)
    return ignored


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    submission_dir = root / "paper" / "submission_jmlr"
    bundle_root = submission_dir / "supplementary_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    for name in ["src", "tests", "scripts", "examples", "data", "outputs", "README.md", "pyproject.toml"]:
        src = root / name
        dst = bundle_root / name
        if src.is_dir():
            shutil.copytree(src, dst, ignore=_ignore_copy)
        elif src.exists():
            shutil.copy2(src, dst)

    archive_base = submission_dir / "supplementary"
    shutil.make_archive(str(archive_base), "zip", bundle_root)
    print(f"Built {archive_base}.zip")


if __name__ == "__main__":
    main()
