"""Sous-ensemble pédagogique du contrat HTTP AgentCore, sans authentification cloud."""
from typing import Literal
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from runner import invoke

app = FastAPI()

class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: str = Field(pattern=r"^INC-[0-9]{3}$")
    mode: Literal["single", "multi"] = "single"

@app.get("/ping")
def ping():
    return {"status": "Healthy"}

@app.post("/invocations")
def invocations(request: Request):
    # L'atelier vient du serveur, jamais du texte de l'utilisateur ni du modèle.
    result = invoke(request.incident_id, request.mode, tenant="atelier-a")
    return JSONResponse(result, status_code=200 if result["ok"] else 503)
