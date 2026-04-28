# BitAgent UI — flat-layout FastAPI app + Jinja2 templates + static assets.
# Multi-stage: site-packages built once, runtime stays slim.

FROM python:3.12-slim AS deps
WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY --from=deps /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=deps /usr/local/bin/ /usr/local/bin/

COPY app.py auth.py config.py database.py graphql_client.py tmdb.py ./
COPY static ./static
COPY templates ./templates

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
ENV APP_PORT=8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${APP_PORT}/healthz" || exit 1

CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${APP_PORT:-8080}"]
