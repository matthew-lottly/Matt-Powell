FROM python:3.11-slim

WORKDIR /app

# System dependencies for rasterio/GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[train,deploy]"

COPY tests/ tests/

ENTRYPOINT ["python", "-m"]
CMD ["tsuan.train"]
