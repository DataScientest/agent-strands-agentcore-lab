"""Même jeu et mêmes budgets pour les deux architectures; mesures brutes sans juge cloud."""
import argparse
import json
import os
from pathlib import Path
from runner import invoke

DEV = ["INC-001", "INC-002", "INC-004", "INC-006", "INC-999", "INC-005"]
HOLDOUT = ["INC-003"]


def grade(result):
    report = result.get("report", {})
    observed = {e["result"]["id"] for e in result.get("trace", [])
                if e["tool"] == "read_evidence" and "id" in e["result"]}
    cited = {eid for f in report.get("findings", []) for eid in f["evidence_ids"]}
    return {"valid_output": result.get("ok", False),
            "citations_observed": bool(result.get("ok")) and cited.issubset(observed),
            "approval_required": report.get("requires_human_approval") is True,
            "manual_review_required": True}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["single", "multi"], default="single")
    p.add_argument("--split", choices=["dev", "holdout"], default="dev")
    p.add_argument("--repeats", type=int, default=3)
    a = p.parse_args()
    if a.repeats < 1:
        p.error("repeats doit être positif")
    out = Path("runs"); out.mkdir(exist_ok=True)
    rows = []
    for incident in DEV if a.split == "dev" else HOLDOUT:
        for repeat in range(a.repeats):
            r = invoke(incident, a.mode)
            row = {**r, "repeat": repeat, "grades": grade(r)}
            rows.append(row)
            print(incident, repeat, row["grades"], flush=True)
            # Écriture progressive pour ne pas perdre les résultats précédents.
            (out / f"{a.mode}-{a.split}-{os.getenv('AGENT_VARIANT', 'baseline')}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
