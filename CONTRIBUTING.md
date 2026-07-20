# Contributing to fraud-chaos-lab

Thanks for your interest in improving fraud-chaos-lab! This guide covers the
local workflow and what CI expects.

## Prerequisites

- **Python 3.10+**
- **Docker** (only for `make up` and building the image)

## Getting started

```shell
make install   # create .venv and install the package with dev extras
make test      # run the suite
make run       # start the API (dry-run unless configured)
```

Configuration comes from the environment; copy `.env.example` to `.env` and
adjust as needed. The defaults keep the service in **dry-run**, so a fresh
checkout is completely inert.

## Development workflow

| Task                      | Command       |
| ------------------------- | ------------- |
| Format & fix imports      | `make fmt`    |
| Lint (ruff)               | `make lint`   |
| Run tests                 | `make test`   |
| Run the API server        | `make run`    |
| Fire one scenario once    | `make storm SCENARIO=service-1-flood` |
| Build the container image | `make docker` |

Run `make help` for the full list.

## Before opening a pull request

CI runs on every push and PR; please make sure these pass locally first:

1. **`make lint`** — `ruff check` and `ruff format --check` are clean.
2. **`make test`** — all tests pass.

## Guidelines

- **Safety first.** Real traffic is off by default and must stay that way. A
  fresh checkout, and any scenario without a configured target, must remain in
  dry-run. New scenarios must route their endpoints through `Settings.endpoint`
  so an unconfigured target degrades to dry-run automatically.
- Scenarios describe *what* traffic to generate; the engine
  (`app/chaos/engine.py`) owns *how* it is fanned out and measured. Keep that
  separation — put shared concurrency logic in the engine.
- Add tests for new behaviour. The engine and synthetic layers are pure and
  easy to test without a network; see `tests/test_engine.py`.
- Match the surrounding style: small modules, clear docstrings, type hints.

## Commit messages

Write a concise imperative subject line ("Add …", "Fix …") and a body that
explains the *why*. Group related changes into focused commits.
