# Run and inspect a local workspace

Use Python 3.12+ and install `requirements.txt`. `python run.py` listens on 127.0.0.1:8787 with authored decision-making. The map uses a bundled OpenStreetMap geometry snapshot; no tile service or geocoding key is required. `/health` checks liveness, `/lab` shows evidence and `/metrics` exposes bounded Prometheus metrics.

For live AI, export `NANGA_LIVE_AI=1` and `NEBIUS_API_KEY`, or set `NANGA_LLM_KEY_FILE` to a private key file outside this repository. Set `BRAINTRUST_API_KEY` or `NANGA_BRAINTRUST_KEY_FILE` to enable redacted remote spans. The app does not automatically load `.env`; Compose uses it for its own variable interpolation. Never commit a real environment or key file. The configured model is explicit in `.env.example` and can be changed with `NANGA_LLM_MODEL`; validate another model with the live suite before using it.

Live generation is opt-in per contribution. Provider failures or malformed responses fall back to authored metadata while preserving the memory. There are at most two source searches, a graph recursion limit and a per-call timeout; there are no automatic billable retries. Provider-reported tokens are retained for invalid output. Dollar cost is unknown without an explicitly configured input/output schedule.

## Monitoring stack

```sh
# Set GRAFANA_ADMIN_PASSWORD in a private .env or shell first.
docker compose up --build -d
```

The app, Prometheus and Grafana are published only on localhost: 8787, 9098 and 3018. Grafana uses your configured password. Two provisioned dashboards contain 16 panels: **Workflow & performance** and **Quality & contributor review**. Three Prometheus alert rules check target availability, model failures and critical last-recorded eval scores. They have no external notification destination.

Compose creates a dedicated 172.29.18.0/24 network and explicitly trusts that subnet for internal scraping and browser connections forwarded by Docker. The native app trusts only loopback clients. Setting `NANGA_SERVER_TOKEN` switches API and metrics access to bearer-token authentication; the token is not embedded in the frontend. The included Compose stack is for local use, not an internet deployment. For a token-enabled workspace, set `sessionStorage.setItem("nanga-token", "your workspace token")` in that browser's console, then reload; do not paste a provider key there.

Sparse traffic can leave rate-based percentile panels empty until enough observations arrive. Histograms provide estimates bounded by their buckets; per-run event timings and the benchmark report contain direct measurements. Evaluation gauges load when `/api/evidence` is read and describe only the last local curated suite. Read each panel's title and the methodology before interpreting a percentage.

On the development host, native Prometheus 3.14.0 and Grafana 12.1.1 were used to inspect the dashboards. See [validation](VALIDATION.md) for the completed checks and Docker's verification status. Existing installations can use `ops/prometheus.yml` with an adjusted scrape address and the supplied provisioning files. The native preview enables anonymous Viewer access only on 127.0.0.1; Compose keeps password-based access.

## Data and deployment

Private records and checkpoints live in `NANGA_DATA_DIR` (default `data/private`). Back up both SQLite databases when the process is stopped; checkpoint state is necessary for pending reviews. Browser media requires separate downloads from each story. Deleting browser storage does not remove server-side text and checkpoints, and deleting the server data does not remove browser media.

The public explorer is built with `python -m nanga.cli preview` into `dist`. It contains only fictional starter content and fictional evaluation evidence, not contributor records. The Pages workflow builds and deploys that static explorer. Run contribution/review in the local Python app. A shared backend requires authenticated contributor identities, ownership checks, quotas, retention controls, backups and community-defined access practices; these are not claimed in this single-owner release.
