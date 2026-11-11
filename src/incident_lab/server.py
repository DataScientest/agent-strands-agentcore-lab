"""Sous-ensemble pédagogique du contrat HTTP AgentCore, sans authentification cloud."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from incident_lab.contracts import InvocationRequest
from incident_lab.runner import invoke

app = FastAPI()


@app.get("/ping")
def ping():
    return {"status": "Healthy"}


@app.post("/invocations")
def invocations(request: InvocationRequest):
    # L'atelier vient du serveur, jamais du texte de l'utilisateur ni du modèle.
    result = invoke(request.incident_id, request.mode, tenant="atelier-a")
    return JSONResponse(result, status_code=200 if result["ok"] else 503)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
