from nanga.benchmark import benchmark

def test_all_benchmark_paths_complete_preparation():
    report=benchmark(iterations=2,write=False)
    assert len(report["results"])==4
    assert all(r["failures"]==0 and r["iterations"]==2 and r["p95_ms"]>=r["p50_ms"] for r in report["results"])
