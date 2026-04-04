"""Minimal CLI entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .config import PipelineConfig
from .pipeline import run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vp-lcp",
        description="3D Vertical Permeability Least-Cost Path framework.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init-config", help="Write a default JSON config file.")
    init_parser.add_argument(
        "--output", default="vp_lcp_config.json", help="Path to the output config file."
    )

    run_parser = subparsers.add_parser("run", help="Run the full 3D-VP-LCP pipeline.")
    run_parser.add_argument("--input", required=True, help="Path to the LAS/LAZ file.")
    run_parser.add_argument("--config", help="Path to a JSON config file.")
    run_parser.add_argument("--output-dir", help="Override output directory.")
    run_parser.add_argument(
        "--neighbours",
        type=int,
        choices=[6, 18, 26],
        help="Voxel adjacency type (6, 18, or 26). Overrides the config value.",
    )
    run_parser.add_argument(
        "--algorithm",
        choices=["dijkstra", "astar"],
        help="Routing algorithm. Overrides the config value.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"vp-lcp {__version__}")
        sys.exit(0)

    if args.command == "init-config":
        config = PipelineConfig()
        config.write_json(args.output)
        print(f"Wrote default config to {args.output}")
        return

    if args.command == "run":
        config = PipelineConfig.from_json(args.config) if args.config else PipelineConfig()
        if args.output_dir:
            config.output.output_dir = args.output_dir
        if getattr(args, "neighbours", None):
            config.routing.neighbours = args.neighbours
        if getattr(args, "algorithm", None):
            config.routing.algorithm = args.algorithm
        result = run_pipeline(args.input, config)
        print(json.dumps(result.to_dict(), indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
