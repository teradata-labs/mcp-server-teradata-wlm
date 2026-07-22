"""
Load driver: real MCP client sessions generating tool traffic.

Each worker is a full MCP client (streamable-http, stateless) with its own
session — exactly what production agents look like. Outcomes are classified
from the server's structured error messages so the report can distinguish
"the server protected itself" (busy, timeout) from "something broke" (error).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger("load-driver")


def classify(text: str) -> str:
    """Map a tool response to an outcome bucket."""
    if text.startswith("Database connection error:"):
        if "Server busy" in text:
            return "busy"
        if "circuit breaker" in text:
            return "breaker_open"
        return "connection_error"
    if "timed out after" in text:
        return "timeout"
    if text.startswith(("Error", "Authorization Error", "Input validation error", "Unsupported tool")):
        return "error"
    return "success"


@dataclass
class CallRecord:
    ts: float
    tool: str
    outcome: str
    latency: float


@dataclass
class RunResults:
    calls: list[CallRecord] = field(default_factory=list)
    sessions_ok: int = 0
    session_failures: list[str] = field(default_factory=list)

    def record(self, tool: str, outcome: str, latency: float):
        self.calls.append(CallRecord(time.monotonic(), tool, outcome, latency))

    def outcomes(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.calls:
            out[c.outcome] = out.get(c.outcome, 0) + 1
        return out

    def latencies(self, outcome: str = None, since: float = None) -> list[float]:
        return [c.latency for c in self.calls
                if (outcome is None or c.outcome == outcome)
                and (since is None or c.ts >= since)]


def percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    v = sorted(values)
    def pct(p): return v[min(len(v) - 1, int(len(v) * p))]
    return {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99), "max": v[-1]}


def pick_weighted(mix: list[tuple[str, dict, float]]) -> tuple[str, dict]:
    total = sum(w for _, _, w in mix)
    r = random.random() * total
    for tool, args, w in mix:
        r -= w
        if r <= 0:
            return tool, args
    return mix[-1][0], mix[-1][1]


async def call_once(session: ClientSession, tool: str, args: dict,
                    results: RunResults, client_timeout: float):
    t0 = time.perf_counter()
    try:
        res = await asyncio.wait_for(session.call_tool(tool, args), timeout=client_timeout)
        text = res.content[0].text if res.content else ""
        outcome = classify(text)
    except (asyncio.TimeoutError, TimeoutError):
        outcome = "client_timeout"
        text = ""
    except Exception as e:
        outcome = "client_error"
        text = str(e)
    results.record(tool, outcome, time.perf_counter() - t0)
    return outcome, text


async def worker(url: str, mix: list[tuple[str, dict, float]],
                 think: tuple[float, float], stop: asyncio.Event,
                 results: RunResults, client_timeout: float):
    """One MCP client session issuing tool calls until stopped."""
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                results.sessions_ok += 1
                while not stop.is_set():
                    tool, args = pick_weighted(mix)
                    await call_once(session, tool, args, results, client_timeout)
                    delay = random.uniform(*think)
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=delay)
                    except (asyncio.TimeoutError, TimeoutError):
                        pass
    except asyncio.CancelledError:
        raise
    except Exception as e:
        results.session_failures.append(f"{type(e).__name__}: {e}")


async def run_constant_load(url: str, sessions: int, duration: float,
                            mix: list[tuple[str, dict, float]],
                            think: tuple[float, float],
                            client_timeout: float) -> RunResults:
    """N concurrent sessions for a fixed duration."""
    results = RunResults()
    stop = asyncio.Event()
    tasks = [asyncio.create_task(worker(url, mix, think, stop, results, client_timeout))
             for _ in range(sessions)]
    await asyncio.sleep(duration)
    stop.set()
    done, pending = await asyncio.wait(tasks, timeout=30)
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    return results


@dataclass
class RampStep:
    sessions: int
    started_at: float
    calls: int = 0
    busy: int = 0
    success: int = 0
    p95: float = 0.0


async def run_ramp(url: str, max_sessions: int, step_size: int,
                   step_duration: float, mix: list[tuple[str, dict, float]],
                   think: tuple[float, float], client_timeout: float,
                   busy_stop_ratio: float = 0.5) -> tuple[RunResults, list[RampStep]]:
    """Add step_size sessions every step_duration until max_sessions or the
    busy ratio exceeds busy_stop_ratio for a full step (the knee), then run
    one more step and a recovery phase at low concurrency."""
    results = RunResults()
    stop = asyncio.Event()
    tasks: list[asyncio.Task] = []
    steps: list[RampStep] = []
    knee_hit = False

    current = 0
    while current < max_sessions:
        add = min(step_size, max_sessions - current)
        tasks += [asyncio.create_task(worker(url, mix, think, stop, results, client_timeout))
                  for _ in range(add)]
        current += add
        step = RampStep(sessions=current, started_at=time.monotonic())
        await asyncio.sleep(step_duration)

        window = [c for c in results.calls if c.ts >= step.started_at]
        step.calls = len(window)
        step.busy = sum(1 for c in window if c.outcome == "busy")
        step.success = sum(1 for c in window if c.outcome == "success")
        step.p95 = percentiles([c.latency for c in window])["p95"]
        steps.append(step)
        logger.info(
            f"ramp: {current} sessions -> {step.calls} calls, "
            f"{step.busy} busy, p95={step.p95:.2f}s")

        if step.calls and step.busy / step.calls >= busy_stop_ratio:
            if knee_hit:
                break  # one extra step past the knee is enough
            knee_hit = True

    stop.set()
    done, pending = await asyncio.wait(tasks, timeout=30)
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    # Recovery phase: light load must succeed again after saturation
    recovery = await run_constant_load(url, sessions=3, duration=10.0,
                                       mix=mix, think=think,
                                       client_timeout=client_timeout)
    rec_step = RampStep(sessions=3, started_at=time.monotonic())
    rec_step.calls = len(recovery.calls)
    rec_step.success = sum(1 for c in recovery.calls if c.outcome == "success")
    rec_step.busy = sum(1 for c in recovery.calls if c.outcome == "busy")
    rec_step.p95 = percentiles([c.latency for c in recovery.calls])["p95"]
    steps.append(rec_step)
    results.calls += recovery.calls
    return results, steps


async def extract_session_no(session: ClientSession, client_timeout: float) -> Optional[int]:
    """Pull a live SessionNo out of show_sessions for the session-scoped tools."""
    try:
        res = await asyncio.wait_for(session.call_tool("show_sessions", {}), timeout=client_timeout)
        text = res.content[0].text if res.content else ""
        data = json.loads(text)
        cols = [c.upper() for c in data.get("columns", [])]
        idx = cols.index("SESSIONNO") if "SESSIONNO" in cols else None
        if idx is not None and data.get("rows"):
            return int(data["rows"][0][idx])
    except Exception:
        pass
    return None
