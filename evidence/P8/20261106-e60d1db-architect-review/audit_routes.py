import contextlib,importlib.util,json,os,pathlib,sys
from unittest.mock import patch
r=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve();os.environ['P8C_REVIEW_ROOT']=str(r);sys.path.insert(0,str(r/'portal/tools'))
import test_route_e2e as t
rows=[]
for cls,name in [(t.SeedRouteE2E,'test_create_allowed_full_route_build_postproof_cleanup'),(t.ReleaseRouteE2E,'test_release_full_route_build_scan_sign_attest_artifacts')]:
 case=cls(name);case.setUp();calls=[];real=t._run_step
 def observed(step,*args,**kw):calls.append(step.get('name',step.get('id')));return real(step,*args,**kw)
 try:
  with patch.object(t,'_run_step',side_effect=observed):getattr(case,name)()
  rows.append({'test':name,'result':'PASS','actually_executed_template_steps':calls})
 finally:case.doCleanups()
release=t.q.parse_template(r/'portal/tools/p8c-portal-release.yml.template')
rows.append({'release_dispatch':release['on']['workflow_dispatch'],'gate_consumer_without_producer':True})
(pathlib.Path(__file__).resolve().parent/'route-audit.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
