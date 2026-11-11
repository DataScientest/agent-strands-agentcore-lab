"""Vérifier le contrat AgentCore dans Floci, sans exécuter Strands."""
import json
import os
import uuid
from urllib.parse import urlparse
import boto3
from botocore.config import Config


def client(service):
    endpoint = os.getenv("FLOCI_ENDPOINT", "http://127.0.0.1:14566")
    if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "floci"}:
        raise ValueError("Floci doit être local; aucun fallback AWS")
    return boto3.client(service, endpoint_url=endpoint, region_name="eu-west-3",
                        aws_access_key_id="test", aws_secret_access_key="test",
                        config=Config(retries={"max_attempts": 1}, connect_timeout=5, read_timeout=10))


def exercise():
    control = client("bedrock-agentcore-control")
    name = "course_" + uuid.uuid4().hex[:8]
    config = dict(agentRuntimeArtifact={"containerConfiguration": {
        "containerUri": "000000000000.dkr.ecr.eu-west-3.amazonaws.com/course:local"}},
        roleArn="arn:aws:iam::000000000000:role/local-course",
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"})
    created = control.create_agent_runtime(agentRuntimeName=name, **config)
    rid = created["agentRuntimeId"]
    try:
        first = control.get_agent_runtime(agentRuntimeId=rid)
        updated = control.update_agent_runtime(agentRuntimeId=rid, description="v2 locale", **config)
        endpoint = control.create_agent_runtime_endpoint(agentRuntimeId=rid,
            name="candidate", agentRuntimeVersion=updated["agentRuntimeVersion"])
        versions = control.list_agent_runtime_versions(agentRuntimeId=rid)
        response = client("bedrock-agentcore").invoke_agent_runtime(
            agentRuntimeArn=updated["agentRuntimeArn"],
            runtimeSessionId=str(uuid.uuid4()), contentType="application/json",
            payload=json.dumps({"incident_id": "INC-001"}).encode())
        body = response["response"].read().decode()
        return {"runtime_id": rid, "first_version": first["agentRuntimeVersion"],
                "second_version": updated["agentRuntimeVersion"],
                "endpoint": endpoint.get("agentRuntimeEndpointArn", "candidate"), "versions": versions["agentRuntimes"],
                "simulated_invoke_body": body, "agent_executed": False}
    finally:
        # Nettoyer seulement les ressources créées par cette exécution.
        try:
            control.delete_agent_runtime_endpoint(agentRuntimeId=rid, endpointName="candidate")
        finally:
            control.delete_agent_runtime(agentRuntimeId=rid)


if __name__ == "__main__":
    print(json.dumps(exercise(), ensure_ascii=False, indent=2, default=str))
