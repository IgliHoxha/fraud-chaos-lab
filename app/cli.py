"""Command-line entrypoint.

Mirrors the two ways you run the lab:

* ``serve``  - start the HTTP API (the long-running service).
* ``storm``  - fire a single scenario once and print the result, then exit.
              Handy as a cron/Kubernetes Job for scheduled game-days.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app import __version__
from app.chaos import scenarios
from app.config import get_settings
from app.models import StormRequest

SCENARIOS = {
    "subscription-churn": scenarios.subscription_churn,
    "service-1-flood": scenarios.service_1_flood,
    "service-2-storm": scenarios.service_2_storm,
}


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=args.host or settings.http_host,
        port=args.port or settings.http_port,
        reload=args.reload,
    )
    return 0


def _storm(args: argparse.Namespace) -> int:
    settings = get_settings()
    run = SCENARIOS[args.scenario]
    request = StormRequest(count=args.count, concurrency=args.concurrency, dry_run=args.dry_run)
    result = asyncio.run(run(request, settings))
    print(json.dumps(result.model_dump(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fraud-chaos-lab", description="Fraud Chaos Lab")
    parser.add_argument("--version", action="version", version=f"fraud-chaos-lab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the HTTP API server")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev)")
    serve.set_defaults(func=_serve)

    storm = sub.add_parser("storm", help="Fire one scenario once and exit")
    storm.add_argument("scenario", choices=sorted(SCENARIOS))
    storm.add_argument("--count", type=int, default=None)
    storm.add_argument("--concurrency", type=int, default=None)
    dry = storm.add_mutually_exclusive_group()
    dry.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    dry.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    storm.set_defaults(func=_storm)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
