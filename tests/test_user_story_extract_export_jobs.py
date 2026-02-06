from __future__ import annotations

from pathlib import Path

from auditgraph.config import load_config
from auditgraph.export.dot import export_dot
from auditgraph.export.graphml import export_graphml
from auditgraph.export.json import export_json
from auditgraph.extract.adr import extract_decisions
from auditgraph.extract.entities import build_log_claim
from auditgraph.extract.logs import extract_log_signatures
from auditgraph.extract.manifest import extract_adr_claims, write_entities
from auditgraph.jobs.runner import run_job
from auditgraph.plugins.registry import load_extractor_plugins
from auditgraph.storage.artifacts import read_json
from tests.support import make_entity, pkg_root


def test_us5_extract_adr_claims_write_decision_index(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    adr_path = tmp_path / "notes" / "adr-0001.md"
    adr_path.parent.mkdir()
    adr_path.write_text("# Use SQLite\n\nDecision details.", encoding="utf-8")

    claims = extract_adr_claims(pkg, [adr_path])

    assert claims
    assert extract_decisions(adr_path)
    assert (pkg / "indexes" / "decisions" / "index.json").exists()


def test_us6_extract_log_signatures_builds_claim(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "app.log"
    log_path.parent.mkdir()
    log_path.write_text("INFO ok\nERROR boom\n", encoding="utf-8")

    signatures = extract_log_signatures(log_path)
    claim = build_log_claim(signatures[0])

    assert signatures
    assert claim["type"] == "error_signature"


def test_us10_export_json_includes_entities(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    entity = make_entity("app.py", "repos/app.py")
    write_entities(pkg, [entity])

    json_path = export_json(tmp_path, pkg, tmp_path / "exports" / "subgraphs" / "export.json")

    payload = read_json(json_path)
    assert payload["entities"]


def test_us10_export_dot_contains_entity(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    entity = make_entity("app.py", "repos/app.py")
    write_entities(pkg, [entity])

    dot_path = export_dot(pkg, tmp_path / "exports" / "subgraphs" / "export.dot")

    assert entity["id"] in Path(dot_path).read_text(encoding="utf-8")


def test_us10_export_graphml_contains_entity(tmp_path: Path) -> None:
    pkg = pkg_root(tmp_path)
    entity = make_entity("app.py", "repos/app.py")
    write_entities(pkg, [entity])

    graphml_path = export_graphml(pkg, tmp_path / "exports" / "subgraphs" / "export.graphml")

    assert entity["id"] in Path(graphml_path).read_text(encoding="utf-8")


def test_us11_extractor_plugins_load() -> None:
    raw = {
        "extractors": [
            {
                "name": "example",
                "module": "example.module",
                "entrypoint": "extract",
                "config": {"enabled": True},
            }
        ]
    }

    plugins = load_extractor_plugins(raw)

    assert plugins
    assert plugins[0].name == "example"
    assert plugins[0].entrypoint == "extract"


def test_us14_jobs_daily_digest_writes_report(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    jobs_path = config_dir / "jobs.yaml"
    jobs_path.write_text(
        """
jobs:
  daily_digest:
    action:
      type: report.changed_since
      args:
        since: "24h"
    output:
      path: "exports/reports/daily.md"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    payload = run_job(tmp_path, load_config(None), "daily_digest")

    assert payload["status"] == "ok"
    output_path = Path(payload["output"])
    assert output_path.exists()
    assert "Changes since" in output_path.read_text(encoding="utf-8")
