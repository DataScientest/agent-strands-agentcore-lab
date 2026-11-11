"""Contrats et accès métier : aucun accès AWS, shell ou réseau dans les outils."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

DATA = json.loads(Path(__file__).with_name("incidents.json").read_text())

class BudgetExceeded(RuntimeError):
    pass

@dataclass
class Budget:
    max_models: int = 12
    max_tools: int = 16
    models: int = 0
    tools: int = 0
    started: float = field(default_factory=time.monotonic)
    events: list = field(default_factory=list)

    def model_call(self):
        self.models += 1
        if self.models > self.max_models:
            raise BudgetExceeded("Budget global d'appels modèle atteint")

    def tool_call(self):
        self.tools += 1
        if self.tools > self.max_tools:
            raise BudgetExceeded("Budget global d'appels outils atteint")

class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypothesis: str
    evidence_ids: list[str] = Field(min_length=1)
    limitation: str

class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: str
    status: Literal["hypothesis", "insufficient_evidence"]
    findings: list[Finding]
    unknowns: list[str] = Field(min_length=1)
    proposed_action: str
    requires_human_approval: Literal[True]

@dataclass
class Investigation:
    incident_id: str
    tenant: str = "atelier-a"
    budget: Budget = field(default_factory=Budget)
    allowed_kinds: frozenset = frozenset({"data", "deployment", "quality"})
    observed: set = field(default_factory=set)
    attempts: dict = field(default_factory=dict)

    def _incident(self):
        incident = DATA.get(self.incident_id)
        if incident is None or incident["tenant"] != self.tenant:
            return None  # Ne pas révéler si un incident existe chez un autre client.
        return incident

    def _record(self, tool, arguments, result):
        self.budget.events.append({"tool": tool, "arguments": arguments, "result": result})
        return result

    def get_incident(self):
        self.budget.tool_call()
        incident = self._incident()
        result = {"error": "NOT_FOUND", "retryable": False}
        if incident:
            result = {"incident_id": self.incident_id, "summary": incident["summary"],
                      "evidence_ids": [e["id"] for e in incident["evidence"]
                                       if e["kind"] in self.allowed_kinds]}
        return self._record("get_incident", {}, result)

    def read_evidence(self, evidence_id):
        self.budget.tool_call()
        incident = self._incident()
        items = incident["evidence"] if incident else []
        e = next((e for e in items if e["id"] == evidence_id
                  and e["kind"] in self.allowed_kinds), None)
        args = {"evidence_id": evidence_id}
        if e is None:
            return self._record("read_evidence", args, {"error": "NOT_FOUND", "retryable": False})
        n = self.attempts.get(evidence_id, 0)
        self.attempts[evidence_id] = n + 1
        if e.get("fail_once") and n == 0:
            return self._record("read_evidence", args, {"error": "UNAVAILABLE", "retryable": True})
        self.observed.add(evidence_id)
        result = {k: v for k, v in e.items() if k != "fail_once"}
        return self._record("read_evidence", args, result)

    def validate_report(self, report):
        if report.incident_id != self.incident_id:
            raise ValueError("INCIDENT_MISMATCH")
        cited = {e for finding in report.findings for e in finding.evidence_ids}
        if not cited.issubset(self.observed):
            raise ValueError("UNOBSERVED_CITATION")
        if report.status == "hypothesis" and not report.findings:
            raise ValueError("EMPTY_HYPOTHESIS")
        return report
