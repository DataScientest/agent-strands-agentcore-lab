FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Les dépendances d'abord : leur couche reste en cache tant que uv.lock ne change pas.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" OTEL_SDK_DISABLED=true
EXPOSE 8080
CMD ["uvicorn", "incident_lab.server:app", "--host", "0.0.0.0", "--port", "8080"]
