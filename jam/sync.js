/* Hammer Jam sync: keeps the tracker and wall pages in sync across devices.
   Fill in the two values below from Supabase (Project Settings > API). The anon key is meant to be public. */
const SUPABASE_URL = 'https://clwinxnwkhijlwbdwnhy.supabase.co';   // e.g. 'https://abcdxyz.supabase.co'
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsd2lueG53a2hpamx3YmR3bmh5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM1NzM2ODUsImV4cCI6MjEwOTE0OTY4NX0.U9AXC6BoWAhe7YdT2ZBea_VqvvTA2g3CoVlr0G0DtIY';   // the "anon public" key

(function(){
  "use strict";
  const KEY='hammerJamTracker.v2', SKEY='hammerJamSync.v1', POLL=10000;
  let cfg=readCfg(), timer=null, dirty=false, busy=false, lastPull=0, onRemote=null, getState=null, statusEl=null, panel=null;

  function readCfg(){try{return JSON.parse(localStorage.getItem(SKEY)||'null')||{};}catch(e){return {};}}
  function writeCfg(){try{localStorage.setItem(SKEY,JSON.stringify(cfg));}catch(e){}}
  const ready=()=>!!(SUPABASE_URL&&SUPABASE_KEY);
  const linked=()=>ready()&&cfg.id&&cfg.pass;

  async function rpc(fn,body){
    const r=await fetch(SUPABASE_URL.replace(/\/$/,'')+'/rest/v1/rpc/'+fn,{method:'POST',
      headers:{'apikey':SUPABASE_KEY,'Authorization':'Bearer '+SUPABASE_KEY,'Content-Type':'application/json'},body:JSON.stringify(body)});
    const txt=await r.text(); let j=null; try{j=txt?JSON.parse(txt):null;}catch(e){}
    if(!r.ok)throw new Error((j&&(j.message||j.hint))||('Server said '+r.status));
    return j;
  }
  function blankState(){const now=Date.now();return {v:2,pay:40,jamStart:Date.parse('2026-11-01T07:00:00Z'),jamEnd:Date.parse('2026-11-16T07:00:00Z'),
    builders:[],boosts:[],potTotal:88,potUsed:0,ret:{mode:'ideal'},sleep:{from:'00:30',to:'09:00'},
    walls:{counts:{15:0,16:0,17:0,18:0,19:0},rings:0,by:Date.parse('2026-11-14T07:00:00Z'),log:[],base:{counts:{15:0,16:0,17:0,18:0,19:0},rings:0,t:now}},
    loot:{gold:null,elix:null,keepE:4}};}
  function localState(){if(getState){try{return JSON.parse(JSON.stringify(getState()));}catch(e){}}try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){return null;}}
  function applyRemote(data,updated){
    try{localStorage.setItem(KEY,JSON.stringify(data));}catch(e){}
    cfg.updated=updated; writeCfg();
    if(onRemote)onRemote(data);
  }

  /* ---------- pull / push ---------- */
  async function pull(force){
    if(!linked()||busy||dirty)return; busy=true;
    try{const j=await rpc('jam_load',{p_id:cfg.id});
      if(j&&j.updated_at&&(force||!cfg.updated||Date.parse(j.updated_at)>Date.parse(cfg.updated))){applyRemote(j.data,j.updated_at);}
      lastPull=Date.now(); status();
    }catch(e){status('Offline: changes stay on this device until it reconnects.');}
    busy=false;
  }
  function push(state){
    if(!linked())return; dirty=true; clearTimeout(timer);
    timer=setTimeout(async()=>{
      if(busy){push(state);return;} busy=true;
      try{const j=await rpc('jam_save',{p_id:cfg.id,p_pass:cfg.pass,p_data:localState()||state,p_since:cfg.updated||null});
        dirty=false;
        if(j&&j.conflict){busy=false;applyRemote(j.data,j.updated_at);status('Another device saved first. Its version is loaded; redo your last change if it is missing.');return;}
        cfg.updated=j.updated_at; writeCfg(); lastPull=Date.now(); status();
      }catch(e){dirty=false;status(/wrong password/i.test(e.message)?'Password no longer matches. Reconnect below.':'Could not sync: '+e.message);}
      busy=false;
    },1200);
  }

  /* ---------- connect ---------- */
  async function connect(id,pass,fresh){
    id=(id||'').trim().toLowerCase();
    if(!/^[a-z0-9_-]{3,32}$/.test(id))return 'Use 3 to 32 letters, numbers, - or _ for the ID.';
    if((pass||'').length<4)return 'Use a password of at least 4 characters.';
    let res; try{res=await rpc('jam_check',{p_id:id,p_pass:pass});}catch(e){return 'Could not reach the sync server: '+e.message;}
    if(res==='wrong')return 'Wrong password for that ID.';
    cfg={id,pass,updated:null}; writeCfg();
    if(res==='new'){
      const data=fresh?blankState():(localState()||blankState());
      try{const j=await rpc('jam_save',{p_id:id,p_pass:pass,p_data:data,p_since:null});cfg.updated=j.updated_at;writeCfg();applyRemote(data,j.updated_at);}
      catch(e){return 'Could not create the ID: '+e.message;}
      return 'Created "'+id+'". Use the same ID and password on your other devices.';
    }
    await pull(true); return 'Connected. This device now shows "'+id+'".';
  }
  function disconnect(){cfg={};writeCfg();status();}

  /* ---------- UI ---------- */
  function status(msg){
    if(!statusEl)return;
    if(!ready()){statusEl.textContent='Sync is not set up yet (fill in sync.js).';return;}
    if(!linked()){statusEl.textContent='Not synced. Data stays on this device.';return;}
    const ago=lastPull?Math.round((Date.now()-lastPull)/1000):null;
    statusEl.textContent=msg||('Synced as '+cfg.id+(ago!=null?' · checked '+(ago<5?'just now':ago+'s ago'):''));
  }
  function buildUI(){
    const wrap=document.querySelector('.wrap'); if(!wrap)return;
    const box=document.createElement('section'); box.className='panel'; box.setAttribute('aria-label','Sync');
    box.innerHTML=`<div class="row spread"><span class="sub" id="jsStatus"></span><button class="small" id="jsToggle" type="button">Sync settings</button></div>
      <div id="jsPanel" class="hide" style="display:grid;gap:8px">
        <div class="row"><label class="sub">Base ID <input id="jsId" type="text" autocomplete="username" style="width:150px" placeholder="sameer-main"></label>
          <label class="sub">Password <input id="jsPass" type="password" autocomplete="current-password" style="width:140px"></label></div>
        <label class="sub"><input id="jsFresh" type="checkbox"> New ID starts empty (for a friend's base)</label>
        <div class="row"><button class="small" id="jsGo" type="button">Connect</button><button class="small" id="jsOut" type="button">Disconnect this device</button></div>
        <div class="note" id="jsMsg">A new ID is created the first time you connect with it. On another device, enter the same ID and password once; after that it stays signed in.</div>
      </div>`;
    wrap.insertBefore(box,wrap.children[1]||null);
    statusEl=box.querySelector('#jsStatus'); panel=box.querySelector('#jsPanel');
    box.querySelector('#jsToggle').onclick=()=>panel.classList.toggle('hide');
    box.querySelector('#jsId').value=cfg.id||'';
    box.querySelector('#jsGo').onclick=async()=>{const m=box.querySelector('#jsMsg');m.textContent='Connecting…';
      m.textContent=await connect(box.querySelector('#jsId').value,box.querySelector('#jsPass').value,box.querySelector('#jsFresh').checked);
      box.querySelector('#jsPass').value='';status();};
    box.querySelector('#jsOut').onclick=()=>{disconnect();box.querySelector('#jsMsg').textContent='This device is disconnected. Its data stays here.';};
    if(!ready()||!linked())panel.classList.remove('hide');
    status();
  }

  window.JamSync={
    push, pull,
    onRemote(fn){onRemote=fn;},
    state(fn){getState=fn;},
    start(){buildUI(); pull(false); setInterval(()=>pull(false),POLL);
      document.addEventListener('visibilitychange',()=>{if(!document.hidden)pull(false);});
      setInterval(()=>status(),5000);}
  };
})();