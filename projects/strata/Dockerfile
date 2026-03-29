FROM python:3.11-slim-bullseye

LABEL maintainer="Matt Powell"
LABEL description="STRATA: Structured Type-Aware Risk Assessment Through Adaptive Calibration"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY examples/ examples/

# Install CPU-only PyTorch + project
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e ".[dev]"

# Run tests by default
CMD ["pytest", "tests/", "-v", "--tb=short"]
