// Offline actual app.js renderers with synthetic DOM/fetch; not a browser or PAK test.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const root=process.argv[2] || '.';
const app=readFileSync(root+'/portal/web/app.js','utf8');
const els={};
const el=id=>els[id]??={innerHTML:'',textContent:'',className:'',classList:{toggle(){}}};
const calls=[];
const env=data=>({freshness:'fresh',partial:false,sources:[],warnings:[],nextCursor:null,data});
const fixtures={
  summary:env({overall:'healthy',counts:{nodesReady:3,nodesExpected:3,nodesObserved:3},alerts:[]}),
  database:env({readyInstances:3,desiredInstances:3,health:'healthy'}),
  storage:env({scope:'kubernetes_objects',items:[{kind:'VolumeSnapshot',health:'unknown',snapshotReadyToUse:null}]}),
  backups:env({velero:{locations:[],backups:[],restores:[]},postgresql:{expectedSchedule:'0 0 2 * * *',schedule:'0 0 3 * * *',expectedTarget:'prefer-standby',target:'primary',barman:{scope:'single_exporter_sample',firstRecoverabilityPointTimestamp:1792469710,lastAvailableBackupTimestamp:1792469710,lastFailedBackupTimestamp:null},wal:{state:'critical',expectedArchiveTimeoutSeconds:300}}}),
  events:{...env({items:[],storage:'postgresql'}),nextCursor:'synthetic-next-page'}
};
const ctx={document:{getElementById:el,querySelectorAll:()=>[],querySelector:()=>null},setInterval(){},fetch:async url=>{calls.push(url);const key=url.split('/').pop().split('?')[0];return{status:200,ok:true,json:async()=>fixtures[key]||env({items:[]})}}};
vm.createContext(ctx);vm.runInContext(app,ctx);
await vm.runInContext('renderOverview()',ctx);
await vm.runInContext('renderBackups()',ctx);
await vm.runInContext('renderEvents()',ctx);
const before=calls.length;
vm.runInContext("setOverall('critical','stale')",ctx);
const result={
  kind:'offline actual JS renderer execution, synthetic DOM/fetch',
  unknownSnapshotStorageHealth:vm.runInContext("storageHealth({items:[{health:'unknown',snapshotReadyToUse:null}]})",ctx),
  staleCriticalClass:el('overall-status').className,
  backupMeta:el('pg-backup-meta').innerHTML,
  realRecoverabilityTimestampRendered:el('pg-backup-meta').innerHTML.includes('recoverabilityPoint=1792469710'),
  observedScheduleRendered:el('pg-backup-meta').innerHTML.includes('schedule=0 0 3 * * *'),
  paginationRequested:calls.some(url=>url.includes('cursor=')),
  paginationNoteRendered:el('table-events').innerHTML.includes('следующая страница'),
  disposition:'FAIL: unknown storage -> healthy, stale critical -> warning, actual Barman/schedule omitted, cursor note without navigation'
};
console.log(JSON.stringify(result,null,2));
