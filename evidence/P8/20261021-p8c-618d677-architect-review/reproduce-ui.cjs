const fs = require('fs');
const vm = require('vm');
const elements = new Map();
function element(id) { if (!elements.has(id)) elements.set(id,{innerHTML:'',textContent:'',className:'',classList:{toggle(){}},addEventListener(){}}); return elements.get(id); }
const calls=[];
const fixtures={summary:{overall:'critical',counts:{nodesReady:3,nodesExpected:3,nodesObserved:3,podsReady:1,podsObserved:1},alerts:[]},database:{readyInstances:3,desiredInstances:3,phase:'old state'},backups:{velero:{health:'healthy'},postgresql:{health:'healthy'}},storage:{items:[{health:'healthy'}]},events:{items:[]}};
const ctx={document:{getElementById:element,querySelectorAll:()=>[],querySelector:()=>null},setInterval:()=>0,fetch:async p=>{calls.push(p);const k=p.split('/').pop().split('?')[0];return{ok:true,status:200,json:async()=>({data:fixtures[k]||{items:[]},freshness:'stale',nextCursor:'more'})};}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('portal/web/app.js','utf8'),ctx);
(async()=>{
 await vm.runInContext('renderOverview()',ctx);
 const overview={overallClass:element('overall-status').className,overallText:element('overall-text').textContent,greenCards:(element('cards').innerHTML.match(/card healthy/g)||[]).length,alerts:element('alerts').innerHTML};
 calls.length=0;
 await vm.runInContext('renderKubernetes()',ctx);
 await vm.runInContext('renderEvents()',ctx);
 console.log(JSON.stringify({execution:'actual app.js in Node VM; synthetic DOM/fetch, no browser/network',overview,requests:calls,followupCursorRequest:calls.some(x=>x.includes('cursor=')),eventsNote:element('table-events').innerHTML},null,2));
})();
