"""Build the public read-only explorer; never export the local collection."""
import json
import shutil
from pathlib import Path
from .content import PLACES,SOURCES,FACTS,SEEDS,CORPUS_HASH
from .evaluate import ROOT

def build():
    static=ROOT/"static"
    catalog={"places":PLACES,"sources":SOURCES,"facts":FACTS,"seeds":SEEDS,"corpus_version":CORPUS_HASH,"workspace":"public-preview"}
    (static/"catalog.json").write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    reports={}
    for key,path in [("evals",ROOT/"evals/reports/latest.json"),("benchmarks",ROOT/"benchmarks/reports/latest.json")]:
        reports[key]=json.loads(path.read_text()) if path.exists() else None
        (static/("evals.json" if key=="evals" else "benchmarks.json")).write_text(json.dumps(reports[key],indent=2))
    live_path=ROOT/"evals/reports/live-traces.json"
    recorded=json.loads(live_path.read_text()) if live_path.exists() else []
    # This file is made only by the evaluator from fictional public fixture cases.
    permitted={c["memory"] for c in json.loads((ROOT/"evals/cases.json").read_text())}
    for r in recorded:
        if r.get("draft",{}).get("memory") not in permitted:raise RuntimeError("Only fictional evaluation traces may enter a public preview")
    live_report=ROOT/"evals/reports/live.json"
    evidence={"runs":[r["ledger"] for r in recorded],"recorded_runs":recorded,"braintrust":"recorded trace links" if recorded else "not recorded","corpus_version":CORPUS_HASH,"reports":reports,"live_evals":json.loads(live_report.read_text()) if live_report.exists() else None}
    (static/"evidence.json").write_text(json.dumps(evidence,indent=2))
    dist=ROOT/"dist"
    if dist.exists():shutil.rmtree(dist)
    dist.mkdir();shutil.copytree(static,dist/"static")
    shutil.copy2(static/"index.html",dist/"index.html");shutil.copy2(static/"lab.html",dist/"lab.html")
    # Extensionless evidence link works on a static host with a directory index.
    (dist/"lab").mkdir();lab=(static/"lab.html").read_text().replace('<head>','<head><base href="../">')
    (dist/"lab/index.html").write_text(lab)
    (dist/".nojekyll").touch()
    return {"dist":str(dist),"local_collection_exported":False,"fictional_recorded_runs":len(recorded)}
