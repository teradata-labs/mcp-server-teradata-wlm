"""
CLI entry point for the load harness.

Usage (from the repo root, with the project venv):

    python -m tests.load --scenario s1 s2 s3 s4 \\
        --database-uri teradata://user:pass@host/db \\
        --pool-size 10 --sessions 50 --duration 60

DATABASE_URI can also come from the environment. The harness launches the
MCP server itself with the scenario environment, drives real MCP traffic at
it, scrapes /metrics, watches Teradata through an independent observer
connection, and writes tests/load/results/<run_id>/report.md + data.json.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .harness import HarnessConfig, MetricsScraper, ServerController, TDObserver
from .report import write_report
from .scenarios import SCENARIOS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="tests.load", description=__doc__)
    p.add_argument("--database-uri", default=os.getenv("DATABASE_URI"),
                   help="teradata://user:pass@host/db for the REAL system "
                        "(default: DATABASE_URI env)")
    p.add_argument("--observer-uri", default=os.getenv("HARNESS_OBSERVER_URI", ""),
                   help="Optional separate credentials for the Teradata observer "
                        "(default: same as --database-uri)")
    p.add_argument("--scenario", nargs="+", default=["s1", "s2", "s3", "s4"],
                   choices=sorted(SCENARIOS), help="Scenarios to run, in order")
    p.add_argument("--sessions", type=int, default=50,
                   help="Concurrent sessions for S2/S3 (default 50)")
    p.add_argument("--max-sessions", type=int, default=200,
                   help="Ramp ceiling for S4 (default 200)")
    p.add_argument("--duration", type=float, default=60.0,
                   help="Steady-state duration in seconds for S2 (default 60)")
    p.add_argument("--pool-size", type=int, default=10)
    p.add_argument("--tool-timeout", type=float, default=60.0)
    p.add_argument("--acquire-timeout", type=float, default=5.0)
    p.add_argument("--cache-ttl", type=float, default=5.0)
    p.add_argument("--port", type=int, default=18900)
    p.add_argument("--out", type=Path,
                   default=Path(__file__).resolve().parent / "results")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    cfg = HarnessConfig(
        database_uri=args.database_uri,
        observer_uri=args.observer_uri or args.database_uri,
        port=args.port,
        pool_size=args.pool_size,
        tool_timeout=args.tool_timeout,
        pool_acquire_timeout=args.acquire_timeout,
        cache_ttl=args.cache_ttl,
        sessions=args.sessions,
        max_sessions=args.max_sessions,
        duration=args.duration,
        run_id=run_id,
        out_dir=args.out,
    )

    server = ServerController(cfg, cfg.out_dir / run_id / "server.log")
    await server.start()

    observer = TDObserver(cfg.observer_uri, cfg.service_user)
    observer.start()

    scenario_results = []
    try:
        for name in args.scenario:
            logging.info(f"=== Running {name} ===")
            scraper = MetricsScraper(cfg.base_url)
            await scraper.snapshot()
            scraper.start(server)
            try:
                result = await SCENARIOS[name](cfg, scraper, observer)
            finally:
                await scraper.stop()
            scenario_results.append(result)
            await asyncio.sleep(3)  # let the pool settle between scenarios
    finally:
        observer.stop()
        await server.stop()

    report_path = write_report(
        cfg.out_dir, run_id,
        config={
            "pool_size": cfg.pool_size,
            "tool_timeout": cfg.tool_timeout,
            "pool_acquire_timeout": cfg.pool_acquire_timeout,
            "cache_ttl": cfg.cache_ttl,
            "sessions": cfg.sessions,
            "max_sessions": cfg.max_sessions,
            "duration": cfg.duration,
            "scenarios": args.scenario,
        },
        scenario_results=scenario_results,
        server_info={"max_rss_mb": server.max_rss_mb},
    )
    print(f"\nReport: {report_path}")

    all_ok = all(c["ok"] for r in scenario_results for c in r["checks"])
    print(f"Overall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args()
    if not args.database_uri:
        print("error: provide --database-uri or set DATABASE_URI "
              "(teradata://user:pass@host/db)", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
