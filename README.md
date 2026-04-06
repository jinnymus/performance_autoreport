# Autoreport

Service and tooling for **performance test reporting**: pull metrics from InfluxDB (InfluxQL or Flux), capture **Grafana** dashboard snapshots via Selenium, assemble an HTML report, and optionally publish to **Confluence**, **Markdown**, local HTML, or an external **report storage** HTTP API. Notifications can be sent through a JWT-protected chat bot integration.

## What goes into the report

### Aggregated metrics table and SLA highlighting

Metrics for the run are read from **InfluxDB**, aggregated per operation and load step (RPM/RPS, percentiles, latency, errors, and similar fields from `src/analysis/`). The report embeds a **single summary table** of those values (styled HTML).

Cells are **highlighted** when a numeric value breaks the response-time SLA: values **above 400 ms** get a salmon background (`highlight()` in `src/main.py`). Adjust the threshold there if your SLA differs.

For `max_performance_search`, the tool also derives **max RPS** where all response times stay within that same **400 ms** budget (`src/analysis/max_rps.py`).

### Load profile

The report includes the **load profile** used for the test:

- **JMX / script path** of the load scenario.
- A **tabular load plan**: load step (% or target), ramp-up, and hold duration for each stage (`block_load_plan` / `block_mnt` in `src/web/template.py`).

Together with objectives and methodology sections, this makes the applied profile visible in the final page.

### Vault and Argo CD

When `vault` and `argo` (plus `applications`) are present in the request:

- **HashiCorp Vault** — for each configured secret path, the report pulls JSON and embeds a **sanitized** copy (sensitive keys masked) via `VaultClient` (`src/clients/vault_client.py`).
- **Argo CD** — deployment metadata for the listed applications is fetched from the Argo API and rendered as an **HTML table** (requests/limits, replicas, environment blob, chart/version labels, etc.) via `ArgoAdapter` (`src/clients/argocd.py`).

This gives a snapshot of **declared configuration** alongside runtime metrics.

### Grafana snapshots by layer (app / backend / platform)

Selenium logs into Grafana and captures **dashboard snapshots** for the test time window. You map each URL in the request; typical **tiers** line up as follows:

| Tier | What it represents in code | Grafana template field (request) |
| ---- | -------------------------- | -------------------------------- |
| **Application / load & business metrics** | JMeter (or equivalent) business view: throughput, response times | `snapshot_template_jmeter` |
| **Backend services** | e.g. Node.js workload panels, request-time / APM-style analytics | `snapshot_template_nodejs`, `snapshot_template_elastic` |
| **Platform / capacity** | Kubernetes **pod** and **node** utilization | `snapshot_template_pods`, `snapshot_template_nodes` |

Each block adds snapshot links plus tabbed/embedded chart sections in Confluence-style output (`create_snapshots_block` in `src/main.py`).

**Database deep dives:** Oracle / PostgreSQL **AWR** attachments are supported in code but currently **commented out** in the main flow; enable that block if you want DB-level reports in the same document.

## Features

- Build a structured report (objectives, conclusion template, methodology, **load profile**, **aggregated SLA-colored table**, multi-dashboard Grafana captures, **Vault** + **Argo CD** sections).
- Compute **max RPS** for `max_performance_search` when all response times stay within **400 ms** (logic in `src/analysis/max_rps.py`).
- Optional POST of run metadata to a compatible storage service (`CLINIC_REPORTS_URL`).
- FastAPI entrypoint for on-demand report generation (`POST /report`).

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
