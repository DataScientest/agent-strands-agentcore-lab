"""Contrats d'entrée et de sortie : ce que l'agent doit rendre et ce que le serveur accepte."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class InvocationRequest(BaseModel):
    """Le corps de `POST /invocations` : l'atelier n'en fait pas partie, il vient du serveur."""

    model_config = ConfigDict(extra="forbid")
    incident_id: str = Field(pattern=r"^INC-[0-9]{3}$")
    mode: Literal["single", "multi"] = "single"
