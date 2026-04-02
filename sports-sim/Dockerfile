FROM python:3.13-slim-bookworm AS base

WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/

RUN pip install --no-cache-dir ".[dev]" \
    && rm -rf /root/.cache/pip

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --no-create-home appuser

# ---------- API image ----------
FROM base AS api
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
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
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
