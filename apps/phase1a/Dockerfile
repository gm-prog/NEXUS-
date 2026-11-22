FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WORKDIR /app

RUN addgroup --system --gid 10001 nexus && adduser --system --uid 10001 --ingroup nexus nexus
COPY apps/phase1a/pyproject.toml apps/phase1a/uv.lock ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check "uv==0.13.0" \
    && uv sync --locked --no-dev --no-install-project
COPY apps/phase1a/src ./src
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "phase1a_demo.server"]
