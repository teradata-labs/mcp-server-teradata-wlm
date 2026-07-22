"""
Report generation: one JSON artifact + one markdown summary per run,
so runs are comparable over time.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_report(out_dir: Path, run_id: str, config: dict,
                 scenario_results: list[dict], server_info: dict) -> Path:
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "config": config,
        "server": server_info,
        "scenarios": scenario_results,
    }
    (run_dir / "data.json").write_text(json.dumps(data, indent=2, default=str))

    lines = [
        f"# TDWM MCP Server load test — {run_id}",
        "",
        f"- **Date:** {data['timestamp']}",
        f"- **Pool size:** {config['pool_size']}  |  **Tool timeout:** {config['tool_timeout']}s"
        f"  |  **Acquire timeout:** {config['pool_acquire_timeout']}s  |  **Cache TTL:** {config['cache_ttl']}s",
        f"- **Server peak RSS:** {server_info.get('max_rss_mb', 0):.0f} MB",
        f"- **QueryBand tag:** `HarnessRun={run_id}` (visible in DBQL / MonitorSession)",
        "",
    ]

    overall_ok = True
    for res in scenario_results:
        checks = res["checks"]
        ok = all(c["ok"] for c in checks)
        overall_ok = overall_ok and ok
        stats = res["stats"]
        lines += [
            f"## {'✅' if ok else '❌'} {res['scenario']}",
            "",
            f"- Calls: **{stats['calls']}** | Outcomes: "
            + ", ".join(f"{k}={v}" for k, v in sorted(stats["outcomes"].items())),
            f"- Success latency: P50 {stats['latency_success']['p50']:.2f}s | "
            f"P95 {stats['latency_success']['p95']:.2f}s | "
            f"P99 {stats['latency_success']['p99']:.2f}s",
            f"- Server metrics Δ: logins={stats['metrics']['db_logins']:.0f}, "
            f"busy={stats['metrics']['busy_rejections']:.0f}, "
            f"cancels={stats['metrics']['cancellations']:.0f}, "
            f"cache_hits={stats['metrics']['cache_hits']:.0f}, "
            f"peak_pool_in_use={stats['metrics']['peak_pool_in_use']:.0f}",
        ]
        td = stats.get("teradata_observer", {})
        if td.get("enabled"):
            lines.append(
                f"- Teradata observer: max service-account sessions = "
                f"**{td['max_service_account_sessions']}**")
        else:
            lines.append(f"- Teradata observer: disabled ({td.get('error') or 'n/a'})")
        lines.append("")
        lines.append("| Check | Result | Detail |")
        lines.append("|---|---|---|")
        for c in checks:
            lines.append(f"| {c['name']} | {'PASS' if c['ok'] else '**FAIL**'} | {c['detail']} |")
        lines.append("")

        if "ramp_steps" in stats:
            lines.append("### Ramp profile")
            lines.append("")
            lines.append("| Sessions | Calls | Success | Busy | P95 (s) |")
            lines.append("|---|---|---|---|---|")
            for s in stats["ramp_steps"]:
                lines.append(f"| {s['sessions']} | {s['calls']} | {s['success']} "
                             f"| {s['busy']} | {s['p95']} |")
            if stats.get("knee_sessions"):
                lines.append("")
                lines.append(f"**Saturation knee: ~{stats['knee_sessions']} sessions** "
                             f"at pool_size={config['pool_size']}.")
            lines.append("")

        if "tool_reports" in stats:
            failed = [t for t in stats["tool_reports"] if t["outcome"] != "success"]
            if failed:
                lines.append("### Failing tools")
                lines.append("")
                lines.append("| Tool | Outcome | Response preview |")
                lines.append("|---|---|---|")
                for t in failed:
                    preview = t["preview"].replace("|", "\\|").replace("\n", " ")
                    lines.append(f"| {t['tool']} | {t['outcome']} | {preview} |")
                lines.append("")

    lines.insert(1, "")
    lines.insert(2, f"**Overall: {'PASS ✅' if overall_ok else 'FAIL ❌'}**")

    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines))
    return report_path
