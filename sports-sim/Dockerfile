FROM python:3.11.15-slim-bookworm AS base

WORKDIR /app
COPY pyproject.toml ./
COPY src/ src/

# Update system packages to reduce known vulnerabilities at build time
RUN apt-get update \
	&& apt-get upgrade -y \
	&& rm -rf /var/lib/apt/lists/* \
	&& pip install --no-cache-dir ".[dev]"

# ---------- API image ----------
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Frontend build ----------
FROM node:20.20.2-alpine3.23 AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
# Use Alpine variant for smaller surface and fewer Debian CVEs; run npm ci
RUN npm ci --ignore-scripts --no-audit
COPY web/ ./
RUN npm run build

# ---------- Combined image (API + static frontend) ----------
FROM base AS prod
COPY --from=web-build /web/dist /app/static
EXPOSE 8000
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
