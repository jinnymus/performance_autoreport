# Autoreport

Service and tooling for **performance test reporting**: pull metrics from InfluxDB (InfluxQL or Flux), capture **Grafana** dashboard snapshots via Selenium, assemble an HTML report, and optionally publish to **Confluence**, **Markdown**, local HTML, or an external **report storage** HTTP API. Notifications can be sent through a JWT-protected chat bot integration.

## Features

- Build a structured report (objectives, methodology, metrics tables, Grafana snapshots, optional Argo CD / Vault configuration sections).
- Compute **max RPS** for `max_performance_search` when all response times stay within **400 ms** (configurable logic in `src/analysis/max_rps.py`).
- Optional POST of run metadata to a compatible storage service (`CLINIC_REPORTS_URL`).
- FastAPI entrypoint for on-demand report generation.

## Requirements

- Python **3.11+** (see `requirements.txt`).
- For Grafana snapshots: a browser environment (headless Chrome is included in the Docker image below).

## Run locally

```bash
cd src
python -m pip install -r ../requirements.txt
# configure environment / .env for your Grafana, Influx, Confluence, etc.
python main.py
```

The default `main` path prepares a payload from the environment and runs one report. For an HTTP API server, use Uvicorn (see `src/main.py` — uncomment or add `uvicorn.run` as needed).

## Docker

The root `Dockerfile` is **self-contained** (public base images only): `selenium/standalone-chrome` plus a **Python 3.12** virtualenv (`build-essential`, `libffi-dev`, and `libssl-dev` are installed so pinned packages such as `cffi` can build when wheels are missing).

The Chrome image is **linux/amd64**. On Apple Silicon the Dockerfile sets `FROM --platform=linux/amd64` so the build uses emulation; on native amd64 hosts the same file works unchanged.

```bash
docker build -t autoreport:local .
docker run --rm -p 9200:9200 --env-file .env autoreport:local
```

`docker-compose.yaml` builds the same image as `autoreport:local` and mounts the project for development.

> **Note:** Older files such as `Dockerfile.bak` referenced private registries and are **not** used for open builds. Replace defaults in settings with your own hosts and secrets via environment variables.

## Configuration

Runtime settings use **pydantic-settings** (`src/settings.py`). Override with environment variables (same names as fields, case-insensitive), for example:

| Variable | Purpose |
| -------- | ------- |
| `INFLUX_*` / request body | InfluxDB connectivity and bucket |
| `GRAFANA_*` / request body | Snapshot URLs and credentials |
| `CONFLUENCE_*` | Wiki host, space, token |
| `ARGO_URL`, `ARGO_TOKEN`, `ARGO_HOST` | Argo CD API (see `src/clients/argocd.py`) |
| `VAULT_TOKEN`, Vault paths | Optional secret rendering in reports |
| `CLINIC_REPORTS_URL` | Optional performance-test storage API |
| `CREATE_REPORT`, `SAVE_TO_STORAGE`, `SEND_BOT_NOTIFICATION` | Feature toggles (`True` / `False`) |
| `CTS_HOST`, `BOT_ID`, `SECRET_KEY`, `CHAT_ID` | Chat bot integration |

Grafana dashboard URLs in `src/web/model.py` and `src/settings.py` use **`grafana.example.com`** placeholders — replace with your real dashboard links (or inject via API request models).

Yandex Wiki OAuth helpers read `YANDEX_OAUTH_CLIENT_ID`, `YANDEX_OAUTH_CLIENT_SECRET`, and `YANDEX_OAUTH_REDIRECT_URI` when using the OAuth flow.

## API sketch

`POST /report` accepts a JSON body shaped like `RequestCreateReport` in `src/web/model.py` (test metadata, Influx, Grafana, server type, optional Argo/Vault applications). Extend the model fields to match your CI payload.

## Project layout

- `src/main.py` — FastAPI app and report orchestration  
- `src/analysis/` — metric aggregation, Flux/Influx helpers, max RPS  
- `src/clients/` — Confluence, Grafana snapshots, Influx, Vault, Argo CD, etc.  
- `src/web/` — Pydantic models and HTML template blocks  
- `src/get_versions.py` — CLI helper to resolve versions from Argo/Vault (adjust `applications` for your cluster)

## License

Add your preferred license file before publishing (this repository did not ship with one).
