import sqlite3
import threading
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.types import interrupt,Command
from langgraph.checkpoint.sqlite import SqliteSaver
from . import content
from .models import Contribution,Composition,Decision,Review
from .provider import Provider
from .storage import Store
from .telemetry import Telemetry,ACTIVE

class State(TypedDict,total=False):
    run_id:str
    request:dict
    place:dict
    evidence:list
    searches:int
    decision:dict
    draft:dict
    status:str
    warnings:list
    steps:int

class Engine:
    def __init__(self,settings,provider=None):
        self.s=settings;settings.data_dir.mkdir(parents=True,exist_ok=True)
        self.store=Store(settings.data_dir/"collection.sqlite")
        self.t=Telemetry(settings,self.store);self.provider=provider or Provider(settings,self.t)
        self.connection=sqlite3.connect(str(settings.data_dir/"checkpoints.sqlite"),check_same_thread=False)
        self.saver=SqliteSaver(self.connection);self.lock=threading.RLock()
        g=StateGraph(State)
        for name,fn in [("consent",self.consent),("resolve_place",self.resolve),("clarify_place",self.clarify),("plan",self.plan),("search_sources",self.retrieve),("compose",self.compose),("validate",self.validate),("review",self.review),("publish",self.publish)]:g.add_node(name,fn)
        g.add_edge(START,"consent")
        g.add_conditional_edges("consent",lambda s:END if s["status"]=="blocked" else "resolve_place")
        g.add_conditional_edges("resolve_place",lambda s:"plan" if s.get("place") else "clarify_place")
        g.add_edge("clarify_place","plan")
        g.add_conditional_edges("plan",lambda s:s["decision"]["action"] if s["decision"]["action"]=="compose" else "search_sources")
        g.add_edge("search_sources","plan");g.add_edge("compose","validate")
        g.add_edge("validate","review")
        g.add_conditional_edges("review",lambda s:"publish" if s["status"]=="approved" else END)
        g.add_edge("publish",END);self.graph=g.compile(checkpointer=self.saver)
    def live_allowed(self,state):return self.s.live and bool(self.s.llm_key) and state["request"]["ai_allowed"]
    def consent(self,state):
        with self.t.step("consent",{"consent":state["request"]["consent"]}):
            return {"status":"working" if state["request"]["consent"] else "blocked","warnings":[]}
    def resolve(self,state):
        with self.t.step("resolve_place",{"gazetteer_version":"town-centres-v1"}):
            return {"place":content.resolve(state["request"]["place_hint"])}
    def clarify(self,state):
        answer=interrupt({"kind":"place","message":"Which town should this memory be associated with? These are approximate town centres, not a village or household location.","choices":content.PLACES})
        chosen=next((p for p in content.PLACES if p["id"]==answer.get("place_id")),None)
        if not chosen:raise ValueError("Choose a listed town")
        with self.t.step("clarify_place",{"place_id":chosen["id"]}):return {"place":chosen}
    def fallback_plan(self,state):
        queries={"Water & landscape":"spring water wetland landscape","Food & everyday life":"food millets coffee farming producers","Language & belonging":"Badaga village language voice community archives","Work & making":"craft makers art embroidery work","Places & change":"heritage walk landscape change restoration"}
        if not state.get("searches"):return Decision(action="search_sources",query=queries[state["request"]["theme"]])
        return Decision(action="compose")
    def plan(self,state):
        with self.t.step("plan",{"searches":state.get("searches",0)}):
            decision=self.fallback_plan(state)
            warnings=list(state.get("warnings",[]))
            if self.live_allowed(state) and state.get("searches",0)<self.s.max_searches:
                try:decision=self.provider.plan(state)
                except Exception:warnings.append("AI planning unavailable or invalid; the authored workflow continued.")
            if state.get("searches",0)>=self.s.max_searches:decision=Decision(action="compose")
            if decision.action=="search_sources" and not decision.query.strip():decision=self.fallback_plan(state)
            return {"decision":decision.model_dump(),"warnings":warnings,"steps":state.get("steps",0)+1}
    def retrieve(self,state):
        with self.t.step("search_sources",{"corpus_version":content.CORPUS_HASH,"search_number":state.get("searches",0)+1}):
            found=content.search(state["decision"]["query"])
            old={v["id"]:v for v in state.get("evidence",[])};old.update({v["id"]:v for v in found})
            return {"evidence":list(old.values()),"searches":state.get("searches",0)+1}
    def fallback_composition(self,state):
        title={"Water & landscape":"A memory beside the water","Food & everyday life":"What the kitchen remembers","Language & belonging":"A familiar name for home","Work & making":"The story behind the work","Places & change":"A place through time"}[state["request"]["theme"]]
        return Composition(title=title,reflection_prompt="What detail would you like someone younger to remember?",fact_ids=[d["id"] for d in state.get("evidence",[])[:3]])
    def compose(self,state):
        with self.t.step("compose",{"memory_rewritten":False}):
            result=self.fallback_composition(state);warnings=list(state.get("warnings",[]))
            if self.live_allowed(state):
                try:result=self.provider.compose(state)
                except Exception:warnings.append("AI composition unavailable or invalid; an authored title and question were used.")
            req=state["request"]
            draft={"id":state["run_id"],**result.model_dump(),"memory":req["memory"],"place_id":state["place"]["id"],"theme":req["theme"],"attribution":req["attribution"],"year":req["year"],"kind":"Contributor memory · unverified personal account","visibility":req["visibility"]}
            return {"draft":draft,"warnings":warnings}
    def validate(self,state):
        with self.t.step("validate",{"corpus_version":content.CORPUS_HASH}):
            draft=dict(state["draft"]);allowed={d["id"] for d in state.get("evidence",[])};ids=draft["fact_ids"]
            warnings=list(state.get("warnings",[]))
            if len(set(ids))!=len(ids) or any(fid not in allowed for fid in ids):
                draft.update(self.fallback_composition(state).model_dump());warnings.append("Unsupported or duplicate source references were rejected.")
                rec=ACTIVE.get()
                if rec and rec.calls:rec.mode="mixed"
            draft["context"]=[content.FACTS[fid] for fid in draft["fact_ids"]]
            draft["memory"]=state["request"]["memory"]
            return {"draft":draft,"status":"waiting_review","warnings":warnings}
    def review(self,state):
        decision=Review.model_validate(interrupt({"kind":"review","draft":state["draft"],"warnings":state.get("warnings",[]),"message":"Check the original memory, separate source context, attribution and visibility before saving."}))
        with self.t.step("review",{"action":decision.action}):
            self.t.reviews.labels(decision.action).inc()
            draft=dict(state["draft"])
            if decision.title:draft["title"]=decision.title
            if decision.fact_ids is not None:
                if len(set(decision.fact_ids))!=len(decision.fact_ids) or not set(decision.fact_ids).issubset(draft["fact_ids"]):
                    raise ValueError("Review may keep or remove retrieved context, not add unsupported references")
                draft["fact_ids"]=decision.fact_ids
                draft["context"]=[content.FACTS[fid] for fid in decision.fact_ids]
            return {"draft":draft,"status":"approved" if decision.action=="approve" else "rejected"}
    def publish(self,state):
        with self.t.step("publish",{"visibility":state["request"]["visibility"]}):
            req=state["request"]
            if not req["consent"]:raise ValueError("Consent is required")
            if req["visibility"]=="collection" and not req["shareable"]:
                return {"status":"blocked","warnings":state.get("warnings",[])+["Collection sharing permission is required. Save a private memory instead."]}
            self.store.publish(state["run_id"],{**state["draft"],"reviewed":True})
            return {"status":"published" if req["visibility"]=="collection" else "saved_private"}
    def config(self,run_id):return {"configurable":{"thread_id":run_id},"recursion_limit":20}
    def start(self,request):
        req=Contribution.model_validate(request)
        run_id=uuid.uuid4().hex
        with self.lock:
            self.store.begin(run_id)
            return self.invoke(run_id,{"run_id":run_id,"request":req.model_dump(),"searches":0,"steps":0})
    def invoke(self,run_id,value):
        with self.t.session(run_id) as rec:
            try:
                result=self.graph.invoke(value,self.config(run_id))
                snap=self.graph.get_state(self.config(run_id))
                rec.status="waiting_place" if snap.next==("clarify_place",) else "waiting_review" if snap.next else result.get("status","error")
            except Exception:
                rec.status="error";raise
        self.store.finish(run_id,rec.status,rec)
        return self.get(run_id)
    def get(self,run_id):
        if not run_id or len(run_id)!=32:raise KeyError("Run not found")
        snap=self.graph.get_state(self.config(run_id))
        if not snap.values:raise KeyError("Run not found")
        value=snap.values
        pending=[i.value for task in snap.tasks for i in task.interrupts]
        status="waiting_place" if snap.next==("clarify_place",) else "waiting_review" if snap.next else value.get("status","error")
        return {"id":run_id,"status":status,"pending":pending[0] if pending else None,"draft":value.get("draft"),"warnings":value.get("warnings",[]),"events":self.store.events(run_id),"ledger":next((r for r in self.store.runs(10000) if r["id"]==run_id),None)}
    def resume(self,run_id,answer,expected):
        with self.lock:
            snap=self.graph.get_state(self.config(run_id))
            if not snap.values:raise KeyError("Run not found")
            if not snap.next:return self.get(run_id)
            if snap.next!=(expected,):raise ValueError("This workflow is waiting for a different response")
            return self.invoke(run_id,Command(resume=answer))
    def close(self):self.connection.close();self.store.close()
