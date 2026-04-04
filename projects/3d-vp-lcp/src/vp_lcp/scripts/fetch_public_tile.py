"""Download a public LAS/LAZ tile described by a small JSON manifest."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import urllib.request


@dataclass(slots=True)
class PublicTileManifest:
    """Metadata needed to fetch one public LiDAR tile."""

    name: str
    url: str
    output_file: str
    sha256: str | None = None


def load_manifest(path: str | Path) -> PublicTileManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return PublicTileManifest(
        name=str(raw["name"]),
        url=str(raw["url"]),
        output_file=str(raw.get("output_file", "public_tile.laz")),
        sha256=str(raw["sha256"]).lower() if raw.get("sha256") else None,
    )


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, output_path.open("wb") as out:
        shutil.copyfileobj(response, out)


def fetch_public_tile(
    manifest_path: str | Path,
    data_dir: str | Path,
    force: bool = False,
) -> Path:
    manifest = load_manifest(manifest_path)
    out_path = Path(data_dir) / manifest.output_file

    if out_path.exists() and not force:
        if manifest.sha256 is None or sha256_file(out_path) == manifest.sha256:
            return out_path

    download_file(manifest.url, out_path)

    if manifest.sha256 is not None:
        digest = sha256_file(out_path)
        if digest != manifest.sha256:
            raise ValueError(
                f"SHA256 mismatch for {out_path}. Expected {manifest.sha256}, got {digest}."
            )

    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download a public LAS/LAZ tile from a JSON manifest.",
    )
    parser.add_argument(
        "--manifest",
        default="data/public_lidar_tile.example.json",
        help="Path to JSON manifest with name/url/output_file/optional sha256.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory where the LAS/LAZ tile will be written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when the destination file already exists.",
    )
    args = parser.parse_args(argv)

    path = fetch_public_tile(args.manifest, args.data_dir, force=args.force)
    print(path)


if __name__ == "__main__":
    main()
