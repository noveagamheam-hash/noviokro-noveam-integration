import React, {useState} from 'react';
export default function V13Monitoring(){
  const [key,setKey]=useState(''),[project,setProject]=useState('standalone'),[route,setRoute]=useState('demo'),[status,setStatus]=useState(200),[latency,setLatency]=useState(25),[data,setData]=useState(null),[audit,setAudit]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function request(path,method='GET',body){const res=await fetch(path,{method,headers:{'X-Admin-Key':key,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const json=await res.json();if(!res.ok)throw Error(json.detail?JSON.stringify(json.detail):`HTTP ${res.status}`);return json;}
  async function load(){setBusy(true);setError('');try{const [m,a]=await Promise.all([request(`/api/v1/v13/monitoring/${project}`),request(`/api/v1/v13/audit/${project}`)]);setData(m);setAudit(a);}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function submit(e){e.preventDefault();setBusy(true);setError('');try{await request('/api/v1/v13/observations','POST',{project,route,status_code:Number(status),latency_ms:Number(latency)});await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
  return <section aria-labelledby="v13-heading" style={{border:'1px solid #888',padding:16,marginTop:20,borderRadius:8}}><h2 id="v13-heading">v1.3 Monitoring & Audit</h2><p>Authenticated, operator-submitted staging snapshots. No production traffic interception or live probing.</p>
    <label>Administrator key <input type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}/></label>{' '}
    <label>Project <select value={project} onChange={e=>{setProject(e.target.value);setData(null);setAudit(null)}}>{['standalone','noveam','noveomediater'].map(p=><option key={p}>{p}</option>)}</select></label>{' '}
    <button disabled={busy||!key} onClick={load}>Refresh monitoring</button>
    <form onSubmit={submit}><h3>Record staging test result</h3><label>Route <input required pattern="[a-z0-9_-]+" value={route} onChange={e=>setRoute(e.target.value)}/></label>{' '}<label>HTTP status <input type="number" min="100" max="599" value={status} onChange={e=>setStatus(e.target.value)}/></label>{' '}<label>Latency (ms) <input type="number" min="0" max="600000" step="0.1" value={latency} onChange={e=>setLatency(e.target.value)}/></label>{' '}<button disabled={busy||!key}>Save snapshot</button></form>
    {error&&<p role="alert">{error}</p>}{data&&<><h3>Latest {data.sample_count} observations</h3><p>Server errors: {data.error_count} · Average latency: {data.average_latency_ms??'N/A'} ms</p><ul>{data.observations.map(o=><li key={o.id}>{o.route}: HTTP {o.status_code}, {o.latency_ms} ms ({o.recorded_at})</li>)}</ul></>}
    {audit&&<><h3>Audit history</h3><ul>{audit.events.map(e=><li key={e.id}>{e.action} — {e.recorded_at}</li>)}</ul></>}
  </section>
}
