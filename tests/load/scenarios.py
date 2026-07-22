"""
Scenarios S1–S4: read-only workloads against a real Teradata system.

Each scenario returns a result dict consumed by report.py, including a list
of pass/fail checks with reasons. Config-change tools are deliberately
excluded from every mix.
"""

from __future__ import annotations

import asyncio
import logging
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .driver import (RunResults, call_once, classify, extract_session_no,
                     percentiles, run_constant_load, run_ramp)
from .harness import HarnessConfig, MetricsScraper, TDObserver

logger = logging.getLogger("load-scenarios")

# Tool mixes: (tool, args, weight). Read/monitor tools only.
MONITORING_MIX = [
    ("show_sessions", {}, 30),
    ("monitor_amp_load", {}, 20),
    ("show_tdwm_summary", {}, 20),
    ("monitor_awt", {}, 10),
    ("show_trottle_statistics", {"type": "ALL"}, 10),
    ("identify_blocking", {}, 10),
]

CACHEABLE_MIX = [
    ("list_WD", {}, 40),
    ("list_active_WD", {}, 30),
    ("list_rulesets", {}, 30),
]

LIGHT_MIX = [
    ("show_tdwm_summary", {}, 50),
    ("list_WD", {}, 50),
]


def _check(checks: list, name: str, ok: bool, detail: str):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    logger.info(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def _common_stats(results: RunResults, scraper: MetricsScraper,
                  observer: TDObserver, cfg: HarnessConfig) -> dict:
    lats = results.latencies(outcome="success")
    per_tool: dict[str, list[float]] = {}
    for c in results.calls:
        if c.outcome == "success":
            per_tool.setdefault(c.tool, []).append(c.latency)
    return {
        "calls": len(results.calls),
        "outcomes": results.outcomes(),
        "sessions_ok": results.sessions_ok,
        "session_failures": results.session_failures[:10],
        "latency_success": percentiles(lats),
        "per_tool_p95": {t: round(percentiles(v)["p95"], 3)
                         for t, v in sorted(per_tool.items())},
        "metrics": {
            "db_logins": scraper.delta("tdwm_mcp_db_logins_total"),
            "busy_rejections": scraper.delta("tdwm_mcp_pool_busy_rejections_total"),
            "cancellations": scraper.delta("tdwm_mcp_request_cancellations_total"),
            "connections_discarded": scraper.delta("tdwm_mcp_db_connections_discarded_total"),
            "cache_hits": scraper.delta("tdwm_mcp_tool_cache_hits_total"),
            "peak_pool_in_use": scraper.peak("tdwm_mcp_pool_connections_in_use"),
            "breaker_opened": scraper.peak("tdwm_mcp_breaker_open") > 0,
        },
        "teradata_observer": {
            "enabled": observer.enabled,
            "max_service_account_sessions": observer.max_sessions,
            "error": observer.error,
        },
    }


def _observer_check(checks: list, observer: TDObserver, cfg: HarnessConfig):
    if observer.enabled and observer.max_sessions is not None:
        _check(checks, "td_sessions_bounded",
               observer.max_sessions <= cfg.pool_size,
               f"max service-account sessions seen in Teradata = "
               f"{observer.max_sessions} (pool_size={cfg.pool_size})")
    else:
        _check(checks, "td_sessions_bounded", True,
               f"observer disabled ({observer.error or 'no data'}) — skipped")


# ---------------------------------------------------------------- S1

# Tools with no session-specific arguments; args chosen to be cheap and safe.
S1_CALLS: list[tuple[str, dict]] = [
    ("show_sessions", {}),
    ("show_physical_resources", {}),
    ("monitor_amp_load", {}),
    ("monitor_awt", {}),
    ("monitor_config", {}),
    ("identify_blocking", {}),
    ("list_active_WD", {}),
    ("list_WD", {}),
    ("list_delayed_request", {}),
    ("list_utility_stats", {}),
    ("display_delay_queue", {"type": "ALL"}),
    ("show_tdwm_summary", {}),
    ("show_trottle_statistics", {"type": "ALL"}),
    ("list_query_band", {"type": "ALL"}),
    ("show_cod_limits", {}),
    ("tdwm_list_clasification", {}),
    ("show_top_users", {"top_n": 10}),
    ("show_sw_event_log", {"Type": "ALL"}),
    ("show_tasm_statistics", {}),
    ("show_tasm_even_history", {"hours": 24}),
    ("show_tasm_rule_history_red", {}),
    ("list_rulesets", {}),
]

SESSION_SCOPED_TOOLS = [
    "show_sql_text_for_session",
    "show_sql_steps_for_session",
    "monitor_session_query_band",
]


async def s1_live_parity(cfg: HarnessConfig, scraper: MetricsScraper,
                         observer: TDObserver) -> dict:
    """Call every read tool once against the live system and validate the
    response — the live-Teradata validation this codebase has been missing."""
    results = RunResults()
    tool_reports = []
    async with streamablehttp_client(cfg.mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            results.sessions_ok += 1

            calls = list(S1_CALLS)
            calls.append(("show_query_log",
                          {"user": cfg.service_user, "hours": 24, "top_n": 10}))
            session_no = await extract_session_no(session, cfg.tool_timeout + 10)
            if session_no is not None:
                for tool in SESSION_SCOPED_TOOLS:
                    calls.append((tool, {"sessionNo": session_no}))

            for tool, args in calls:
                outcome, text = await call_once(
                    session, tool, args, results, cfg.tool_timeout + 10)
                tool_reports.append({
                    "tool": tool, "outcome": outcome,
                    "preview": text[:120],
                })

    failed = [t for t in tool_reports if t["outcome"] not in ("success",)]
    checks: list = []
    _check(checks, "all_tools_live",
           not failed,
           f"{len(tool_reports) - len(failed)}/{len(tool_reports)} tools succeeded"
           + (f"; failing: {[t['tool'] for t in failed]}" if failed else ""))
    _observer_check(checks, observer, cfg)

    stats = _common_stats(results, scraper, observer, cfg)
    stats["tool_reports"] = tool_reports
    return {"scenario": "S1 live-parity smoke", "checks": checks, "stats": stats}


# ---------------------------------------------------------------- S2

async def s2_monitoring_storm(cfg: HarnessConfig, scraper: MetricsScraper,
                              observer: TDObserver) -> dict:
    """N sessions of realistic monitoring traffic; baseline latency/error rate."""
    results = await run_constant_load(
        cfg.mcp_url, sessions=cfg.sessions, duration=cfg.duration,
        mix=MONITORING_MIX, think=(0.5, 1.5),
        client_timeout=cfg.tool_timeout + 15)

    outcomes = results.outcomes()
    total = max(1, len(results.calls))
    hard_errors = (outcomes.get("error", 0) + outcomes.get("client_error", 0)
                   + outcomes.get("connection_error", 0))
    lat = percentiles(results.latencies(outcome="success"))

    checks: list = []
    _check(checks, "sessions_established",
           results.sessions_ok == cfg.sessions,
           f"{results.sessions_ok}/{cfg.sessions} sessions initialized")
    _check(checks, "hard_error_rate_lt_1pct",
           hard_errors / total < 0.01,
           f"{hard_errors}/{total} hard errors ({hard_errors / total:.2%})")
    _check(checks, "p99_under_2x_timeout",
           lat["p99"] < cfg.tool_timeout,
           f"success P50={lat['p50']:.2f}s P95={lat['p95']:.2f}s P99={lat['p99']:.2f}s")
    _observer_check(checks, observer, cfg)

    return {"scenario": f"S2 monitoring storm ({cfg.sessions} sessions, {cfg.duration:.0f}s)",
            "checks": checks,
            "stats": _common_stats(results, scraper, observer, cfg)}


# ---------------------------------------------------------------- S3

async def s3_cache_proof(cfg: HarnessConfig, scraper: MetricsScraper,
                         observer: TDObserver) -> dict:
    """Hammer cacheable metadata tools; DB round trips must be << tool calls."""
    results = await run_constant_load(
        cfg.mcp_url, sessions=cfg.sessions, duration=min(cfg.duration, 30.0),
        mix=CACHEABLE_MIX, think=(0.1, 0.3),
        client_timeout=cfg.tool_timeout + 15)

    total = len(results.calls)
    cache_hits = scraper.delta("tdwm_mcp_tool_cache_hits_total")
    successes = results.outcomes().get("success", 0)
    hit_ratio = cache_hits / max(1, successes)

    checks: list = []
    _check(checks, "cache_hit_ratio_gt_70pct",
           hit_ratio > 0.70,
           f"{cache_hits:.0f} cache hits / {successes} successful calls = {hit_ratio:.0%}")
    _check(checks, "no_busy_under_cached_load",
           results.outcomes().get("busy", 0) == 0,
           f"busy rejections: {results.outcomes().get('busy', 0)} "
           "(cached traffic should barely touch the pool)")
    _observer_check(checks, observer, cfg)

    return {"scenario": f"S3 cache proof ({cfg.sessions} sessions)",
            "checks": checks,
            "stats": _common_stats(results, scraper, observer, cfg)}


# ---------------------------------------------------------------- S4

async def s4_saturation_ramp(cfg: HarnessConfig, scraper: MetricsScraper,
                             observer: TDObserver) -> dict:
    """Ramp to max_sessions or the busy knee; verify fail-fast and recovery."""
    results, steps = await run_ramp(
        cfg.mcp_url, max_sessions=cfg.max_sessions, step_size=20,
        step_duration=15.0, mix=LIGHT_MIX, think=(0.2, 0.6),
        client_timeout=cfg.tool_timeout + 15)

    busy_lats = results.latencies(outcome="busy")
    busy_p95 = percentiles(busy_lats)["p95"]
    knee = next((s.sessions for s in steps[:-1]
                 if s.calls and s.busy / s.calls >= 0.5), None)
    recovery = steps[-1]

    checks: list = []
    _check(checks, "busy_errors_fail_fast",
           (not busy_lats) or busy_p95 < cfg.pool_acquire_timeout + 2.0,
           f"{len(busy_lats)} busy rejections, P95 latency {busy_p95:.2f}s "
           f"(acquire timeout {cfg.pool_acquire_timeout:.0f}s)")
    _check(checks, "no_client_hangs",
           results.outcomes().get("client_timeout", 0) == 0,
           f"client-side timeouts: {results.outcomes().get('client_timeout', 0)}")
    _check(checks, "recovers_after_saturation",
           recovery.calls > 0 and recovery.success / max(1, recovery.calls) > 0.95,
           f"recovery phase: {recovery.success}/{recovery.calls} successes at 3 sessions")
    _observer_check(checks, observer, cfg)

    stats = _common_stats(results, scraper, observer, cfg)
    stats["ramp_steps"] = [
        {"sessions": s.sessions, "calls": s.calls, "busy": s.busy,
         "success": s.success, "p95": round(s.p95, 3)}
        for s in steps]
    stats["knee_sessions"] = knee
    return {"scenario": f"S4 saturation ramp (to {cfg.max_sessions} sessions)",
            "checks": checks, "stats": stats}


SCENARIOS = {
    "s1": s1_live_parity,
    "s2": s2_monitoring_storm,
    "s3": s3_cache_proof,
    "s4": s4_saturation_ramp,
}
