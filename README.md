# Fraud Chaos Lab

> **"We break our own systems so hackers can't."**

![CI](https://github.com/IgliHoxha/fraud-chaos-lab/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Fraud Chaos Lab** is a resilience engine that simulates high-velocity,
catastrophic fraud scenarios - Synthetic Identity Floods, service-1 fraud storms,
service-2 IoT storms - against **your own** infrastructure, to prove it stays
*antifragile* under the worst case.

It is a chaos-engineering tool, not an attack tool. By default it runs in
**dry-run**: it exercises the full concurrency machinery in-process and sends
**zero** real requests. You opt into hitting a real target - one you are
authorised to test - by configuring it explicitly.

## How it works

```
                POST /chaos/*
                        ┌──────────────────┐
   client  ──────────▶  │   api (FastAPI)  │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   scenarios      │  what traffic to make
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   engine         │  bounded async fan-out
                        └────────┬─────────┘
  synthetic identities  ┌────────▼─────────┐  dry-run OR real POSTs
  (Faker)  ─────────────│  provider client │────────▶  upstreams
                        └──────────────────┘
                        (provider-1 · service-1 · service-2 …)
```

Scenarios decide *what* synthetic traffic to generate; the **engine** owns *how*
it is fanned out (a semaphore-bounded `asyncio.gather`) and measured (per-request
latency, success/failure, throughput). The **provider client** is the single
choke point where dry-run is enforced.

## Project layout

```
.
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── cli.py               # `serve` and one-off `storm` subcommands
│   ├── config.py            # env-based settings (safe, dry-run defaults)
│   ├── models.py            # request/response schemas
│   ├── metrics.py           # Prometheus instrumentation
│   ├── api/                 # HTTP routes: /chaos/* and ops probes
│   ├── chaos/               # engine + the three scenarios
│   ├── providers/           # async upstream client (dry-run choke point)
│   └── synthetic/           # Faker-backed synthetic identities
├── tests/                   # pytest suite (engine, synthetic, API)
├── docs/openapi.yaml        # generated API specification
├── Dockerfile               # multi-stage, non-root image
├── docker-compose.yaml      # app + bundled mock upstream
└── .github/workflows/       # CI (test matrix, ruff, docker build)
```

## Capabilities

Three high-velocity attack vectors, each exposed as an endpoint.

### 1. Subscription Churn Storm - `POST /chaos/subscription-churn`

A botnet creates thousands of fake accounts and immediately cancels them to
degrade reputation and fill databases with junk. Each unit generates a synthetic
identity, subscribes it to **provider-1**, **provider-2** and **provider-3** concurrently,
then immediately unsubscribes - probing consistency limits.

### 2. Service-1 Fraud Flood - `POST /chaos/service-1-flood`

A data leak triggers thousands of simultaneous fraud detections. Floods
upstream service-1 with critical `FRAUD_DETECTED` events to stress its ingestion
queue and alerting latency.

### 3. Service-2 IoT Storm - `POST /chaos/service-2-storm`

A city-wide hack sets off every smoke alarm at once. Simulates thousands of IoT
devices reporting fake fire/smoke telemetry to stress upstream service-2 and
dispatch logic.

## Getting started

```shell
# 1. Install into a local virtualenv
make install

# 2. Run the tests
make test

# 3. Start the API (dry-run - nothing leaves the process)
make run
```

Then open <http://localhost:8080/docs> for interactive API docs, or fire a storm:

```shell
curl -X POST http://localhost:8080/chaos/service-1-flood \
  -H 'content-type: application/json' -d '{"count": 5000, "concurrency": 200}'
```

```json
{
  "scenario": "service-1-flood",
  "dry_run": true,
  "requested": 5000,
  "succeeded": 5000,
  "failed": 0,
  "duration_seconds": 0.42,
  "requests_per_second": 11904.76,
  "latency_p50_ms": 1.6,
  "latency_p95_ms": 2.9,
  "latency_max_ms": 4.1
}
```

Every request body field is optional and falls back to configuration:

| Field         | Meaning                                            | Default             |
| ------------- | -------------------------------------------------- | ------------------- |
| `count`       | Synthetic events to generate (clamped to the max)  | `DEFAULT_STORM_SIZE`|
| `concurrency` | Max in-flight requests                             | `CONCURRENCY`       |
| `dry_run`     | Override the server safety switch for this storm   | server `DRY_RUN`    |

## Arming it against a real target

Real traffic is deliberately hard to trigger by accident - it needs **both** a
target and the flag flipped:

```shell
export STORM_TARGET_BASE_URL=https://staging.internal.example.com
export DRY_RUN=false
make run
```

Per-scenario upstreams can be pointed individually with `PROVIDER_1_URL`, `PROVIDER_2_URL`,
`PROVIDER_3_URL`, `SERVICE_1_URL`, `SERVICE_2_URL`; anything unset falls back to
`STORM_TARGET_BASE_URL` + a conventional path. With no target configured, the
service stays in dry-run no matter what `DRY_RUN` says.

> **Warning:** Only ever point this at infrastructure you own or are explicitly authorised
> to load-test.

## CLI

The same code runs as a long-lived server or a one-off job (handy as a cron /
Kubernetes Job for scheduled game-days):

```shell
python -m app serve                        # start the HTTP API
python -m app storm service-1-flood --count 1000 # fire one scenario and print the result
python -m app storm service-2-storm --no-dry-run
```

## Docker

```shell
make docker                                   # build fraud-chaos-lab:latest
docker run --rm -p 8080:8080 fraud-chaos-lab  # dry-run by default

# Or the full stack: the app armed against a bundled mock upstream
docker compose up --build
```

`docker compose up` starts the engine **and** a mock upstream (`go-httpbin`),
wired together with `DRY_RUN=false` - a safe, self-contained end-to-end storm
target on your machine.

## Endpoints

| Method | Path                         | Description                       |
| ------ | ---------------------------- | --------------------------------- |
| `POST` | `/chaos/subscription-churn`  | Subscription churn storm          |
| `POST` | `/chaos/service-1-flood`     | Service-1 fraud flood             |
| `POST` | `/chaos/service-2-storm`     | Service-2 IoT storm               |
| `GET`  | `/healthz`                   | Liveness probe                    |
| `GET`  | `/readyz`                    | Readiness + effective dry-run     |
| `GET`  | `/metrics`                   | Prometheus metrics                |
| `GET`  | `/docs`                      | Interactive OpenAPI docs          |

## Observability

Prometheus metrics are exposed at `/metrics`:

- `chaos_requests_total{scenario,outcome}` - synthetic requests fired.
- `chaos_storm_duration_seconds{scenario}` - wall-clock storm duration.
- `chaos_request_latency_seconds{scenario}` - per-request latency.

## CI

`.github/workflows/ci.yml` runs on every push and pull request: the pytest suite
across Python 3.10-3.12, `ruff` lint + format checks, and a Docker image build.

## Development

```shell
make fmt    # format & fix imports
make lint   # ruff check + format --check
make test   # pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and what CI expects.

## License

[MIT](LICENSE)
