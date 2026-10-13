import json
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from .config import Settings
from .engine import Engine
from .models import Composition,Decision
from .content import search,resolve,CORPUS_HASH

ROOT=Path(__file__).resolve().parents[1]

class FaultProvider:
    """Explicit failure fixtures; not described as live provider executions."""
    def __init__(self,kind):self.kind=kind
    def plan(self,state):
        if self.kind=="fault_timeout":raise TimeoutError("simulated timeout")
        if self.kind=="fault_loop":return Decision(action="search_sources",query="spring water")
        return Decision(action="compose")
    def compose(self,state):
        if self.kind=="fault_timeout":raise TimeoutError("simulated timeout")
        ids=["unknown-fact"] if self.kind=="fault_reference" else ["hatti-village","hatti-village"] if self.kind=="fault_duplicate" else []
        return Composition(title="Fictional test memory",reflection_prompt="What should be remembered?",fact_ids=ids)

def case_input(case,live=False):
    return {"memory":case["memory"],"place_hint":case["place_hint"],"theme":case.get("theme","Water & landscape"),"attribution":"Fictional evaluation fixture","consent":case["kind"]!="no_consent","shareable":case["kind"]!="unshareable","visibility":"private" if case["kind"]=="private" else "collection","ai_allowed":live}

def execute_case(engine,case,live=False):
    body=case_input(case,live);r=engine.start(body);initial=r
    gate=int(not any(s["id"]==r["id"] for s in engine.store.stories()))
    clarify=int((r["status"]=="waiting_place")== (case["kind"]=="ambiguous"))
    if r["status"]=="waiting_place":r=engine.resume(r["id"],{"place_id":case["choice"]},"clarify_place")
    if r["status"]=="waiting_review":r=engine.resume(r["id"],{"action":"reject" if case["kind"]=="reject" else "approve"},"review")
    expected="blocked" if case["kind"] in ["no_consent","unshareable"] else "saved_private" if case["kind"]=="private" else "rejected" if case["kind"]=="reject" else "published"
    preserved=int(not r["draft"] or r["draft"]["memory"]==case["memory"])
    placed=int(not r["draft"] or r["draft"]["place_id"]==(case.get("choice") or resolve(case["place_hint"])["id"]))
    source_valid=int(not r["draft"] or set(r["draft"]["fact_ids"]).issubset({f["id"] for f in engine.graph.get_state(engine.config(r["id"])).values.get("evidence",[])}) and len(set(r["draft"]["fact_ids"]))==len(r["draft"]["fact_ids"]))
    private=int(not r["draft"] or r["draft"]["visibility"]==body["visibility"])
    bounded=int(sum(e["stage"]=="search_sources" for e in r["events"])<=2)
    consent=int(case["kind"]!="no_consent" or [e["stage"] for e in r["events"]]==["consent"])
    scores={"task_correctness":int(r["status"]==expected and placed),"review_gate":gate,"memory_preservation":preserved,"source_reference_validity":source_valid,"clarification_behavior":clarify,"visibility_preservation":private,"bounded_searches":bounded,"consent_enforcement":consent}
    return {"case_id":case["id"],"kind":case["kind"],"run_id":r["id"],"status":r["status"],"expected_status":expected,"scores":scores,"mode":r["ledger"]["mode"],"model_calls":r["ledger"]["calls"],"tokens":r["ledger"]["input_tokens"]+r["ledger"]["output_tokens"],"stages":[e["stage"] for e in r["events"]],"trace_url":r["ledger"]["trace_url"]}

def evaluate(live=False,limit=None,upload=False):
    cases=json.loads((ROOT/"evals/cases.json").read_text())
    if live:cases=[c for c in cases if c["kind"]=="ordinary"][:limit or 8]
    elif limit:cases=cases[:limit]
    base=Settings();rows=[];recorded=[]
    with tempfile.TemporaryDirectory() as tmp:
        settings=Settings(data_dir=Path(tmp),live=live,llm_key=base.llm_key if live else "",braintrust_key=base.braintrust_key if live else "")
        if live and not settings.llm_key:raise RuntimeError("Live evaluation needs a configured provider key")
        engine=Engine(settings)
        original=engine.provider
        for c in cases:
            if c["kind"].startswith("fault_"):
                engine.s.live=True;engine.s.llm_key="fixture-only";engine.provider=FaultProvider(c["kind"])
                row=execute_case(engine,c,True);row["mode"]="simulated-fault"
            else:
                engine.s.live=live;engine.s.llm_key=base.llm_key if live else "";engine.provider=original
                row=execute_case(engine,c,live)
            rows.append(row)
            if live:recorded.append(engine.get(row["run_id"]))
        engine.close()
    scores={k:sum(r["scores"][k] for r in rows)/len(rows) for k in rows[0]["scores"]}
    retrieval=json.loads((ROOT/"evals/retrieval.json").read_text());hits=[];reciprocal=[]
    for case in retrieval:
        ids=[f["id"] for f in search(case["query"])];hits.append(sum(i in ids for i in case["expected"])/len(case["expected"]))
        reciprocal.append(max([1/(ids.index(i)+1) for i in case["expected"] if i in ids] or [0]))
    scores["retrieval_recall_at_3"]=sum(hits)/len(hits);scores["retrieval_mrr_at_3"]=sum(reciprocal)/len(reciprocal)
    if live:scores["live_execution_rate"]=sum(r["mode"]=="live" and r["model_calls"]>0 for r in rows)/len(rows)
    report={"created_at":datetime.now(timezone.utc).isoformat(),"mode":"live-provider" if live else "authored-workflow + explicit simulated failures","cases":len(rows),"retrieval_cases":len(retrieval),"scores":scores,"corpus_version":CORPUS_HASH,"scope":"Curated engineering fixtures. Source-reference validity is structural, not a claim of cultural or linguistic accuracy. Retrieval cases are authored against this small corpus; no held-out community benchmark.","results":rows}
    filename="live.json" if live else "latest.json"
    (ROOT/"evals/reports"/filename).write_text(json.dumps(report,indent=2))
    if live:(ROOT/"evals/reports/live-traces.json").write_text(json.dumps(recorded,indent=2))
    if upload:
        if not base.braintrust_key:raise RuntimeError("Braintrust upload needs a key")
        import braintrust
        experiment=braintrust.init_experiment(project=base.braintrust_project,experiment=datetime.now(timezone.utc).strftime("workflow-%Y%m%d-%H%M%S")+("-live" if live else "-authored"),api_key=base.braintrust_key)
        for row in rows:
            with experiment.start_span(name=row["case_id"]) as span:
                span.log(input={"case_id":row["case_id"],"fixture_kind":row["kind"]},output={"status":row["status"],"mode":row["mode"],"stages":row["stages"]},expected={"status":row["expected_status"]},scores=row["scores"],metadata={"execution":"recorded LangGraph run","corpus_version":CORPUS_HASH})
        experiment.flush();report["braintrust_experiment_url"]=experiment.summarize().experiment_url
        (ROOT/"evals/reports"/filename).write_text(json.dumps(report,indent=2))
    return report
