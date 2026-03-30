FROM python:3.11-bookworm-slim AS base

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
FROM node:20-bookworm-slim AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
# Update system packages in the node build image as well
RUN apt-get update \
	&& apt-get upgrade -y \
	&& rm -rf /var/lib/apt/lists/* \
	&& npm ci --ignore-scripts
COPY web/ ./
RUN npm run build

# ---------- Combined image (API + static frontend) ----------
FROM base AS prod
COPY --from=web-build /web/dist /app/static
EXPOSE 8000
CMD ["uvicorn", "sports_sim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
