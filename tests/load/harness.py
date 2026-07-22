"""
Load-harness infrastructure: server lifecycle, metrics scraping, and the
direct-Teradata observer.

The server under test runs unmodified against a REAL Teradata system — the
harness only controls its environment, drives MCP traffic at it, and watches
it from three vantage points (client, /metrics, Teradata itself).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("load-harness")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _first_line(e: BaseException, limit: int = 200) -> str:
    """Teradata driver errors carry full Go stack traces; keep line one."""
    return str(e).splitlines()[0][:limit]


@dataclass
class HarnessConfig:
    """Run configuration. database_uri points at the real Teradata system."""
    database_uri: str
    port: int = 18900
    pool_size: int = 10
    tool_timeout: float = 60.0
    pool_acquire_timeout: float = 5.0
    cache_ttl: float = 5.0
    max_sessions: int = 200
    duration: float = 60.0
    sessions: int = 50
    run_id: str = ""
    out_dir: Path = REPO_ROOT / "tests" / "load" / "results"
    observer_uri: str = ""  # defaults to database_uri

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def mcp_url(self) -> str:
        return f"{self.base_url}/mcp/"

    @property
    def service_user(self) -> str:
        return urlparse(self.database_uri).username or ""


class ServerController:
    """Launches the MCP server subprocess with a scenario-specific
    environment, waits for /health, samples RSS, and tears it down."""

    def __init__(self, cfg: HarnessConfig, log_path: Path):
        self.cfg = cfg
        self.log_path = log_path
        self.proc: Optional[subprocess.Popen] = None
        self.rss_samples: list[tuple[float, int]] = []

    async def start(self):
        env = os.environ.copy()
        env.update({
            "DATABASE_URI": self.cfg.database_uri,
            "MCP_TRANSPORT": "streamable-http",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(self.cfg.port),
            "MCP_STATELESS_HTTP": "true",
            "MCP_JSON_RESPONSE": "true",
            "DB_POOL_SIZE": str(self.cfg.pool_size),
            "TOOL_TIMEOUT": str(self.cfg.tool_timeout),
            "POOL_ACQUIRE_TIMEOUT": str(self.cfg.pool_acquire_timeout),
            "CACHE_TTL": str(self.cfg.cache_ttl),
            # Tag every query so DBAs can identify (and kill) harness traffic
            "QUERYBAND_EXTRA": f"HarnessRun={self.cfg.run_id}",
        })
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logfile = open(self.log_path, "w")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "tdwm_mcp"],
            env=env, cwd=REPO_ROOT,
            stdout=self._logfile, stderr=subprocess.STDOUT,
        )
        await self._wait_healthy()
        logger.info(f"Server up on {self.cfg.base_url} (pid={self.proc.pid})")

    async def _wait_healthy(self, timeout: float = 60.0):
        deadline = time.monotonic() + timeout
        async with httpx.AsyncClient() as client:
            while time.monotonic() < deadline:
                if self.proc.poll() is not None:
                    raise RuntimeError(
                        f"Server exited early (rc={self.proc.returncode}); see {self.log_path}")
                try:
                    r = await client.get(f"{self.cfg.base_url}/health", timeout=2.0)
                    if r.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
        raise RuntimeError(f"Server did not become healthy within {timeout}s; see {self.log_path}")

    def sample_rss(self):
        """Record the server's RSS (KB) via ps — no extra dependency."""
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            out = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(self.proc.pid)],
                capture_output=True, text=True, timeout=5)
            self.rss_samples.append((time.monotonic(), int(out.stdout.strip() or 0)))
        except Exception:
            pass

    @property
    def max_rss_mb(self) -> float:
        return max((r for _, r in self.rss_samples), default=0) / 1024.0

    async def stop(self):
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            await asyncio.to_thread(self.proc.wait, 15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            await asyncio.to_thread(self.proc.wait, 5)
        self._logfile.close()
        logger.info(f"Server stopped (rc={self.proc.returncode})")


_METRIC_RE = re.compile(r'^(\w+)(?:\{([^}]*)\})?\s+([0-9eE+.\-]+)$')


def _parse_metrics(text: str) -> dict[tuple[str, tuple], float]:
    """Parse Prometheus text format into {(name, sorted label items): value}."""
    out = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        m = _METRIC_RE.match(line.strip())
        if not m:
            continue
        name, labels_raw, value = m.groups()
        labels = tuple(sorted(
            tuple(p.split("=", 1)) for p in re.findall(r'\w+="[^"]*"', labels_raw or "")
        ))
        out[(name, labels)] = float(value)
    return out


class MetricsScraper:
    """Polls the server's /metrics endpoint during a run."""

    def __init__(self, base_url: str, interval: float = 2.0):
        self.base_url = base_url
        self.interval = interval
        self.snapshots: list[tuple[float, dict]] = []
        self._task: Optional[asyncio.Task] = None

    async def snapshot(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/metrics", timeout=5.0)
            self.snapshots.append((time.monotonic(), _parse_metrics(r.text)))

    def start(self, server: Optional[ServerController] = None):
        async def _loop():
            while True:
                try:
                    await self.snapshot()
                    if server:
                        server.sample_rss()
                except Exception as e:
                    logger.debug(f"metrics scrape failed: {e}")
                await asyncio.sleep(self.interval)
        self._task = asyncio.create_task(_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # final snapshot for accurate deltas
        try:
            await self.snapshot()
        except Exception:
            pass

    def value(self, name: str, snap: dict, **label_filter) -> float:
        """Sum a metric across label sets matching label_filter."""
        total = 0.0
        for (n, labels), v in snap.items():
            if n != name:
                continue
            ld = {k: val.strip('"') for k, val in labels}
            if all(ld.get(k) == str(want) for k, want in label_filter.items()):
                total += v
        return total

    def delta(self, name: str, **label_filter) -> float:
        if not self.snapshots:
            return 0.0
        first, last = self.snapshots[0][1], self.snapshots[-1][1]
        return self.value(name, last, **label_filter) - self.value(name, first, **label_filter)

    def peak(self, name: str, **label_filter) -> float:
        return max((self.value(name, snap, **label_filter)
                    for _, snap in self.snapshots), default=0.0)


class TDObserver:
    """Independent Teradata connection watching the server from the database
    side — the vantage point mocks can't provide.

    Polls the session count for the service account: it must never exceed
    pool_size (+ this observer's own margin is excluded by counting only the
    service user), and it proves cancellations actually terminate work in
    Teradata. Runs in a thread (the driver is blocking). Degrades gracefully
    if MONITOR privileges are missing.
    """

    def __init__(self, database_uri: str, service_user: str, interval: float = 3.0):
        self.database_uri = database_uri
        self.service_user = service_user
        self.interval = interval
        self.samples: list[tuple[float, int]] = []
        self.enabled = False
        self.error: Optional[str] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="td-observer")
        self._thread.start()

    def _run(self):
        try:
            import teradatasql
            from urllib.parse import unquote
            parsed = urlparse(self.database_uri)
            params = dict(
                host=parsed.hostname,
                user=unquote(parsed.username) if parsed.username else None,
                password=unquote(parsed.password) if parsed.password else None,
                database=parsed.path.lstrip("/") or None)
            # Honor the same auth mechanism the server uses (LDAP, KRB5, ...)
            logmech = os.getenv("DB_LOGMECH", "TD2")
            if logmech.upper() != "TD2":
                params["logmech"] = logmech
            if os.getenv("DB_LOGDATA"):
                params["logdata"] = os.getenv("DB_LOGDATA")
            conn = teradatasql.connect(**params)
        except Exception as e:
            self.error = f"observer connect failed: {_first_line(e)}"
            logger.warning(self.error)
            return
        self.enabled = True
        try:
            while not self._stop.is_set():
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT COUNT(*) FROM TABLE (MonitorSession(-1,'*',0)) AS t1 "
                        "WHERE UserName = ?", [self.service_user])
                    count = cur.fetchone()[0]
                    cur.close()
                    # exclude this observer's own session
                    self.samples.append((time.monotonic(), max(0, int(count) - 1)))
                except Exception as e:
                    self.error = f"observer poll failed: {_first_line(e)}"
                    logger.warning(self.error)
                    break
                self._stop.wait(self.interval)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    @property
    def max_sessions(self) -> Optional[int]:
        return max((c for _, c in self.samples), default=None) if self.enabled else None
