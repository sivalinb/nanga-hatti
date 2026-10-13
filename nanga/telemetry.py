import contextvars
import time
from contextlib import contextmanager
from prometheus_client import CollectorRegistry,Counter,Histogram,Gauge,generate_latest

ACTIVE=contextvars.ContextVar("nanga_active",default=None)

class Telemetry:
    def __init__(self,settings,store):
        self.settings,self.store=settings,store
        self.registry=CollectorRegistry()
        self.tasks=Counter("nanga_workflow_sessions_total","Workflow invocations including resumes",["status","mode"],registry=self.registry)
        self.stages=Histogram("nanga_stage_duration_seconds","Instrumented stage durations",["stage"],registry=self.registry,buckets=(.001,.005,.01,.025,.1,.5,1,3,10,30,60))
        self.latency=Histogram("nanga_request_duration_seconds","HTTP request durations",["route"],registry=self.registry,buckets=(.005,.01,.025,.1,.5,1,3,10,30,60,120))
        self.errors=Counter("nanga_stage_errors_total","Failed instrumented stages",["stage"],registry=self.registry)
        self.tokens=Counter("nanga_tokens_total","Provider-reported tokens",["direction"],registry=self.registry)
        self.calls=Counter("nanga_model_calls_total","Actual model HTTP calls",["status"],registry=self.registry)
        self.tool_calls=Counter("nanga_tool_calls_total","Tool invocations",["tool"],registry=self.registry)
        self.reviews=Counter("nanga_reviews_total","Contributor decisions",["decision"],registry=self.registry)
        self.evals=Gauge("nanga_eval_score","Last locally loaded evaluation score",["suite","metric"],registry=self.registry)
        self.bt=None; self.bt_state="disabled"
        if settings.braintrust_key:
            try:
                import braintrust
                self.bt=braintrust.init_logger(project=settings.braintrust_project,api_key=settings.braintrust_key,set_current=False)
                self.bt_state="configured"
            except Exception: self.bt_state="unavailable"
    def render(self): return generate_latest(self.registry)
    def session(self,run_id): return Recorder(self,run_id)
    @contextmanager
    def step(self,name,metadata=None):
        rec=ACTIVE.get(); started=time.perf_counter(); status="ok"; span=None
        clean=metadata or {}
        if rec and rec.root:
            try: span=rec.root.start_span(name=name,span_attributes={"type":"tool" if name in ["resolve_place","search_sources","publish"] else "function"})
            except Exception: self.bt_state="unavailable"
        try: yield
        except BaseException:
            status="error"; self.errors.labels(name).inc(); raise
        finally:
            duration=time.perf_counter()-started; self.stages.labels(name).observe(duration)
            if name in ["resolve_place","search_sources","publish"]: self.tool_calls.labels(name).inc()
            if rec: self.store.event(rec.run_id,name,status,duration,clean)
            if span:
                try:
                    span.log(input=clean,output={"status":status},metrics={"duration_seconds":duration});span.end()
                except Exception: self.bt_state="unavailable"

class Recorder:
    def __init__(self,telemetry,run_id):
        self.t,self.run_id=telemetry,run_id; self.root=None; self.trace_url=None
        self.input_tokens=self.output_tokens=self.calls=0; self.usage_complete=True
        self.mode="authored"; self.status="error"; self.elapsed=0
    @property
    def cost(self):
        if not self.calls:return 0.0
        s=self.t.settings
        if not self.usage_complete or s.input_price is None or s.output_price is None:return None
        return (self.input_tokens*s.input_price+self.output_tokens*s.output_price)/1_000_000
    def usage(self,usage):
        if "prompt_tokens" not in usage or "completion_tokens" not in usage:self.usage_complete=False
        self.input_tokens+=usage.get("prompt_tokens",0);self.output_tokens+=usage.get("completion_tokens",0)
        self.t.tokens.labels("input").inc(usage.get("prompt_tokens",0));self.t.tokens.labels("output").inc(usage.get("completion_tokens",0))
    def __enter__(self):
        self.started=time.perf_counter();self.ctx=ACTIVE.set(self)
        if self.t.bt:
            try:
                self.root=self.t.bt.start_span(name="memory_workflow",span_attributes={"type":"task"})
                self.root.log(input={"run_id":self.run_id},metadata={"content_logging":"redacted","app":"Nanga Hatti"})
                self.trace_url=self.root.permalink()
            except Exception:self.t.bt_state="unavailable"
        return self
    def __exit__(self,*args):
        self.elapsed=time.perf_counter()-self.started
        if self.root:
            try:
                self.root.log(output={"status":self.status,"mode":self.mode},metrics={"prompt_tokens":self.input_tokens,"completion_tokens":self.output_tokens,"model_calls":self.calls})
                self.root.end();self.t.bt.flush();self.t.bt_state="connected"
            except Exception:self.t.bt_state="unavailable"
        ACTIVE.reset(self.ctx);self.t.tasks.labels(self.status,self.mode).inc()
