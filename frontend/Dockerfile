# syntax=docker/dockerfile:1
#
# Building behind a TLS-inspecting corporate proxy? Pass its CA bundle as a
# build secret (never stored in any image layer):
#   docker build --secret id=extra_ca,src=/path/to/ca-bundle.crt -t smiley .
# Without the secret, the build uses the normal public CA roots.

# --- Stage 1: build the React app ------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime serving the API + the built app on one port --
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/smiley.db \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/frontend/dist /app/frontend/dist

RUN useradd --system --uid 10001 smiley \
    && mkdir -p /data \
    && chown smiley /data
USER smiley
VOLUME ["/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# --proxy-headers so login throttling sees the real client IP behind a
# reverse proxy / load balancer instead of the proxy's own address.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
