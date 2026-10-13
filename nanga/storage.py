import json
import sqlite3
import threading
import time

class Store:
    def __init__(self,path):
        self.lock=threading.RLock()
        self.db=sqlite3.connect(str(path),check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created REAL, status TEXT, mode TEXT, duration REAL, input_tokens INTEGER, output_tokens INTEGER, calls INTEGER, cost REAL, trace_url TEXT);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id TEXT, stage TEXT, status TEXT, duration REAL, metadata TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS stories (id TEXT PRIMARY KEY, content TEXT, created REAL);
        """)
    def begin(self,run_id):
        with self.lock,self.db:
            self.db.execute("INSERT INTO runs VALUES (?,?, 'starting','authored',0,0,0,0,NULL,NULL)",(run_id,time.time()))
    def finish(self,run_id,status,rec):
        with self.lock,self.db:
            old=self.db.execute("SELECT mode,calls,cost FROM runs WHERE id=?",(run_id,)).fetchone()
            mode=rec.mode
            if old and old[1] and mode=="authored": mode=old[0]
            elif old and old[1] and old[0]!=mode: mode="mixed"
            cost=rec.cost
            if old and old[1] and (old[2] is None or cost is None): cost=None
            elif old and old[2] is not None and cost is not None: cost+=old[2]
            self.db.execute("UPDATE runs SET status=?,mode=?,duration=duration+?,input_tokens=input_tokens+?,output_tokens=output_tokens+?,calls=calls+?,cost=?,trace_url=COALESCE(?,trace_url) WHERE id=?",(status,mode,rec.elapsed,rec.input_tokens,rec.output_tokens,rec.calls,cost,rec.trace_url,run_id))
    def event(self,run_id,stage,status,duration,metadata):
        with self.lock,self.db:
            self.db.execute("INSERT INTO events(run_id,stage,status,duration,metadata,created) VALUES (?,?,?,?,?,?)",(run_id,stage,status,duration,json.dumps(metadata),time.time()))
    def events(self,run_id):
        with self.lock:
            rows=self.db.execute("SELECT stage,status,duration,metadata FROM events WHERE run_id=? ORDER BY id",(run_id,)).fetchall()
        return [{"stage":s,"status":t,"duration_ms":round(d*1000,2),"metadata":json.loads(m)} for s,t,d,m in rows]
    def publish(self,run_id,story):
        with self.lock,self.db:
            self.db.execute("INSERT OR IGNORE INTO stories VALUES (?,?,?)",(run_id,json.dumps(story),time.time()))
    def stories(self):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute("SELECT content FROM stories ORDER BY created DESC")]
    def runs(self,limit=25):
        with self.lock:
            rows=self.db.execute("SELECT * FROM runs ORDER BY created DESC LIMIT ?",(limit,)).fetchall()
        fields=["id","created","status","mode","duration","input_tokens","output_tokens","calls","cost_usd","trace_url"]
        return [dict(zip(fields,r)) for r in rows]
    def close(self): self.db.close()
