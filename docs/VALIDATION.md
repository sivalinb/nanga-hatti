# Release validation · 13 October 2026

Validated on Darwin arm64 with Python 3.12.14. Public deployment and CI results can be inspected in the repository's Actions history.

| Area | Completed check |
| --- | --- |
| Python | 29 tests passed after the Nanga Hatti rename |
| Authored evaluation | 50 workflow fixtures; all eight engineering guards passed |
| Retrieval | 20 authored queries; Recall@3 1.000, MRR@3 0.975 |
| Live evaluation | 8/8 fully live cases; 22 calls, 10,566 reported tokens; Braintrust experiment uploaded |
| Benchmark | Four authored configurations with 120 measurements each, plus eight live measurements; zero failures |
| Browser contribution | Fictional example, live opt-in, review title edit, context removal, approval and private collection verified |
| Restart | Waiting review restored after stopping/restarting the native server; approval resumed successfully |
| Media | Synthetic two-second audio and the fictional illustration uploaded to browser storage; both visible and separately downloadable after page reload |
| Map | Bundled OSM roads/water geometry and selectable town markers loaded without remote tiles |
| Responsive | 390 × 844 browser viewport checked; document width 390 with no horizontal overflow |
| JavaScript | Both app and evidence scripts passed Node syntax checks |
| Monitoring | Native Grafana 12.1.1 dashboards loaded against Prometheus 3.14.0; scrape target `up=1`, model calls/tokens visible |
| Rules | Promtool validated all three Prometheus alert rules |
| Static export | Builder excludes the collection database; fictional trace memories checked against public fixture set |

The native monitoring preview used an isolated Prometheus port (9099) because an existing user service occupied 9098. The included Compose mapping remains 9098. The app and Grafana previews used 8787 and 3018.

Docker/Compose was not executed because Docker is unavailable on this host. Source configuration is included; a verified native monitoring preview is not a Docker build result. No production shared backend, community data collection, language/pronunciation evaluation, culture validation, public Grafana service, or load-tested deployment is claimed.

Benchmark timings exclude human review and HTTP/browser transport. Live cases are a small curated suite. Engineering guard percentages are not broad semantic or cultural accuracy percentages. See [eval methodology](EVALS.md) and [benchmark methodology](BENCHMARKS.md).

Illustration is fictional and AI-generated. UI and Grafana screenshots show the working application, using fictional test input. Historical experiment URLs in the earlier mixed-mode report preserve the original project name; they are not relabeled as new executions.
