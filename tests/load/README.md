# Load harness — real-Teradata concurrency testing

Tests the limits and scale of the TDWM MCP server against a **real Teradata
system** — no mocked connectivity. You supply the system and credentials; the
harness launches the server, drives real MCP client traffic at it, and
observes from three vantage points:

1. **Client side** — per-call latency percentiles and a structured outcome
   taxonomy (`success` / `busy` / `timeout` / `breaker_open` / errors).
2. **Server side** — continuous `/metrics` scraping (pool gauges, busy
   rejections, cancellations, cache hits, breaker state) plus process RSS.
3. **Teradata side** — an independent `teradatasql` observer connection
   polling `MonitorSession`, proving the service account's session count
   never exceeds the pool size and that aborted work actually disappears
   from the database. Requires MONITOR privilege; degrades gracefully.

## Usage

```bash
python -m tests.load \
    --database-uri "teradata://user:password@tdhost/database" \
    --scenario s1 s2 s3 s4 \
    --pool-size 10 --sessions 50 --duration 60 --max-sessions 200
```

`DATABASE_URI` env is used if `--database-uri` is omitted. Use
`--observer-uri` (or `HARNESS_OBSERVER_URI`) to give the observer separate
credentials.

Results land in `tests/load/results/<run_id>/`: `report.md` (pass/fail
checks, latency tables, ramp profile), `data.json` (raw, machine-readable),
and `server.log`.

## Scenarios

| ID | What it does | What it proves |
|----|--------------|----------------|
| S1 | Every read tool called once, live | Live-parity: all tools work against this Teradata version |
| S2 | N sessions of monitoring traffic (think time 0.5–1.5s) | Baseline latency/error rate under realistic load |
| S3 | N sessions hammering cacheable metadata tools | Single-flight + TTL cache collapse DB round trips |
| S4 | Ramp +20 sessions/15s to 200 or the busy knee, then recovery | Capacity knee, fail-fast under saturation, clean recovery |

## Safety

- **Read-only**: no config-change tools (throttles/filters/activate) appear
  in any mix.
- Every query is tagged `HarnessRun=<run_id>` in the QueryBand — DBAs can
  find and abort harness traffic instantly via DBQL/MonitorSession.
- The ramp holds only one step past the saturation knee, then backs off.
- Use a dedicated test account: the harness measures the MCP server, and the
  account needs MONITOR privileges and read access to `dbc.qrylogv`.

## Interpreting S4

The "knee" is where busy rejections exceed 50% of a step's calls — that's
the honest concurrency capacity for the configured `--pool-size` and think
time. Capacity scales with pool size until Teradata (not the server) becomes
the limit; rerun with different `--pool-size` values to find that crossover.
Horizontal scale beyond one process = N replicas in stateless mode behind a
round-robin LB.
