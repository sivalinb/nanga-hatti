import json
import math
import os
import platform
import statistics
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from .config import Settings
from .engine import Engine
from .evaluate import case_input,ROOT
from .content import resolve,search
from .models import Contribution

def percentile(values,p):return sorted(values)[max(0,math.ceil(len(values)*p)-1)]

def benchmark(live=False,iterations=120,write=True):
    if iterations<1:raise ValueError("iterations must be positive")
    cases=[c for c in json.loads((ROOT/"evals/cases.json").read_text()) if c["kind"]=="ordinary"]
    base=Settings();results=[]
    # Same node functions, ledger and event writes; only orchestration/checkpointing differs.
    def fixed(engine,case):
        run_id=uuid.uuid4().hex
        state={"run_id":run_id,"request":Contribution.model_validate(case_input(case)).model_dump(),"searches":0,"steps":0}
        with engine.lock:
            engine.store.begin(run_id)
            with engine.t.session(run_id) as rec:
                for fn in [engine.consent,engine.resolve,engine.plan,engine.retrieve,engine.plan,engine.compose,engine.validate]:
                    state.update(fn(state))
                rec.status=state["status"]
            engine.store.finish(run_id,rec.status,rec)
        return state["status"]=="waiting_review"
    for mode,concurrency in [("fixed authored preparation",1),("LangGraph authored",1),("LangGraph authored",4),("LangGraph authored",8)]+([("LangGraph live provider",1)] if live else []):
        n=min(iterations,8) if "live" in mode else iterations
        with tempfile.TemporaryDirectory() as tmp:
            engine=Engine(Settings(data_dir=Path(tmp),live="live" in mode,llm_key=base.llm_key if "live" in mode else "",braintrust_key=""))
            def task(i):
                start=time.perf_counter()
                if mode.startswith("fixed"):
                    ok=fixed(engine,cases[i%len(cases)]);return (time.perf_counter()-start)*1000,ok,0,0,"authored"
                try:
                    r=engine.start(case_input(cases[i%len(cases)],"live" in mode));ledger=r["ledger"]
                    return (time.perf_counter()-start)*1000,r["status"]=="waiting_review",ledger["calls"],ledger["input_tokens"]+ledger["output_tokens"],ledger["mode"]
                except Exception:return (time.perf_counter()-start)*1000,False,0,0,"error"
            for i in range(3 if "live" not in mode else 1):task(i)
            start=time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:measurements=list(pool.map(task,range(n)))
            wall=time.perf_counter()-start;lat=[m[0] for m in measurements]
            results.append({"mode":mode,"iterations":n,"concurrency":concurrency,"p50_ms":statistics.median(lat),"p95_ms":percentile(lat,.95),"p99_ms":percentile(lat,.99),"throughput_rps":n/wall,"wall_seconds":wall,"failures":sum(not m[1] for m in measurements),"model_calls":sum(m[2] for m in measurements),"reported_tokens":sum(m[3] for m in measurements),"actual_modes":{key:sum(m[4]==key for m in measurements) for key in sorted({m[4] for m in measurements})},"cost_usd":None if any(m[2] for m in measurements) else 0})
            engine.close()
    report={"created_at":datetime.now(timezone.utc).isoformat(),"environment":platform.system()+" "+platform.machine()+" · Python "+platform.python_version()+" · "+str(os.cpu_count())+" logical CPUs","warmups":"3 authored runs per configuration; 1 live run when enabled. Warmups excluded.","scope":"In-process wall-clock draft preparation through the review boundary; human review excluded. Fixed baseline uses the same authored node functions, ledger and event writes but has no LangGraph checkpoints. Concurrent LangGraph runs share a serialized SQLite engine. Live samples include actual provider latency and explicitly report fallback modes; sample size is small. No production throughput claim.","percentiles":"Nearest-rank p95/p99; median p50","results":results}
    if write:(ROOT/"benchmarks/reports/latest.json").write_text(json.dumps(report,indent=2))
    return report
