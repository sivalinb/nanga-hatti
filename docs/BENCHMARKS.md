# Measured performance and its limits

Run `python -m nanga.cli benchmark` for authored measurements, or add `--live` with a configured provider key to include actual model latency. The report records UTC time, OS/architecture, Python version, CPU count, iteration count, concurrency, p50/p95/p99, wall time, achieved throughput, failures, actual execution modes, model calls and provider-reported tokens.

Measurements use `time.perf_counter()` around draft preparation through the review boundary. Human review time is excluded. The fixed authored baseline uses the same node functions, ledger writes and event writes in a predetermined sequence, with no LangGraph checkpoint persistence. LangGraph authored mode adds graph routing and disk checkpoints. This comparison measures their overhead; it does not establish that an agent is faster or more accurate.

The authored configurations run 120 measured preparations each, at concurrency 1 for the fixed baseline and concurrency 1, 4 and 8 for LangGraph. Three warmups per configuration are excluded. Concurrent LangGraph tasks share a serialized SQLite engine; latency includes waiting for that lock. Throughput is measured completions divided by the complete batch's wall time. Percentiles use nearest rank for p95/p99 and the median for p50.

The live configuration uses eight measured preparations and one excluded warmup. Its latency includes actual planning/composition HTTP calls. It reports every fallback or mixed result explicitly. With eight samples, a p95 is effectively a sample maximum, not a stable service percentile. API caching and unrelated host/network load can affect measurements. No artificial latency is inserted.

```sh
python -m nanga.cli benchmark --iterations 120
python -m nanga.cli benchmark --live --iterations 120
```

The public report is from the development machine; GitHub Actions also produces separate per-Python-version benchmark artifacts. Those CI artifacts are not substituted for the recorded development report. Requests served over HTTP, browser rendering and shared deployments need separate load tests before capacity planning. The repository makes no production RPS or end-user latency guarantee.

USD cost remains unknown for live calls unless a verified pricing schedule is configured. Reported tokens are available; they are not converted using guessed prices. The `/lab` page and [JSON report](../benchmarks/reports/latest.json) show actual measurements. The chart is generated from that JSON.
