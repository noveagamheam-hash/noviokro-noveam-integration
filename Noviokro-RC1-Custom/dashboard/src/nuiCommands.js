export const FEATURES=[
 {id:'overview',title:'Overview',status:'Local dashboard',description:'An overview of existing and planned Noviokro capabilities.'},
 {id:'bots',title:'Multi-bot sandbox',status:'Basic',description:'Existing DevBot, TestBot, QA, marketing, branding, PR and press workflows remain in their original panels.'},
 {id:'discovery',title:'Custom API discovery',status:'Staging only / development',description:'Original discovery engine is a development requirement; no live scanning is enabled here.'},
 {id:'auth',title:'Administrator authentication',status:'Partial',description:'Existing v0.8 identity and legacy keys remain unchanged; this panel does not handle credentials.'},
 {id:'roles',title:'Multi-role permissions',status:'Partial',description:'Project-scoped permissions require continued enforcement and regression testing.'},
 {id:'qa',title:'QA testing & monitoring',status:'Offline tests',description:'Use existing QA and monitoring endpoints and panels below for actual records.'},
 {id:'drafts',title:'AI content drafting',status:'Limited',description:'Existing reviewable draft flows; optional local inference remains configuration-dependent.'},
 {id:'gateway',title:'Graphical API management',status:'Not complete',description:'Gateway and registry remain unchanged; production readiness is not claimed.'},
 {id:'nui',title:'NUI accessibility',status:'Basic',description:'Typed navigation commands, optional voice recognition, keyboard controls and accessibility toggles.'},
 {id:'callbot',title:'DevBot & CallBot',status:'Not complete',description:'DevBot foundations exist; complete autonomous workflows and CallBot remain future work.'},
 {id:'noveam',title:'NOVEAM integration',status:'Not connected',description:'No production routing or data changes.'},
 {id:'noveomediater',title:'Noveomediater integration',status:'Not connected',description:'No production routing or data changes.'}
];
export function interpretCommand(input){
 const value=String(input||'').trim().toLowerCase();
 if(!value)return {message:'Enter a command. Try “help”.'};
 if(/^(help|commands|what can you do)[?.!]*$/.test(value))return {message:'Try: show overview, show bots, show discovery, show authentication, show roles, show QA, show drafts, show gateway, show NUI, show CallBot, show NOVEAM, or show Noveomediater.'};
 const map=[['noveomediater',/noveomediater/],['noveam',/\bnoveam\b/],['callbot',/callbot|devbot/],['discovery',/discover|discovery|endpoint/],['auth',/auth|login|administrator/],['roles',/role|permission|rbac/],['qa',/qa|test|monitor/],['drafts',/draft|marketing|branding|press|public relations|\bpr\b/],['gateway',/gateway|route|graphical api/],['nui',/nui|accessib|voice/],['bots',/bot|sandbox/],['overview',/overview|home|dashboard/]];
 if(!/^(show|open|view|go to|navigate to|display|tell me about|status of)\b/.test(value))return {message:'Only read-only navigation commands are supported. Try “show QA” or “help”.'};
 for(const [section,pattern] of map){if(pattern.test(value)){const feature=FEATURES.find(x=>x.id===section);return {section,message:`Showing ${feature.title}. Status: ${feature.status}.`}}}
 return {message:'Unknown section. Type “help” for supported commands.'};
}
