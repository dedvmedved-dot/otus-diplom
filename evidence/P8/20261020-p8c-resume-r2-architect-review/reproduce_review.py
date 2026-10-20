"""Read-only local reproduction for source commit 17fdf97. No cluster/network calls.

Usage: python3 reproduce_review.py PATH_TO_CHECKOUT_ROOT
Only synthetic inputs are used. Every helper subprocess and password prompt is mocked.
"""
import contextlib
import getpass
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

root = Path(sys.argv[1])
results = []
for filename in ('provision-ui-auth.py', 'provision-registry-pull.py'):
    path = root / 'portal/tools' / filename
    spec = importlib.util.spec_from_file_location('review_helper', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    def mocked_run(argv, **kwargs):
        calls.append(argv)
        if 'get' in argv:
            return SimpleNamespace(returncode=1, stdout='', stderr='Forbidden')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    captured = io.StringIO()
    with patch.object(sys, 'argv', ['helper', '--context', 'synthetic-context']), \
         patch.object(getpass, 'getpass', return_value='A' * 43), \
         patch.object(subprocess, 'run', side_effect=mocked_run), \
         contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        code = module.main()
    results.append({'case': filename + ': forbidden precheck', 'exit_code': code,
                    'write_attempted': any('apply' in a or 'create' in a for a in calls),
                    'write_verb': 'apply' if any('apply' in a for a in calls) else None,
                    'expected': 'nonzero exit and no write; FAIL reproduced'})

js = r'''
const fs = require('fs');
const vm = require('vm');
const elements = new Map();
const element = id => { if (!elements.has(id)) elements.set(id, {textContent:'',innerHTML:'',className:'',classList:{add(){},remove(){},toggle(){}}}); return elements.get(id); };
const sandbox = {
  document:{getElementById:element,querySelectorAll:()=>[],querySelector:()=>null},
  setInterval:()=>0,
  fetch:async path=>({status:200,ok:true,json:async()=>({freshness:'fresh',data:
    path.endsWith('/summary') ? {overall:'healthy',counts:{nodesObserved:3,nodesReady:3,nodesExpected:3},alerts:[],subsystems:[]} :
    path.endsWith('/database') ? {readyInstances:3,desiredInstances:3,health:'healthy'} : {items:[]}})}),
  report:value=>process.stdout.write(JSON.stringify(value)),
};
const source = fs.readFileSync(process.argv[1], 'utf8');
vm.runInNewContext(source + `\n(async()=>{const out=[];
try { await renderKubernetes(); out.push({case:'frontend data.items',result:'unexpected success'}); }
catch(e){out.push({case:'frontend data.items',result:'FAIL reproduced',error:e.message});}
await renderOverview();
out.push({case:'summary overall',expected:'healthy',actual:document.getElementById('overall-text').textContent});
report(out);
})().catch(e=>report({harnessError:e.message}));`,sandbox);
'''
node = subprocess.run(['node', '-e', js, str(root / 'portal/web/app.js')],
                      capture_output=True, text=True, timeout=15, check=True)
results.extend(json.loads(node.stdout))
print(json.dumps({'review_head':'17fdf97b96ab19498d973f969bddc6244cb95af0',
                  'mode':'synthetic local mocks only; no real credentials, Kubernetes or GitHub mutations',
                  'results':results}, ensure_ascii=False, indent=2))
