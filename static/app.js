(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let catalog, stories = [], currentPlace = 'all', currentTheme = 'All', local = false, run = null, map, markers = [], media = {}, recorder, chunks = [], mediaTimer;
  async function api(path, body) {
    const headers = body ? {'Content-Type':'application/json'} : {};
    const token = (sessionStorage.getItem('nanga-token') || sessionStorage.getItem('namma-token')); if (token) headers.Authorization = 'Bearer ' + token;
    const res = await fetch(path, {method:body ? 'POST':'GET', headers, ...(body ? {body:JSON.stringify(body)} : {})});
    if (!res.ok) {
      if (res.status === 401) throw new Error('This workspace requires a server token. Follow the workspace token instructions in the local operations guide.');
      let data; try { data = await res.json(); } catch { data = {}; }
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the form and try again.');
    }
    return res.json();
  }
  function mediaDB() {
    return new Promise((resolve,reject) => { const r = indexedDB.open('namma-media-v1',1); r.onupgradeneeded=()=>r.result.createObjectStore('attachments'); r.onsuccess=()=>resolve(r.result); r.onerror=()=>reject(r.error); });
  }
  async function mediaStore(id,value) {
    const db=await mediaDB(); await new Promise((resolve,reject)=>{const tx=db.transaction('attachments','readwrite');tx.objectStore('attachments').put(value,id);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});db.close();
  }
  async function mediaRead(id) {
    const db=await mediaDB();const value=await new Promise((resolve,reject)=>{const r=db.transaction('attachments').objectStore('attachments').get(id);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});db.close();return value;
  }
  function view(name) {
    for (const v of ['explore','contribute','collection']) $('#' + v + '-view').classList.toggle('hidden',v!==name);
    document.querySelectorAll('.nav[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
    if(name==='collection') renderCollection();
    if(name==='explore' && map) setTimeout(()=>map.invalidateSize(),0);
    if(name==='contribute') $('#contribute-view').scrollIntoView({behavior:'smooth',block:'start'});
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>view(b.dataset.view)));
  const placeName = id => catalog.places.find(p=>p.id===id)?.name || 'A place in the hills';
  function card(s) {
    return `<article class="story-card"><div class="card-visual"><span class="card-place">${esc(placeName(s.place_id))}</span><span class="card-theme">${esc(s.theme)}</span></div><div class="card-body"><span class="card-meta">${esc(s.kind)}${s.visibility==='private'?' · Private':''}</span><h3>${esc(s.title)}</h3><p>${esc(s.memory.slice(0,150))}${s.memory.length>150?'…':''}</p><span class="card-meta">${esc(s.year)}</span></div><button class="card-action" data-story="${esc(s.id)}">Read the memory <span aria-hidden="true">↗</span></button></article>`;
  }
  function wireCards(el){el.querySelectorAll('[data-story]').forEach(b=>b.addEventListener('click',()=>openStory(b.dataset.story)));}
  function render() {
    const term=$('#search').value.toLocaleLowerCase();
    const all=[...catalog.seeds,...stories.filter(s=>s.visibility==='collection')];
    const matches=all.filter(s=>(currentPlace==='all'||s.place_id===currentPlace)&&(currentTheme==='All'||s.theme===currentTheme)&&[s.title,s.memory,s.theme,placeName(s.place_id)].join(' ').toLocaleLowerCase().includes(term));
    $('#cards').innerHTML=matches.length?matches.map(card).join(''):'<p class="empty">No memories match yet. Try another place or clear the search.</p>';
    $('#count').textContent=matches.length+' '+(matches.length===1?'memory':'memories');wireCards($('#cards'));
    document.querySelectorAll('.place-button').forEach(b=>b.classList.toggle('active',b.dataset.place===currentPlace));
    document.querySelectorAll('.theme').forEach(b=>b.classList.toggle('active',b.dataset.theme===currentTheme));
    const p=catalog.places.find(p=>p.id===currentPlace);if(p&&map)map.setView([p.lat,p.lon],12);
  }
  function renderCollection(){ $('#my-cards').innerHTML=stories.length?stories.map(card).join(''):'<p class="empty">Your first memory can begin with a few words. Choose Add a memory to start.</p>';wireCards($('#my-cards')); }
  function contextHTML(ids,review=false){return ids.map(id=>catalog.facts[id]).filter(Boolean).map(f=>`<div class="context">${review?`<label class="check"><input type="checkbox" data-fact-id="${esc(f.id)}" checked> Keep this context</label>`:''}<p>${esc(f.text)}</p><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.publisher)} ↗</a></div>`).join('');}
  async function openStory(id){
    const s=[...catalog.seeds,...stories].find(s=>s.id===id);if(!s)return;
    $('#story-detail').innerHTML=`<p class="eyebrow">${esc(placeName(s.place_id))} · ${esc(s.theme)}</p><h2>${esc(s.title)}</h2><p class="label">${esc(s.kind)}${s.visibility==='private'?' · Private in this workspace':''}</p><p class="memory-quote">${esc(s.memory)}</p><p class="small">${esc(s.attribution)} · ${esc(s.year)}</p><div id="story-media"></div><h3>Landscape &amp; community context</h3><p class="small">These sources offer context. They do not verify the personal memory.</p><div class="review-context">${contextHTML(s.fact_ids || [])}</div>${s.reflection_prompt?`<p>${esc(s.reflection_prompt)}</p>`:''}`;
    $('#story-dialog').showModal();
    try{const m=await mediaRead(id);if(m){const container=$('#story-media');for(const [kind,blob] of Object.entries(m)){if(!(blob instanceof Blob))continue;const url=URL.createObjectURL(blob);const el=document.createElement(kind==='audio'?'audio':'img');el.src=url;if(kind==='audio')el.controls=true;else{el.alt='Contributor photograph saved in this browser';el.className='dialog-photo';}container.appendChild(el);const a=document.createElement('a');a.href=url;a.download='nanga-hatti-'+kind;a.className='report-link';a.textContent='Download '+kind+' ↓';container.appendChild(a);}}}catch{ /* Text remains usable without IndexedDB. */ }
  }
  $('#story-dialog .close').addEventListener('click',()=>$('#story-dialog').close());
  $('#story-dialog').addEventListener('click',e=>{if(e.target===$('#story-dialog'))$('#story-dialog').close();});
  $('#search').addEventListener('input',render);
  function filePick(input,kind,max){input.addEventListener('change',()=>{const f=input.files[0];if(!f)return;if(f.size>max){$('#media-status').textContent='Choose a smaller file (audio up to 4 MB; photos up to 5 MB).';input.value='';return;}if(kind==='photo'&&!['image/jpeg','image/png','image/webp'].includes(f.type)){$('#media-status').textContent='Choose a JPEG, PNG or WebP photograph.';return;}media[kind]=f;const preview=$('#'+kind+'-preview');preview.src=URL.createObjectURL(f);preview.classList.remove('hidden');$('#media-status').textContent='Saved temporarily in this browser; attached when the draft is prepared.';});}
  filePick($('#audio-file'),'audio',4*1024*1024);filePick($('#photo-file'),'photo',5*1024*1024);
  $('#record').addEventListener('click',async()=>{
    if(recorder?.state==='recording'){recorder.stop();return;}
    try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=()=>{clearTimeout(mediaTimer);stream.getTracks().forEach(t=>t.stop());media.audio=new Blob(chunks,{type:recorder.mimeType});$('#audio-preview').src=URL.createObjectURL(media.audio);$('#audio-preview').classList.remove('hidden');$('#record').textContent='Record a voice';$('#media-status').textContent='Recording stays in this browser. Add its words to your memory if you wish.';};recorder.start();$('#record').textContent='Stop recording';$('#media-status').textContent='Recording… up to 20 seconds.';mediaTimer=setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},20000);}catch{$('#media-status').textContent='Microphone unavailable. You can choose an audio file instead.';}
  });
  $('#example').addEventListener('click',()=>{ $('#memory').value='I remember walking beside a spring in Kotagiri after the rain. I want to keep the sound of that water and ask my family what has changed.';$('#place-hint').value='Kotagiri';$('#theme').value='Water & landscape';$('#attribution').value='Fictional demonstration';$('#year').value='An imagined childhood';$('#consent').checked=true;$('#shareable').checked=true;$('#studio-status').textContent='Fictional example loaded. You can edit it before preparing the draft.'; });
  $('#memory-form').addEventListener('submit',async e=>{
    e.preventDefault();if(!local)return;$('#prepare').disabled=true;$('#studio-status').textContent='Preparing your memory…';
    const f=new FormData(e.target);const body=Object.fromEntries(f);body.year ||= 'A remembered moment';body.consent=$('#consent').checked;body.shareable=$('#shareable').checked;body.ai_allowed=$('#ai-allowed').checked;
    try{run=await api('/api/runs',body);if(Object.keys(media).length)await mediaStore(run.id,media);localStorage.setItem('namma-pending',run.id);renderRun();$('#studio-status').textContent='Ready for your review.';}catch(err){$('#studio-status').textContent=err.message;$('#studio-status').classList.add('error');}finally{$('#prepare').disabled=false;}
  });
  function renderRun(){
    const box=$('#workflow');box.classList.remove('hidden');
    const timeline=`<div class="timeline">${run.events.map(e=>`<span class="step">${esc(e.stage.replaceAll('_',' '))} · ${e.duration_ms.toFixed(1)} ms</span>`).join('')}</div>`;
    if(run.status==='waiting_place'){
      box.innerHTML=`<h3>Give this memory a place.</h3><p>${esc(run.pending.message)}</p><div class="form-actions">${catalog.places.map(p=>`<button class="button" data-choice="${p.id}">${esc(p.name)}</button>`).join('')}</div>${timeline}`;
      box.querySelectorAll('[data-choice]').forEach(b=>b.addEventListener('click',async()=>{b.disabled=true;try{run=await api('/api/runs/'+run.id+'/place',{place_id:b.dataset.choice});renderRun();}catch(e){$('#studio-status').textContent=e.message;}}));
    }else if(run.status==='waiting_review'){
      const d=run.draft;box.innerHTML=`<p class="eyebrow">CHECK BEFORE KEEPING</p><label>Story title<input class="review-title" id="review-title" maxlength="100" value="${esc(d.title)}"></label><p class="memory-quote">${esc(d.memory)}</p><p class="small">${esc(d.attribution)} · ${esc(placeName(d.place_id))} · ${esc(d.visibility==='private'?'Private in your workspace':'Your local collection')}</p><h3>Separate source context</h3><p class="small">Keep the context that helps tell this story; remove anything that does not belong.</p><div class="review-context">${contextHTML(d.fact_ids,true)}</div><p>${esc(d.reflection_prompt)}</p>${run.warnings.map(w=>`<p class="notice">${esc(w)}</p>`).join('')}<div class="form-actions"><button class="button primary" data-review="approve">Approve &amp; save</button><button class="button" data-review="reject">Reject this draft</button></div>${timeline}<p class="small">${esc(run.ledger?.mode || 'authored')} workflow · ${run.ledger?.calls || 0} model calls. Voice and photos remain in this browser.</p>`;
      box.querySelectorAll('[data-review]').forEach(b=>b.addEventListener('click',async()=>{b.disabled=true;try{const fact_ids=[...box.querySelectorAll('[data-fact-id]:checked')].map(el=>el.dataset.factId);run=await api('/api/runs/'+run.id+'/review',{action:b.dataset.review,title:$('#review-title').value,fact_ids});stories=await api('/api/stories');renderRun();render();}catch(e){$('#studio-status').textContent=e.message;b.disabled=false;}}));
    }else{
      const success=['published','saved_private'].includes(run.status);box.innerHTML=`<h3>${success?'Your memory is kept.':run.status==='rejected'?'Draft rejected.':'Permission is needed.'}</h3><p>${success?'Your reviewed story is saved in this workspace.':esc(run.warnings.join(' '))}</p><button class="button" data-view="collection">View my collection ↗</button>${timeline}`;box.querySelector('[data-view]').addEventListener('click',()=>view('collection'));localStorage.removeItem('namma-pending');
    }
    box.scrollIntoView({behavior:'smooth',block:'start'});
  }
  $('#export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({app:'Nanga Hatti',version:1,exported_at:new Date().toISOString(),stories},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='nanga-hatti-stories.json';a.click();URL.revokeObjectURL(a.href);});
  async function init(){
    try{catalog=await api('/api/catalog');stories=await api('/api/stories');local=true;}catch{catalog=await (await fetch('static/catalog.json')).json();}
    $('#workspace').textContent=local?'Your local workspace':'Public explorer';
    if(!local){$('#studio-offline').classList.remove('hidden');$('#prepare').disabled=true;$('#mode-note').textContent+=' Contribution and review run in the local Python app.';}
    $('#place-buttons').innerHTML=`<button class="place-button active" data-place="all">All places</button>`+catalog.places.map(p=>`<button class="place-button" data-place="${p.id}">${esc(p.name)}</button>`).join('');
    $('#place-buttons').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{currentPlace=b.dataset.place;render();}));
    const themes=['All',...new Set(catalog.seeds.map(s=>s.theme))];$('#themes').innerHTML=themes.map(t=>`<button class="theme${t==='All'?' active':''}" data-theme="${esc(t)}">${esc(t)}</button>`).join('');$('#themes').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{currentTheme=b.dataset.theme;render();}));
    if(window.L){map=L.map('map',{scrollWheelZoom:false,minZoom:9,maxZoom:13}).setView([11.40,76.78],10);map.attributionControl.addAttribution('<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>');try{const geometry=await(await fetch('static/region.geojson')).json();L.geoJSON(geometry,{style:f=>({color:f.properties.kind==='road'?'#a5b5a6':'#729d9c',weight:f.properties.kind==='road'?1.4:1.8,fillColor:'#b6d0c9',fillOpacity:.65})}).addTo(map);}catch{$('#map').insertAdjacentHTML('afterend','<p class="small">Regional geometry unavailable; the town markers remain selectable.</p>');}for(const p of catalog.places){const m=L.circleMarker([p.lat,p.lon],{radius:7,color:'#183d36',fillColor:'#c66747',fillOpacity:1}).addTo(map).bindTooltip(p.name,{permanent:true,direction:'right',className:'town-label'});m.on('click',()=>{currentPlace=p.id;render();});markers.push(m);}}else{$('#map').textContent='Map unavailable. Choose a place above to explore its memories.';}
    render();const pending=localStorage.getItem('namma-pending');if(local&&pending){try{run=await api('/api/runs/'+pending);if(run.pending){view('contribute');renderRun();}}catch{localStorage.removeItem('namma-pending');}}
  }
  init().catch(()=>{$('#workspace').textContent='Unable to load';$('#cards').textContent='The collection could not load. Please refresh when the server is available.';});
})();
