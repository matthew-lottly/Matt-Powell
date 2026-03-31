FROM cgr.dev/chainguard/python:latest-dev AS base

WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/

RUN pip install --no-cache-dir ".[dev]"

# ---------- API image ----------
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Frontend build ----------
FROM cgr.dev/chainguard/node:latest-dev AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm ci --ignore-scripts --no-audit
COPY web/ ./
RUN npm run build

# ---------- Combined image (API + static frontend) ----------
FROM base AS prod
COPY --from=web-build /web/dist /app/static
EXPOSE 8000
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
