import json,os,pathlib,sys
from unittest.mock import patch
r=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve();os.environ['P8C_REVIEW_ROOT']=str(r);sys.path.insert(0,str(r/'portal/tools'))
import test_route_e2e as t
rows=[]
for cls,name in [(t.SeedRouteE2E,'test_create_allowed_full_route_build_postproof_cleanup'),(t.ReleaseRouteE2E,'test_release_full_route_gate_build_scan_sign_attest_proof_cleanup')]:
 case=cls(name);case.setUp();calls=[];real=t._run_step
 def observed(step,*args,**kw):
  p=real(step,*args,**kw);calls.append({'step':step.get('name',step.get('id')),'exit':p.returncode,'stderr':p.stderr[:1500]});return p
 try:
  with patch.object(t,'_run_step',side_effect=observed):getattr(case,name)()
  rows.append({'test':name,'test_result':'PASS','actually_executed_template_steps':calls})
 finally:case.doCleanups()
(pathlib.Path(__file__).resolve().parent/'route-audit.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
