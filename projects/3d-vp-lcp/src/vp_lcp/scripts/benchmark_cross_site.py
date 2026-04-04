"""Aggregate multiple real-tile benchmark runs and pick a robust default config."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import csv
import json


@dataclass(slots=True)
class SiteRow:
    site: str
    voxel_size: float
    neighbours: int
    algorithm: str
    normalize_resistance: bool
    runtime_seconds: float
    runtime_penalized_score: float
    informative_3d: bool


@dataclass(slots=True)
class CrossSiteRow:
    voxel_size: float
    neighbours: int
    algorithm: str
    normalize_resistance: bool
    site_count: int
    mean_site_rank: float
    worst_site_rank: int
    mean_runtime_seconds: float


def _config_key(row: SiteRow) -> tuple[float, int, str, bool]:
    return (row.voxel_size, row.neighbours, row.algorithm, row.normalize_resistance)


def load_site_rows(site_name: str, benchmark_csv: str | Path, require_informative: bool = True) -> list[SiteRow]:
    rows: list[SiteRow] = []
    with Path(benchmark_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        has_informative_col = bool(reader.fieldnames and "informative_3d" in reader.fieldnames)
        for raw in reader:
            if str(raw.get("status", "")).strip().lower() != "ok":
                continue
            informative_3d = (
                str(raw.get("informative_3d", "true")).strip().lower() in {"1", "true", "yes"}
                if has_informative_col
                else True
            )
            if require_informative and not informative_3d:
                continue
            rows.append(
                SiteRow(
                    site=site_name,
                    voxel_size=float(raw["voxel_size"]),
                    neighbours=int(raw["neighbours"]),
                    algorithm=str(raw["algorithm"]),
                    normalize_resistance=str(raw["normalize_resistance"]).strip().lower() in {"1", "true", "yes"},
                    runtime_seconds=float(raw["runtime_seconds"]),
                    runtime_penalized_score=float(raw["runtime_penalized_score"]),
                    informative_3d=informative_3d,
                )
            )
    return rows


def aggregate_cross_site(site_rows: list[SiteRow]) -> list[CrossSiteRow]:
    if not site_rows:
        return []

    by_site: dict[str, list[SiteRow]] = {}
    for row in site_rows:
        by_site.setdefault(row.site, []).append(row)

    rank_by_site_and_key: dict[tuple[str, tuple[float, int, str, bool]], int] = {}
    for site, rows in by_site.items():
        ordered = sorted(rows, key=lambda r: r.runtime_penalized_score, reverse=True)
        for rank, row in enumerate(ordered, start=1):
            rank_by_site_and_key[(site, _config_key(row))] = rank

    all_sites = sorted(by_site)
    all_keys = sorted({_config_key(r) for r in site_rows})

    out: list[CrossSiteRow] = []
    for key in all_keys:
        ranks: list[int] = []
        runtimes: list[float] = []
        for site in all_sites:
            rank = rank_by_site_and_key.get((site, key))
            if rank is None:
                continue
            ranks.append(rank)
            match = next(r for r in by_site[site] if _config_key(r) == key)
            runtimes.append(match.runtime_seconds)

        if not ranks:
            continue

        out.append(
            CrossSiteRow(
                voxel_size=key[0],
                neighbours=key[1],
                algorithm=key[2],
                normalize_resistance=key[3],
                site_count=len(ranks),
                mean_site_rank=float(sum(ranks) / len(ranks)),
                worst_site_rank=max(ranks),
                mean_runtime_seconds=float(sum(runtimes) / len(runtimes)),
            )
        )

    out.sort(key=lambda r: (r.mean_site_rank, r.worst_site_rank, r.mean_runtime_seconds))
    return out


def write_cross_site(
    rows: list[CrossSiteRow],
    output_csv: str | Path,
    output_json: str | Path,
    expected_site_count: int,
) -> None:
    output_csv = Path(output_csv)
    output_json = Path(output_json)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "voxel_size",
        "neighbours",
        "algorithm",
        "normalize_resistance",
        "site_count",
        "mean_site_rank",
        "worst_site_rank",
        "mean_runtime_seconds",
    ]

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    full_coverage = [r for r in rows if r.site_count == expected_site_count]
    best = full_coverage[0] if full_coverage else (rows[0] if rows else None)
    payload = {
        "expected_site_count": expected_site_count,
        "rows": [asdict(r) for r in rows],
        "best_full_coverage": asdict(best) if best is not None else None,
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate benchmark_results.csv files from multiple sites.",
    )
    parser.add_argument(
        "--site",
        action="append",
        required=True,
        help="Site spec in the form name=path/to/benchmark_results.csv. Repeat for each site.",
    )
    parser.add_argument(
        "--output-root",
        default="outputs/real-data-cross-site",
        help="Directory for cross-site summary artifacts.",
    )
    parser.add_argument(
        "--allow-non-informative",
        action="store_true",
        help="Include non-informative 3D rows in ranking (default excludes them).",
    )
    args = parser.parse_args(argv)

    site_rows: list[SiteRow] = []
    for spec in args.site:
        if "=" not in spec:
            raise ValueError("Each --site value must be name=csv_path")
        name, csv_path = spec.split("=", 1)
        site_rows.extend(
            load_site_rows(
                name.strip(),
                csv_path.strip(),
                require_informative=not args.allow_non_informative,
            )
        )

    out_rows = aggregate_cross_site(site_rows)
    output_root = Path(args.output_root)
    write_cross_site(
        out_rows,
        output_root / "cross_site_summary.csv",
        output_root / "cross_site_summary.json",
        expected_site_count=len(args.site),
    )

    full_coverage = [r for r in out_rows if r.site_count == len(args.site)]
    if full_coverage:
        top = full_coverage[0]
        print(
            "Best robust config: "
            f"voxel={top.voxel_size:g}, neighbours={top.neighbours}, "
            f"algorithm={top.algorithm}, normalize={top.normalize_resistance}, "
            f"mean_rank={top.mean_site_rank:.3f}, worst_rank={top.worst_site_rank}"
        )
    elif out_rows:
        top = out_rows[0]
        print(
            "Best partial-coverage config: "
            f"voxel={top.voxel_size:g}, neighbours={top.neighbours}, "
            f"algorithm={top.algorithm}, normalize={top.normalize_resistance}"
        )
    else:
        print("No successful site rows found.")


if __name__ == "__main__":
    main()
