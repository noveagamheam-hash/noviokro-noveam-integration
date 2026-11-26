import React, {useState} from 'react';

export default function NoveamIntegration() {
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Configure the NOVEAM backend address on the manager before connecting.');
  const [catalogs, setCatalogs] = useState([]);
  async function request(path, options = {}) {
    const response = await fetch('/api/v1/integrations' + path, {
      ...options, cache: 'no-store',
      headers: {'X-Admin-Key': key, 'Content-Type': 'application/json'},
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}).`);
    if (data === null) throw new Error('The manager did not return JSON. Check the dashboard proxy.');
    return data;
  }
  async function run(action) {
    if (busy || !key.trim()) return;
    setBusy(true); setMessage('Connecting to the manager…');
    try {
      if (action === 'routing') {
        const result = await request('/noveam/routing');
        setMessage(result.enabled && result.backend
          ? `HTTP gateway enabled: ${result.http_prefix} → ${result.backend}. WebSockets still use the direct backend.`
          : 'HTTP gateway is not configured/enabled. Set the manager backend origin and enable the NOVEAM gateway, then restart the manager.');
      } else if (action === 'health') {
        const result = await request('/health/noveam/backend');
        setMessage(result.reachable && result.available
          ? `NOVEAM catalog is available at ${result.probe_path}. This checks catalog availability, not database health.`
          : `NOVEAM catalog is unavailable${result.upstream_status ? ` (HTTP ${result.upstream_status})` : ''}.`);
      } else {
        if (action === 'discover') await request('/discover', {
          method: 'POST', body: JSON.stringify({project: 'noveam', service: 'backend'}),
        });
        const rows = await request('/discoveries?project=noveam');
        setCatalogs(rows.filter(row => row.service === 'backend'));
        setMessage(action === 'discover' ? 'NOVEAM catalog imported. No application endpoints were executed.' : 'Saved NOVEAM catalogs loaded.');
      }
    } catch (error) { setMessage(error.message || 'Unable to connect to the manager.'); }
    finally { setBusy(false); }
  }
  return <section className="v10" aria-labelledby="noveam-link-heading">
    <h2 id="noveam-link-heading">NOVEAM API linking</h2>
    <p>Inspect the configured backend and import its API catalog. Existing NOVEAM traffic and authentication stay on their current routes.</p>
    <label>Manager admin key <input type="password" disabled={busy} value={key} onChange={e => {setKey(e.target.value);setCatalogs([]);}} autoComplete="off" /></label>
    <div className="v10-controls">
      <button disabled={busy || !key.trim()} onClick={() => run('routing')}>Check API routing configuration</button>
      <button disabled={busy || !key.trim()} onClick={() => run('health')}>Check NOVEAM connection</button>
      <button disabled={busy || !key.trim()} onClick={() => run('discover')}>Import NOVEAM API catalog</button>
      <button disabled={busy || !key.trim()} onClick={() => run('load')}>Load saved catalogs</button>
    </div>
    <p>Local frontend: <a href="http://127.0.0.1:5500/login.html?gateway=noviokro" target="_blank" rel="noopener noreferrer">Open NOVEAM through Noviokro</a>. Enable the manager gateway before using this link.</p>
    <p role="status" aria-live="polite">{message}</p>
    <div className="v10-output">{catalogs.map(catalog => <article key={catalog.id}>
      <h3>{catalog.title} · {catalog.endpoints.length} routes</h3>
      <p>{catalog.spec_version} · {catalog.discovered_at}</p>
      <pre>{catalog.endpoints.map(route => `${route.method} ${route.path}${route.query?.length ? ` · query: ${route.query.join(', ')}` : ''}`).join('\n')}</pre>
    </article>)}</div>
  </section>;
}
