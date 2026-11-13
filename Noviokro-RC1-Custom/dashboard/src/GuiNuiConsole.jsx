import React,{useState,useRef} from 'react';
import {interpretCommand,FEATURES} from './nuiCommands.js';

export default function GuiNuiConsole(){
 const [query,setQuery]=useState(''),[feedback,setFeedback]=useState('Type “show QA”, “show bots”, “show discovery”, or “help”.'),[active,setActive]=useState('overview'),[listening,setListening]=useState(false);
 const [contrast,setContrast]=useState(false),[large,setLarge]=useState(false);const recognition=useRef(null);
 function execute(value){const action=interpretCommand(value);setFeedback(action.message);if(action.section)setActive(action.section);}
 function startVoice(){const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SpeechRecognition){setFeedback('Voice recognition is unavailable in this browser. Typed commands remain available.');return;}
 try{const rec=new SpeechRecognition();rec.lang='en-IN';rec.interimResults=false;rec.maxAlternatives=1;
 rec.onresult=e=>{const text=e.results[0][0].transcript;setQuery(text);execute(text)};
 rec.onerror=e=>{setFeedback('Voice input error: '+e.error+'. You can type a command instead.');setListening(false)};
 rec.onend=()=>setListening(false);recognition.current=rec;rec.start();setListening(true)}catch{setFeedback('Unable to start voice recognition. Use typed commands.')}}
 function stopVoice(){recognition.current?.stop();setListening(false)}
 return <section id="noviokro-gui-nui" className={'ng-shell '+(contrast?'ng-contrast ':'')+(large?'ng-large':'')} aria-label="Noviokro GUI and NUI console">
 <header className="ng-header"><div><p className="ng-eyebrow">Noviokro · Additive local interface</p><h2>GUI & NUI Control Center</h2><p>Safe, read-only navigation and feature status. Existing consoles remain below.</p></div><span className="ng-pill">Local development</span></header>
 <div className="ng-toolbar"><label><input type="checkbox" checked={contrast} onChange={e=>setContrast(e.target.checked)}/> High contrast</label><label><input type="checkbox" checked={large} onChange={e=>setLarge(e.target.checked)}/> Larger text</label><a href="#legacy-console">Skip to existing console</a></div>
 <div className="ng-layout"><nav aria-label="GUI feature sections" className="ng-nav">{FEATURES.map(item=><button type="button" key={item.id} aria-current={active===item.id?'page':undefined} className={active===item.id?'ng-active':''} onClick={()=>setActive(item.id)}>{item.title}</button>)}</nav>
 <div className="ng-content"><h3>{FEATURES.find(x=>x.id===active)?.title}</h3><p>{FEATURES.find(x=>x.id===active)?.description}</p><div className="ng-grid">{(active==='overview'?FEATURES.filter(x=>x.id!=='overview'):FEATURES.filter(x=>x.id===active)).map(x=><article key={x.id} className="ng-card"><strong>{x.title}</strong><span className="ng-status">{x.status}</span><p>{x.description}</p>{x.id!=='overview'&&<button type="button" onClick={()=>setActive(x.id)}>View section</button>}</article>)}</div>
 <div className="ng-nui"><h3>Natural-language commands</h3><p>Commands only change this panel. They never run bots, scan networks, or change settings.</p><form onSubmit={e=>{e.preventDefault();execute(query)}}><label htmlFor="ng-command">Command</label><div className="ng-command"><input id="ng-command" value={query} onChange={e=>setQuery(e.target.value)} placeholder="e.g. show QA"/><button type="submit">Run command</button><button type="button" onClick={listening?stopVoice:startVoice} aria-pressed={listening}>{listening?'Stop microphone':'Voice input'}</button></div></form><p role="status" aria-live="polite" className="ng-feedback">{feedback}</p><p className="ng-hint">Voice recognition may use browser/vendor services. Do not dictate secrets. Microphone access requires permission.</p></div></div></div></section>;
}
