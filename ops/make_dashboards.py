"""Regenerate versioned Grafana dashboards from application metric names."""
import json
from pathlib import Path

def panel(i,title,expr,kind="timeseries",unit="short",legend="",x=0,y=0,w=12,h=7):
    return {"id":i,"title":title,"type":kind,"datasource":{"type":"prometheus","uid":"nanga-prometheus"},"gridPos":{"x":x,"y":y,"w":w,"h":h},"targets":[{"refId":"A","expr":expr,"legendFormat":legend}],"fieldConfig":{"defaults":{"unit":unit},"overrides":[]},"options":{"reduceOptions":{"calcs":["lastNotNull"],"fields":"","values":False},"legend":{"displayMode":"list","placement":"bottom"},"tooltip":{"mode":"multi"}}}

def dashboard(uid,title,panels):
    return {"uid":uid,"title":title,"schemaVersion":41,"version":1,"tags":["nanga-hatti","LangGraph","Braintrust"],"timezone":"browser","refresh":"5s","time":{"from":"now-15m","to":"now"},"panels":panels,"annotations":{"list":[]},"templating":{"list":[]}}

p=[panel(1,"Workflow sessions","sum(nanga_workflow_sessions_total)","stat",w=6,h=4),panel(2,"Actual model calls","sum(nanga_model_calls_total)","stat",x=6,w=6,h=4),panel(3,"Provider-reported tokens","sum(nanga_tokens_total)","stat",x=12,w=6,h=4),panel(4,"Metrics target","up{job=\"nanga-hatti\"}","stat",x=18,w=6,h=4),panel(5,"Stage latency · p95 estimate","histogram_quantile(0.95, sum by (le,stage) (rate(nanga_stage_duration_seconds_bucket[5m])))",unit="s",legend="{{stage}}",y=4),panel(6,"HTTP latency · p95 estimate","histogram_quantile(0.95, sum by (le,route) (rate(nanga_request_duration_seconds_bucket[5m])))",unit="s",legend="{{route}}",x=12,y=4),panel(7,"Model calls by result","sum by (status) (nanga_model_calls_total)",legend="{{status}}",y=11),panel(8,"Workflow modes","sum by (mode) (nanga_workflow_sessions_total)",legend="{{mode}}",x=12,y=11),panel(9,"Tool invocations","sum by (tool) (nanga_tool_calls_total)",legend="{{tool}}",y=18),panel(10,"Token accounting","sum by (direction) (nanga_tokens_total)",legend="{{direction}}",x=12,y=18)]
q=[panel(1,"Consent enforcement · curated suite","nanga_eval_score{metric=\"consent_enforcement\"}","stat","percentunit",w=8,h=4),panel(2,"Review gate · curated suite","nanga_eval_score{metric=\"review_gate\"}","stat","percentunit",x=8,w=8,h=4),panel(3,"Source reference validity · structural","nanga_eval_score{metric=\"source_reference_validity\"}","stat","percentunit",x=16,w=8,h=4),panel(4,"Last-loaded evaluation scores","nanga_eval_score",unit="percentunit",legend="{{metric}}",y=4,w=24),panel(5,"Contributor decisions","sum by (decision) (nanga_reviews_total)",legend="{{decision}}",y=11),panel(6,"Workflow outcomes","sum by (status) (nanga_workflow_sessions_total)",legend="{{status}}",x=12,y=11)]
root=Path(__file__).parent/"grafana/dashboards"
for uid,title,panels in [("nanga-workflow","Nanga Hatti · Workflow & performance",p),("nanga-quality","Nanga Hatti · Quality & contributor review",q)]:
    (root/(uid+".json")).write_text(json.dumps(dashboard(uid,title,panels),indent=2))
print("Generated 2 dashboards with 16 panels")
