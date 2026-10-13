"""Original source-attributed summaries; fictional memories are labeled explicitly."""
import hashlib
import json
import math
import re
from collections import Counter

PLACES = [
    {"id": "kotagiri", "name": "Kotagiri", "aliases": ["kotagiri", "kothagiri", "கோத்தகிரி"], "lat": 11.4227, "lon": 76.8607},
    {"id": "coonoor", "name": "Coonoor", "aliases": ["coonoor", "kunnoor", "குன்னூர்"], "lat": 11.3530, "lon": 76.7959},
    {"id": "ooty", "name": "Udhagamandalam", "aliases": ["ooty", "udhagamandalam", "ootacamund", "உதகமண்டலம்"], "lat": 11.4102, "lon": 76.6950},
]
SOURCES = [
    {"id":"hatti", "title":"The word Hatti", "url":"https://badaga.co/2021/06/08/the-beauty-of-ha-sound-in-badaga/", "publisher":"Bellie Jayaprakash", "topics":["language","village","names"], "facts":[("hatti-village","Hatti is a Badaga word for village."), ("hatti-sound","The cited community author emphasizes retaining the initial h sound in Hatti.")]},
    {"id":"mosaic", "title":"A landscape of forests, grasslands and wetlands", "url":"https://nnhs.in/mainstreaming-community-led-ecological-restoration/", "publisher":"Nilgiri Natural History Society", "topics":["landscape","water","grassland","shola","restoration"], "facts":[("mosaic-landscape","The Nilgiris landscape includes shola groves, montane grasslands, wetlands and marshes."), ("mosaic-history","Restoration choices should consider the past vegetation of a particular site."), ("mosaic-water","Local restoration discussions connect native vegetation and soils with the water cycle.")]},
    {"id":"water", "title":"Nilgiris Water Portal", "url":"https://nilgiriswaterportal.in/downloads/", "publisher":"Keystone Foundation", "topics":["water","spring","wetland","memory","badaga"], "facts":[("water-reports","The Water Portal provides reports and case studies on Nilgiris water resources."), ("water-stories","Its resource collection includes a Badaga Water Stories calendar from 2017.")]},
    {"id":"radio", "title":"Radio Kotagiri", "url":"https://radiokotagiri.keystone-foundation.org/", "publisher":"Radio Kotagiri", "topics":["voice","music","story","community","language"], "facts":[("radio-voices","Radio Kotagiri carries local-language stories, songs and community experiences."), ("radio-learning","The station has collaborated with schools and colleges on community media.")]},
    {"id":"archives", "title":"Community archives and access", "url":"https://keystone-foundation.org/workshop-on-community-archives/", "publisher":"Keystone Foundation", "topics":["memory","archive","consent","community","history"], "facts":[("archives-control","Keystone describes community archives with access guided by community membership and cultural norms."), ("archives-glossary","A reported archives workshop included work on language glossaries.")]},
    {"id":"food", "title":"Aadhimalai community producers", "url":"https://aadhimalai.in/", "publisher":"Aadhimalai", "topics":["food","millet","coffee","honey","work","farming"], "facts":[("food-enterprise","Aadhimalai describes itself as an enterprise owned by Indigenous producers of the Nilgiri Biosphere Reserve."), ("food-produce","Its producers cultivate crops including coffee, pepper, millets and pulses.")]},
    {"id":"embroidery", "title":"Toda Embroidery registration", "url":"https://search.ipindia.gov.in/GIRPublicSearch/Application/Details/135", "publisher":"Intellectual Property India", "topics":["craft","embroidery","toda","maker"], "facts":[("embroidery-gi","Toda Embroidery is recorded as a registered geographical indication in the official registry.")]},
    {"id":"art", "title":"Kurumba artists and storytelling", "url":"https://lastforest.in/products/kurumba-tribal-art", "publisher":"Last Forest", "topics":["craft","painting","kurumba","maker"], "facts":[("art-makers","Last Forest describes paintings made by Kurumba artists that depict community life and relationships with nature.")]},
    {"id":"school", "title":"Nilgiris Uyirsholai", "url":"https://keystone-foundation.org/launch-climate-education-implementation/", "publisher":"Keystone Foundation", "topics":["school","climate","learning","children"], "facts":[("school-launch","Keystone reports that the Nilgiris Uyirsholai climate curriculum and portal launched in August 2026."), ("school-place","The curriculum uses local ecology, observations and activities for climate learning.")]},
    {"id":"walk", "title":"Kotagiri heritage walks", "url":"https://nnhs.in/of-name-and-fame-heritage-walk-kotagiri/", "publisher":"Nilgiri Natural History Society", "topics":["walk","history","names","kotagiri"], "facts":[("walk-stories","NNHS has organized a Kotagiri heritage walk exploring stories behind local places.")]},
    {"id":"longwood", "title":"Longwood Shola interpretation centre", "url":"https://nnhs.in/nature-interpretation-center-at-longwood-shola-kotagiri/", "publisher":"Nilgiri Natural History Society", "topics":["shola","forest","learning","kotagiri"], "facts":[("longwood-learning","The Longwood Shola interpretation centre presents information on local ecosystems, species and water sources.")]},
    {"id":"invasives", "title":"Citizen observations of invasive plants", "url":"https://nnhs.in/invasive-plant-mapping/", "publisher":"Nilgiri Natural History Society", "topics":["invasive","plant","restoration","citizen","observation"], "facts":[("invasives-citizens","NNHS reports invasive-plant mapping involving citizens, students, scientists and forest staff.")]},
]
FACTS = {fid: {"id":fid,"text":txt,"source_id":s["id"],"source_title":s["title"],"url":s["url"],"publisher":s["publisher"]} for s in SOURCES for fid,txt in s["facts"]}
CORPUS_HASH = hashlib.sha256(json.dumps(SOURCES,sort_keys=True).encode()).hexdigest()[:16]
SEEDS = [
    {"id":"seed-spring","title":"The path beside the spring","place_id":"kotagiri","theme":"Water & landscape","memory":"I remember taking the longer path home so I could pause beside the stream. The hills felt different after rain.","fact_ids":["mosaic-landscape","water-stories"],"kind":"Fictional demonstration","attribution":"Authored example; no real contributor","year":"An imagined childhood"},
    {"id":"seed-kitchen","title":"A kitchen that carries a season","place_id":"coonoor","theme":"Food & everyday life","memory":"The sound of preparing supper is what I remember first. I would like to ask my family which ingredients they grew and which they bought.","fact_ids":["food-produce"],"kind":"Fictional demonstration","attribution":"Authored example; no real contributor","year":"A family conversation prompt"},
    {"id":"seed-name","title":"Say the place name slowly","place_id":"ooty","theme":"Language & belonging","memory":"When I hear the name of home spoken by someone familiar, it sounds like more than a place on a map.","fact_ids":["hatti-village","archives-control"],"kind":"Fictional demonstration","attribution":"Authored example; no real contributor","year":"A memory-making prompt"},
    {"id":"seed-makers","title":"Hands, patience and a story","place_id":"kotagiri","theme":"Work & making","memory":"I want to record the ordinary steps behind something handmade, in the maker's own words and with their agreement.","fact_ids":["art-makers","embroidery-gi"],"kind":"Fictional demonstration","attribution":"Authored example; no real contributor","year":"A contribution idea"},
]
def tokens(text):
    return re.findall(r"[\w]+",text.casefold(),re.UNICODE)

def search(query, limit=3):
    """BM25 on the small reviewed fact collection. Scores are retrieval relevance."""
    docs=list(FACTS.values()); bags=[Counter(tokens(d["text"]+" "+" ".join(next(s["topics"] for s in SOURCES if s["id"]==d["source_id"])))) for d in docs]
    terms=tokens(query); avg=sum(sum(b.values()) for b in bags)/len(bags)
    ranked=[]
    for d,b in zip(docs,bags):
        score=0.0
        for term in set(terms):
            df=sum(term in other for other in bags); freq=b[term]
            if freq:
                idf=math.log(1+(len(bags)-df+0.5)/(df+0.5)); score+=idf*freq*2.5/(freq+1.5*(0.25+0.75*sum(b.values())/avg))
        if score>0: ranked.append({**d,"score":round(score,6)})
    return sorted(ranked,key=lambda x:(-x["score"],x["id"]))[:limit]

def resolve(hint):
    hint=hint.strip().casefold()
    exact=[p for p in PLACES if hint in p["aliases"] or hint==p["id"]]
    if len(exact)==1: return exact[0]
    embedded=[p for p in PLACES if any(re.search(r"(?<!\w)"+re.escape(a)+r"(?!\w)",hint) for a in p["aliases"])]
    return embedded[0] if len(embedded)==1 else None
