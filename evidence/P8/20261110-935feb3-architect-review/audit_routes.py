import json,os,pathlib,sys
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve();os.environ['P8C_REVIEW_ROOT']=str(ROOT);sys.path.insert(0,str(ROOT/'portal/tools'))
import test_route_e2e as t
rows=[]
for cls,name in [(t.SeedRouteE2E,'test_create_allowed_full_route'),(t.ReleaseRouteE2E,'test_full_route_all_mandatory_steps_zero')]:
 c=cls(name);c.setUp();calls=[];real=t._run_step
 def track(step,*a,**k):
  p=real(step,*a,**k)
  calls.append({'step':step.get('name',step.get('id')),'exit':p.returncode});return p
 try:
  with patch.object(t,'_run_step',side_effect=track):getattr(c,name)()
  rows.append({'test':name,'result':'PASS','calls':calls})
 finally:c.doCleanups()
(pathlib.Path(__file__).resolve().parent/'route-audit.json').write_text(json.dumps(rows,indent=2))
print('routes',[(x['test'],len(x['calls']),all(c['exit']==0 for c in x['calls'])) for x in rows])
