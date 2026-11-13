import React,{useState} from 'react';

const projects=['standalone','noveam','noveomediater'];
async function jsonFetch(path,token,adminKey){
 const headers={};if(token)headers.Authorization=`Bearer ${token}`;if(adminKey)headers['X-Admin-Key']=adminKey;
 const res=await fetch(path,{headers,cache:'no-store'});let data;try{data=await res.json()}catch{throw Error(`Invalid response (${res.status})`)}
 if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:`HTTP ${res.status}`);return data;
}
export default function V10Console(){
 const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[token,setToken]=useState(''),[adminKey,setAdminKey]=useState('');
 const [project,setProject]=useState('standalone'),[view,setView]=useState('overview'),[data,setData]=useState({}),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function login(e){e.preventDefault();setBusy(true);setError('');try{const r=await fetch('/api/v1/v08/identity/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})});const d=await r.json();if(!r.ok)throw Error(d.detail||`HTTP ${r.status}`);setToken(d.access_token);setPassword('')}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function refresh(){setBusy(true);setError('');setData({});try{
  const requests={identity:[`/api/v1/v08/identity/me/${project}`,token],qa:[`/api/v1/v08/qa/report/${project}`,token],press:[`/api/v1/v08/press/evidence/${project}`,token],monitoring:[`/api/v1/v10/monitoring/${project}`,token],bots:['/api/v1/sandbox/bots',null],runs:['/api/v1/sandbox/runs',null],routes:['/api/v1/routes',null],discovery:['/api/v1/integrations/discoveries',null]};
  const keys=view==='overview'?['identity','monitoring']:view==='qa'?['qa']:view==='bots'?['bots','runs']:view==='api'?['routes','discovery']:view==='press'?['press']:['identity'];
  const next={};for(const key of keys){const [path,t]=requests[key];next[key]=await jsonFetch(path,t,adminKey)}setData(next)
 }catch(e){setError(e.message)}finally{setBusy(false)}}
 return <section className="v10" aria-label="v1.0 authenticated management dashboard"><h2>Noviokro v1.0.0 · Management GUI</h2><p>Local development console. Read-only views; existing APIs and bots remain unchanged. External integrations are not connected.</p>
 <form onSubmit={login} className="v10-controls"><label>Username <input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)}/></label><label>Password <input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button disabled={busy} type="submit">Sign in</button></form>
 <div className="v10-controls"><label>Legacy admin key (for legacy read-only panels) <input type="password" autoComplete="off" value={adminKey} onChange={e=>setAdminKey(e.target.value)}/></label><label>Project <select value={project} onChange={e=>{setProject(e.target.value);setData({})}}>{projects.map(p=><option key={p} value={p}>{p}</option>)}</select></label><button onClick={()=>{setToken('');setAdminKey('');setData({})}}>Clear credentials</button></div>
 <nav aria-label="Management views" className="v10-nav">{[['overview','Overview'],['qa','QA results'],['bots','Bot history'],['api','API management'],['press','Press evidence']].map(([id,label])=><button type="button" key={id} aria-current={view===id?'page':undefined} onClick={()=>{setView(id);setData({});setError('')}}>{label}</button>)}</nav>
 <button onClick={refresh} disabled={busy||(!token&&!adminKey)}>{busy?'Loading…':'Load selected view'}</button>{error&&<p role="alert">{error}</p>}
 <div aria-live="polite" className="v10-output">{Object.keys(data).length===0?<p>Sign in using the v0.8 identity endpoint, select a view, and load data. Legacy API and sandbox views also require the local admin key.</p>:Object.entries(data).map(([name,value])=><section key={name}><h3>{name}</h3><pre>{JSON.stringify(value,null,2)}</pre></section>)}</div>
 <p><small>Access is enforced by existing backend endpoints. Project-scoped QA and monitoring do not expose standalone records to other projects. Credentials are kept only in component memory. Typed NUI navigation is available above.</small></p></section>
}
