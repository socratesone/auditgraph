from __future__ import annotations

import argparse
import json
from pathlib import Path

from auditgraph import __version__
from auditgraph.scaffold import initialize_workspace


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditgraph", description="Auditgraph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show version")

    init_parser = subparsers.add_parser("init", help="Initialize a workspace")
    init_parser.add_argument("--root", default=".", help="Workspace root (default: .)")
    init_parser.add_argument(
        "--config-source",
        default=str(Path(__file__).resolve().parent.parent / "config" / "pkg.yaml"),
        help="Path to sample config file",
    )

    for name in ("ingest", "extract", "link", "index", "query", "rebuild"):
        subparsers.add_parser(name, help=f"Run {name} stage (placeholder)")

    return parser


def _print_placeholder(stage: str) -> None:
    payload = {
        "stage": stage,
        "status": "not_implemented",
        "message": "This command is a scaffold placeholder. Implement the pipeline stage next.",
    }
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "version":
        print(__version__)
        return

    if args.command == "init":
        root = Path(args.root).resolve()
        config_source = Path(args.config_source).resolve()
        created = initialize_workspace(root, config_source)
        payload = {
            "root": str(root),
            "created": created,
            "config_source": str(config_source),
        }
        print(json.dumps(payload, indent=2))
        return

    _print_placeholder(args.command)


if __name__ == "__main__":
    main()
