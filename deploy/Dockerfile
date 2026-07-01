# FastAPI backend image for the Render -> Fly.io re-host (2026-06-25).
# Mirrors render.yaml's web service: installs the locked deps and serves
# `uvicorn main:app` from dashboard/backend, with the repo root on the path so
# dashboard/backend/config.py can import the root config.py + src/ + models/.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1: OpenMP runtime required by scikit-learn / lightgbm wheels at import.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The BACKEND's locked, hashed deps (fastapi, uvicorn, python-dotenv, kiteconnect,
# slowapi, sqlalchemy, pandas, ...) — EXACTLY what Render's web service installed. Render's
# rootDir was dashboard/backend, so its `-r requirements.lock` resolved to THIS file, not the
# repo-root quant/ML lock (which has uvicorn but is missing the API deps like python-dotenv).
COPY dashboard/backend/requirements.lock ./
RUN pip install --require-hashes -r requirements.lock

# Copy the app source. The repo root must be on the path so dashboard/backend/config.py
# can import the root config.py + src/. The existing root .dockerignore trims data/,
# models/, results/, frontend, tests, and caches — the API reads results + the model
# badge via the GitHub API at runtime (github_data.py / GITHUB_TOKEN), so none of those
# need to be baked into the image.
COPY . .

# uvicorn imports `main:app` with CWD = dashboard/backend (rootDir parity); the
# repo root (/app) is put on sys.path by dashboard/backend/config.py's bootstrap.
WORKDIR /app/dashboard/backend
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
