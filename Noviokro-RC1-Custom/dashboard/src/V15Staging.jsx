import React, {useState} from 'react';
export default function V15Staging(){
  const [key,setKey]=useState('');
  const [status,setStatus]=useState(null);
  const [summary,setSummary]=useState(null);
  const [error,setError]=useState('');
  async function load(){
    setError('');
    try {
      const get=async path=>{
        const response=await fetch(path,{headers:{'X-Admin-Key':key},cache:'no-store'});
        const result=await response.json();
        if(!response.ok)throw new Error(result.detail||`HTTP ${response.status}`);
        return result;
      };
      const [nextStatus,nextSummary]=await Promise.all([
        get('/api/v1/v15/status'),get('/api/v1/v15/traffic-summary')
      ]);
      setStatus(nextStatus);setSummary(nextSummary);
    }catch(e){setError(e.message);setStatus(null);setSummary(null)}
  }
  return <section aria-label="v1.5 staging diagnostics" style={{borderTop:'2px solid #777',marginTop:24,paddingTop:16}}>
    <h2>v1.5 — Staging gateway diagnostics</h2>
    <p>Read-only, standalone monitoring. No production project connection.</p>
    <label>Administrator key <input type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}/></label>
    <button type="button" onClick={load}>Load staging status</button>
    {error&&<p role="alert">{error}</p>}
    {status&&<p role="status">Telemetry: {status.telemetry_enabled?'enabled':'disabled'} · DB rate limiting: {status.db_rate_limit_enabled?'enabled':'disabled'} · Staging proxy: {status.proxy_enabled?'enabled':'disabled'} · Production ready: no</p>}
    {summary&&<div><h3>Staging route summary</h3>{!summary.enabled?<p>Telemetry is disabled.</p>:summary.routes.length===0?<p>No recorded staging requests.</p>:<table><thead><tr><th>Route</th><th>Requests</th><th>5xx</th><th>429</th><th>Avg latency (ms)</th></tr></thead><tbody>{summary.routes.map(r=><tr key={r.route}><td>{r.route}</td><td>{r.requests}</td><td>{r.server_errors}</td><td>{r.rate_limited}</td><td>{r.avg_latency_ms}</td></tr>)}</tbody></table>}</div>}
  </section>;
}
