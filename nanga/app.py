import hmac
import ipaddress
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Request,Depends
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from .config import Settings
from .engine import Engine
from .models import Contribution,Review,PlaceChoice
from . import content

ROOT=Path(__file__).resolve().parents[1]

def create_app(settings=None):
    settings=settings or Settings();engine=Engine(settings)
    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.close()
    app=FastAPI(title="Nanga Hatti",lifespan=lifespan)
    app.state.engine=engine
    def access(request:Request):
        if settings.server_token:
            token=request.headers.get("authorization","").removeprefix("Bearer ")
            if not hmac.compare_digest(token,settings.server_token):raise HTTPException(401,"Workspace token required")
        elif request.client and request.client.host!="testclient":
            address=ipaddress.ip_address(request.client.host)
            if not (address.is_loopback or settings.trusted_network and address in ipaddress.ip_network(settings.trusted_network)):
                raise HTTPException(403,"This is a local workspace")
        origin=request.headers.get("origin")
        if request.method!="GET" and origin and origin.rstrip("/")!=str(request.base_url).rstrip("/"):
            raise HTTPException(403,"Use the workspace page for changes")
    @app.middleware("http")
    async def measure(request,call_next):
        start=time.perf_counter()
        result=await call_next(request)
        route="stories" if request.url.path=="/api/stories" else "workflow" if request.url.path.startswith("/api/runs") else "read"
        engine.t.latency.labels(route).observe(time.perf_counter()-start)
        result.headers["X-Content-Type-Options"]="nosniff"
        result.headers["Referrer-Policy"]="same-origin"
        if request.url.path.startswith("/api/"):result.headers["Cache-Control"]="no-store"
        return result
    app.mount("/static",StaticFiles(directory=ROOT/"static"),name="static")
    @app.get("/")
    def home():return FileResponse(ROOT/"static/index.html")
    @app.get("/lab")
    def lab():return FileResponse(ROOT/"static/lab.html")
    @app.get("/health")
    def health():return {"status":"ok","app":"Nanga Hatti"}
    @app.get("/api/catalog",dependencies=[Depends(access)])
    def catalog():return {"places":content.PLACES,"sources":content.SOURCES,"facts":content.FACTS,"seeds":content.SEEDS,"corpus_version":content.CORPUS_HASH,"workspace":"local"}
    @app.get("/api/stories",dependencies=[Depends(access)])
    def stories():return engine.store.stories()
    @app.post("/api/runs",dependencies=[Depends(access)])
    def start(body:Contribution):return engine.start(body.model_dump())
    @app.get("/api/runs/{run_id}",dependencies=[Depends(access)])
    def run(run_id:str):
        try:return engine.get(run_id)
        except KeyError:raise HTTPException(404,"Run not found")
    @app.post("/api/runs/{run_id}/place",dependencies=[Depends(access)])
    def place(run_id:str,body:PlaceChoice):
        if body.place_id not in {p["id"] for p in content.PLACES}:raise HTTPException(422,"Choose a listed town")
        try:return engine.resume(run_id,body.model_dump(),"clarify_place")
        except KeyError:raise HTTPException(404,"Run not found")
        except ValueError as e:raise HTTPException(409,str(e))
    @app.post("/api/runs/{run_id}/review",dependencies=[Depends(access)])
    def review(run_id:str,body:Review):
        try:return engine.resume(run_id,body.model_dump(),"review")
        except KeyError:raise HTTPException(404,"Run not found")
        except ValueError as e:raise HTTPException(409,str(e))
    @app.get("/api/evidence",dependencies=[Depends(access)])
    def evidence():
        reports={}
        for name,path in [("evals",ROOT/"evals/reports/latest.json"),("benchmarks",ROOT/"benchmarks/reports/latest.json")]:
            reports[name]=json.loads(path.read_text()) if path.exists() else None
        if reports["evals"]:
            for k,v in reports["evals"].get("scores",{}).items():engine.t.evals.labels("authored",k).set(v)
        live_report=ROOT/"evals/reports/live.json"
        return {"runs":engine.store.runs(),"braintrust":engine.t.bt_state,"live_configured":settings.live and bool(settings.llm_key),"corpus_version":content.CORPUS_HASH,"reports":reports,"live_evals":json.loads(live_report.read_text()) if live_report.exists() else None}
    @app.get("/metrics",dependencies=[Depends(access)])
    def metrics():return Response(engine.t.render(),media_type="text/plain; version=0.0.4")
    return app
