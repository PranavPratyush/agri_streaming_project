"""Unit tests for Prometheus and Grafana operational configuration and dashboard definitions."""

from __future__ import annotations

import json
from pathlib import Path
import yaml
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_prometheus_server_config():
    """Verify Prometheus main configuration syntax and essential scrape targets."""
    prom_path = REPO_ROOT / "infra" / "prometheus" / "prometheus.yml"
    assert prom_path.exists(), f"Missing {prom_path}"

    with prom_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "global" in config
    assert "scrape_interval" in config["global"]
    assert "evaluation_interval" in config["global"]
    assert "rule_files" in config
    assert "alert_rules.yml" in config["rule_files"]

    assert "scrape_configs" in config
    job_names = [sc["job_name"] for sc in config["scrape_configs"]]
    expected_jobs = {
        "prometheus",
        "agri-ingestion",
        "agri-stream-processor",
        "agri-risk-engine",
        "agri-persistence-sink",
        "agri-backend-api",
    }
    assert expected_jobs.issubset(set(job_names)), f"Missing expected scrape jobs: {expected_jobs - set(job_names)}"


def test_prometheus_alert_rules_config():
    """Verify Prometheus alert rules structure, severity labels, and annotations."""
    rules_path = REPO_ROOT / "infra" / "prometheus" / "alert_rules.yml"
    assert rules_path.exists(), f"Missing {rules_path}"

    with rules_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "groups" in data and len(data["groups"]) > 0
    rules = data["groups"][0].get("rules", [])
    assert len(rules) >= 6

    alert_names = set()
    for rule in rules:
        assert "alert" in rule, f"Rule missing 'alert' name: {rule}"
        assert "expr" in rule, f"Rule {rule['alert']} missing 'expr'"
        assert "for" in rule, f"Rule {rule['alert']} missing 'for' duration"
        assert "labels" in rule and "severity" in rule["labels"]
        assert rule["labels"]["severity"] in {"critical", "warning", "info"}
        assert "annotations" in rule
        assert "summary" in rule["annotations"]
        assert "description" in rule["annotations"]
        alert_names.add(rule["alert"])

    expected_alerts = {
        "ServiceDown",
        "StaleSourceTelemetry",
        "SustainedConsumerLag",
        "RepeatedSparkMicroBatchFailures",
        "DeadLetterQueueGrowth",
        "CriticalCropStressIndex",
    }
    assert expected_alerts.issubset(alert_names), f"Missing required alert rules: {expected_alerts - alert_names}"


def test_grafana_provisioning_config():
    """Verify Grafana datasource and dashboard provisioning YAML configurations."""
    ds_path = REPO_ROOT / "infra" / "grafana" / "provisioning" / "datasources" / "datasources.yml"
    db_path = REPO_ROOT / "infra" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"

    assert ds_path.exists(), f"Missing {ds_path}"
    assert db_path.exists(), f"Missing {db_path}"

    with ds_path.open("r", encoding="utf-8") as f:
        ds_data = yaml.safe_load(f)
    assert "datasources" in ds_data
    ds_types = {ds["type"] for ds in ds_data["datasources"]}
    assert "prometheus" in ds_types
    assert "postgres" in ds_types

    with db_path.open("r", encoding="utf-8") as f:
        db_data = yaml.safe_load(f)
    assert "providers" in db_data
    assert len(db_data["providers"]) > 0
    assert db_data["providers"][0]["options"]["path"] == "/etc/grafana/dashboards"


def test_grafana_dashboards_syntax_and_integrity():
    """Verify all 7 provisioned Grafana dashboards are valid JSON, unique UIDs, and valid panels."""
    dashboards_dir = REPO_ROOT / "infra" / "grafana" / "dashboards"
    assert dashboards_dir.exists(), f"Missing {dashboards_dir}"

    expected_dashboards = [
        "01-system-overview.json",
        "02-kafka-and-consumer-groups.json",
        "03-spark-streaming-checkpoint-health.json",
        "04-ingestion-source-freshness.json",
        "05-data-quality-sensor-health.json",
        "06-candidate-alerts-investigator.json",
        "07-reliability-evaluation-metrics.json",
    ]

    seen_uids = set()

    for db_filename in expected_dashboards:
        db_file = dashboards_dir / db_filename
        assert db_file.exists(), f"Expected dashboard missing: {db_filename}"

        with db_file.open("r", encoding="utf-8") as f:
            dashboard = json.load(f)

        uid = dashboard.get("uid")
        assert uid and uid.startswith("agri-"), f"Dashboard {db_filename} has invalid or missing UID: {uid}"
        assert uid not in seen_uids, f"Duplicate UID detected in {db_filename}: {uid}"
        seen_uids.add(uid)

        assert dashboard.get("title"), f"Dashboard {db_filename} missing title"
        panels = dashboard.get("panels", [])
        assert len(panels) > 0, f"Dashboard {db_filename} has no panels"

        panel_ids = set()
        for panel in panels:
            p_id = panel.get("id")
            assert p_id is not None, f"Panel missing ID in {db_filename}"
            assert p_id not in panel_ids, f"Duplicate panel ID {p_id} in {db_filename}"
            panel_ids.add(p_id)

            assert panel.get("title"), f"Panel {p_id} in {db_filename} missing title"
            targets = panel.get("targets", [])
            for target in targets:
                assert "expr" in target or "rawSql" in target, f"Panel {panel.get('title')} in {db_filename} missing query target"

