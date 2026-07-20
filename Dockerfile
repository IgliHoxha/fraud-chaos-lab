# ---- build stage ----
FROM python:3.11-slim AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src

# Build a self-contained virtualenv we can copy into the runtime image.
COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install .

# ---- runtime stage ----
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 chaos
WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY app ./app

USER chaos
EXPOSE 8080

ENTRYPOINT ["fraud-chaos-lab"]
CMD ["serve"]
