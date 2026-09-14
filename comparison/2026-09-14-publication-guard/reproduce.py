#!/usr/bin/env python3
"""Recompute the rejected-run comparison and matched diagnostic from evidence."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESPONDED = {"ok", "noCompactFilters"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(name):
    return json.loads((HERE / name).read_text())


def records(data, summary):
    assert digest(data) == summary["recordsSHA256"]
    rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    assert len(rows) == summary["dialled"] == summary["expectedRecords"]
    assert len({(r["host"], r["port"]) for r in rows}) == len(rows)
    assert all(r["runStartedAt"] == summary["generatedAt"] for r in rows)
    assert all(r["inputSHA256"] == summary["inputSHA256"] for r in rows)
    for overlay, counts in summary["networks"].items():
        actual = Counter(r["outcome"] for r in rows if r["network"] == overlay)
        assert sum(actual.values()) == counts["dialled"]
        assert actual["ok"] == counts["usable"]
        assert actual["noCompactFilters"] == counts["noCompactFilters"]
    return rows


def endpoint(row):
    return row["host"], row["port"]


def selection_key(row):
    return digest(f"{row['host']}:{row['port']}".encode())


def fraction(rows):
    answered = sum(r["outcome"] in RESPONDED for r in rows)
    return {
        "attempted": len(rows), "version_responders": answered,
        "response_percent": 100 * answered / len(rows),
        "outcomes": dict(sorted(Counter(r["outcome"] for r in rows).items())),
    }


def reproduce():
    metadata = read_json("metadata.json")
    for name, expected in metadata["files"].items():
        assert digest((HERE / name).read_bytes()) == expected, name
    accepted_summary = read_json("accepted-summary.json")
    rejected_summary = read_json("rejected-summary.json")
    diagnostic_summary = read_json("diagnostic-summary.json")
    assert accepted_summary["completeRun"] and rejected_summary["completeRun"]
    assert diagnostic_summary["sample"] == 48 and not diagnostic_summary["completeRun"]
    assert digest(gzip.decompress((HERE / "rejected-input.json.gz").read_bytes())) == rejected_summary["inputSHA256"]
    accepted = records(gzip.decompress((ROOT / metadata["accepted_records_path"]).read_bytes()), accepted_summary)
    rejected = records(gzip.decompress((HERE / "rejected-records.jsonl.gz").read_bytes()), rejected_summary)
    diagnostic = records((HERE / "diagnostic-records.jsonl").read_bytes(), diagnostic_summary)
    assert digest((HERE / "nodes.txt").read_bytes()) == diagnostic_summary["inputSHA256"]
    index = {endpoint(r): r for r in accepted}
    candidates = [r for r in rejected if r["network"] == "tor"
                  and endpoint(r) in index and index[endpoint(r)]["outcome"] in RESPONDED]
    selected = {
        "previously_answered_now_timeout": sorted(
            [r for r in candidates if r["outcome"] == "timeout"], key=selection_key)[:32],
        "answered_both_runs": sorted(
            [r for r in candidates if r["outcome"] in RESPONDED], key=selection_key)[:16],
    }
    group = {endpoint(r): label for label, rows in selected.items() for r in rows}
    saved = {endpoint(r): r["group"] for r in read_json("selection.json")["endpoints"]}
    assert group == saved and set(group) == {endpoint(r) for r in diagnostic}
    overlays = {}
    for overlay in ("clearnet", "tor", "i2p"):
        before = fraction([r for r in accepted if r["network"] == overlay])
        after = fraction([r for r in rejected if r["network"] == overlay])
        overlays[overlay] = {
            "accepted_run": before, "rejected_run": after,
            "response_difference_percentage_points": after["response_percent"] - before["response_percent"],
        }
    assert overlays["tor"]["rejected_run"]["response_percent"] < 50
    return {
        "schemaVersion": 1,
        "processing_script_sha256": digest(Path(__file__).read_bytes()),
        "comparison_scope": "Within-run version-response fractions. Windows and endpoint sets differ; changes are descriptive, not causal or whole-network availability estimates.",
        "windows": {
            label: {"started_at": s["generatedAt"], "ended_at": s["observationEndedAt"]}
            for label, s in (("accepted", accepted_summary), ("rejected", rejected_summary), ("diagnostic", diagnostic_summary))
        },
        "overlays": overlays,
        "diagnostic": {label: fraction([r for r in diagnostic if group[endpoint(r)] == label]) for label in selected},
        "publication": metadata["publication"],
        "limitation": metadata["diagnostic"]["limitation"],
    }


if __name__ == "__main__":
    report = reproduce()
    if sys.argv[1:] == ["--check"]:
        assert report == read_json("report.json"), "Preserved report differs from source evidence"
        print("Source hashes, aggregate counts, deterministic cohort and report verified")
    elif not sys.argv[1:]:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        raise SystemExit("usage: reproduce.py [--check]")
