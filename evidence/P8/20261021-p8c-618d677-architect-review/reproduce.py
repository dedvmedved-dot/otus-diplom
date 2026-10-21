import json, pathlib, re, sqlite3, subprocess, sys, yaml
root=pathlib.Path(__file__).parent
wf=yaml.safe_load((root/'portal/tools/p8c-portal-release.yml.template').read_text())
step=next(x for x in wf['jobs']['release']['steps'] if x.get('name','').startswith('SBOM + provenance'))
raw=step['run'].split('<<EOF\n',1)[1].split('\nEOF',1)[0]
predicate=json.loads(raw)
oa=json.loads((root/'docs/architecture/p8c/openapi.json').read_text())
lag=oa['components']['schemas']['Health']['properties']['persistenceLagSeconds']
store=(root/'portal/internal/store/store.go').read_text()
verify=store.split('func (s *Store) VerifySchema',1)[1].split('// ChecksumFile',1)[0]
helpers=[]
for cwd,cmd in [(root,['python3','portal/tools/test_helpers.py','-v']),(root/'portal',['python3','tools/test_helpers.py','-v'])]:
 p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
 helpers.append({'cwd':str(cwd.relative_to(root)),'argv':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
# SQL order/OFFSET semantic counterexample only, SQLite in memory, NOT a PG integration test.
db=sqlite3.connect(':memory:');db.execute('create table e(id integer, ingested_at integer)')
db.executemany('insert into e values (?,?)',[(1,3),(2,2),(3,1)])
page=lambda n:[r[0] for r in db.execute('select id from e order by ingested_at desc,id desc limit 2 offset ?', (n,))]
p1=page(0);db.execute('update e set ingested_at=4 where id=3');p2=page(2)
handlers=(root/'portal/internal/httpapi/handlers.go').read_text()
counts={name:body.count('s.snapshot()') for name,body in re.findall(r'func \(s \*Server\) (handle\w+)\([^\n]+\{\n(.*?)(?=\nfunc |\Z)',handlers,re.S)}
out={'reviewedHead':'618d6775ff159353412312d1b57f11813d8c7aee','helperRuns':helpers,'provenanceFileTopLevelKeys':list(predicate),'expectedPredicateFieldsMissing':[k for k in ['builder','buildType','invocation'] if k not in predicate],'lagContract':lag,'emittedInitialFailureLag':-1,'verifySchemaMissingColumns':[k for k in ['id','object_kind','object_namespace','object_name'] if '{"portal.timeline_events", "'+k+'"}' not in verify],'eventsOffsetCounterexample':{'engine':'SQLite; same ORDER/OFFSET semantics only','page1':p1,'page2AfterUpsert':p2,'duplicateIDs':list(set(p1)&set(p2)),'unseenID':3},'snapshotReadsPerHandler':counts}
print(json.dumps(out,indent=2))
