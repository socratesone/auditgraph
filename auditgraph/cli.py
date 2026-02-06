from __future__ import annotations

import argparse
import json
from pathlib import Path

from auditgraph import __version__
from auditgraph.config import load_config
from auditgraph.export import export_dot, export_graphml, export_json
from auditgraph.logging import setup_logging
from auditgraph.jobs.runner import list_jobs, run_job
from auditgraph.pipeline.runner import PipelineRunner
from auditgraph.query import diff_runs, keyword_search, neighbors, node_view, why_connected
from auditgraph.scaffold import initialize_workspace
from auditgraph.storage.artifacts import profile_pkg_root


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditgraph", description="Auditgraph CLI")
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Log level (default: INFO)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show version")

    init_parser = subparsers.add_parser("init", help="Initialize a workspace")
    init_parser.add_argument("--root", default=".", help="Workspace root (default: .)")
    init_parser.add_argument(
        "--config-source",
        default=str(Path(__file__).resolve().parent.parent / "config" / "pkg.yaml"),
        help="Path to sample config file",
    )

    ingest_parser = subparsers.add_parser("ingest", help="Run ingest stage")
    ingest_parser.add_argument("--root", default=".", help="Workspace root")
    ingest_parser.add_argument("--config", default=None, help="Config path")

    import_parser = subparsers.add_parser("import", help="Manually import files")
    import_parser.add_argument("paths", nargs="+", help="Files or directories to import")
    import_parser.add_argument("--root", default=".", help="Workspace root")
    import_parser.add_argument("--config", default=None, help="Config path")

    for name in ("extract", "link", "index"):
        subparsers.add_parser(name, help=f"Run {name} stage (placeholder)")

    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild all stages (placeholder)")
    rebuild_parser.add_argument("--root", default=".", help="Workspace root")
    rebuild_parser.add_argument("--config", default=None, help="Config path")

    query_parser = subparsers.add_parser("query", help="Run query stage")
    query_parser.add_argument("--q", default="", help="Query string")
    query_parser.add_argument("--root", default=".", help="Workspace root")
    query_parser.add_argument("--config", default=None, help="Config path")

    node_parser = subparsers.add_parser("node", help="Show node details")
    node_parser.add_argument("id", help="Entity id")
    node_parser.add_argument("--root", default=".", help="Workspace root")
    node_parser.add_argument("--config", default=None, help="Config path")

    neighbors_parser = subparsers.add_parser("neighbors", help="Show node neighbors")
    neighbors_parser.add_argument("id", help="Entity id")
    neighbors_parser.add_argument("--depth", type=int, default=1, help="Traversal depth")
    neighbors_parser.add_argument("--root", default=".", help="Workspace root")
    neighbors_parser.add_argument("--config", default=None, help="Config path")

    diff_parser = subparsers.add_parser("diff", help="Diff two runs (placeholder)")
    diff_parser.add_argument("--run-a", required=False, help="First run id")
    diff_parser.add_argument("--run-b", required=False, help="Second run id")
    diff_parser.add_argument("--root", default=".", help="Workspace root")
    diff_parser.add_argument("--config", default=None, help="Config path")

    export_parser = subparsers.add_parser("export", help="Export subgraph (placeholder)")
    export_parser.add_argument("--format", default="json", help="Export format")
    export_parser.add_argument("--root", default=".", help="Workspace root")
    export_parser.add_argument("--config", default=None, help="Config path")
    export_parser.add_argument("--output", default=None, help="Output file path")

    jobs_parser = subparsers.add_parser("jobs", help="Run automation jobs")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command", required=True)
    jobs_run = jobs_subparsers.add_parser("run", help="Run a named job")
    jobs_run.add_argument("name", help="Job name")
    jobs_run.add_argument("--root", default=".", help="Workspace root")
    jobs_run.add_argument("--config", default=None, help="Config path")
    jobs_subparsers.add_parser("list", help="List available jobs")

    why_parser = subparsers.add_parser("why-connected", help="Explain why two nodes are connected")
    why_parser.add_argument("--from", dest="from_id", required=True, help="Source id")
    why_parser.add_argument("--to", dest="to_id", required=True, help="Target id")
    why_parser.add_argument("--root", default=".", help="Workspace root")
    why_parser.add_argument("--config", default=None, help="Config path")

    return parser


def _print_placeholder(stage: str, args: argparse.Namespace) -> None:
    payload = {
        "stage": stage,
        "status": "not_implemented",
        "message": "This command is a scaffold placeholder. Implement the pipeline stage next.",
        "args": {k: v for k, v in vars(args).items() if k not in {"log_level", "command"}},
    }
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    setup_logging(args.log_level)

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

    if args.command == "ingest":
        runner = PipelineRunner()
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        result = runner.run_stage("ingest", root=root, config=config)
        print(json.dumps({"stage": result.stage, "status": result.status, "detail": result.detail}, indent=2))
        return

    if args.command == "import":
        runner = PipelineRunner()
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        result = runner.run_import(root=root, config=config, targets=list(args.paths))
        print(json.dumps({"stage": result.stage, "status": result.status, "detail": result.detail}, indent=2))
        return

    if args.command == "rebuild":
        runner = PipelineRunner()
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        result = runner.run_stage("rebuild", root=root, config=config)
        print(json.dumps({"stage": result.stage, "status": result.status, "detail": result.detail}, indent=2))
        return

    if args.command == "query":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        profile = config.profile()
        search_cfg = profile.get("search", {})
        enable_semantic = bool(search_cfg.get("semantic", {}).get("enabled", False))
        score_rounding = float(search_cfg.get("ranking", {}).get("score_rounding", 0.000001))
        results = keyword_search(
            pkg_root,
            args.q,
            enable_semantic=enable_semantic,
            score_rounding=score_rounding,
        )
        print(json.dumps({"query": args.q, "results": results}, indent=2))
        return

    if args.command == "node":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        payload = node_view(pkg_root, args.id)
        print(json.dumps(payload, indent=2))
        return

    if args.command == "neighbors":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        payload = neighbors(pkg_root, args.id, depth=args.depth)
        print(json.dumps(payload, indent=2))
        return

    if args.command == "diff":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        payload = diff_runs(pkg_root, args.run_a or "", args.run_b or "")
        print(json.dumps(payload, indent=2))
        return

    if args.command == "export":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        output_path = Path(args.output) if args.output else root / "exports" / "subgraphs" / f"export.{args.format}"
        if args.format == "dot":
            path = export_dot(pkg_root, output_path)
        elif args.format == "graphml":
            path = export_graphml(pkg_root, output_path)
        else:
            path = export_json(root, pkg_root, output_path)
        print(json.dumps({"format": args.format, "output": str(path)}, indent=2))
        return

    if args.command == "why-connected":
        root = Path(args.root).resolve()
        config = load_config(Path(args.config) if args.config else None)
        pkg_root = profile_pkg_root(root, config)
        payload = why_connected(pkg_root, args.from_id, args.to_id)
        print(json.dumps(payload, indent=2))
        return

    if args.command == "jobs":
        if args.jobs_command == "list":
            root = Path(".").resolve()
            config = load_config(None)
            payload = {"jobs": list_jobs(root, config)}
            print(json.dumps(payload, indent=2))
            return
        if args.jobs_command == "run":
            root = Path(args.root).resolve()
            config = load_config(Path(args.config) if args.config else None)
            payload = run_job(root, config, args.name)
            print(json.dumps(payload, indent=2))
            return

    _print_placeholder(args.command, args)


if __name__ == "__main__":
    main()
