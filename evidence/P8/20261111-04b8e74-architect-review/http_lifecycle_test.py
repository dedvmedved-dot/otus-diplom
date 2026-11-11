"""Existing R1 contract: total HTTP deadline and consume-before-decode.
Offline: anonymous AF_UNIX sockets only; no TCP/DNS/cluster/registry.
Run from repo root with P8C_REVIEW_ROOT=$PWD python3 <file> -v.
"""
import http.client,json,os,pathlib,socket,sys,tempfile,threading,time,unittest
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'))
import wrapper as w

class HTTPLifecycle(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  p=patch.object(w,'RESERVATION_BASE',str(self.root/'authority'));p.start();self.addCleanup(p.stop)
  self.g={'package_sha256':'d'*64};w._reset_transport();w._reset_read_cache();w._set_budget_base({});w._set_budget_context(self.g,None,{})
  self.addCleanup(w._set_budget_context,None,None,None);self.addCleanup(w._set_budget_base,{});self.addCleanup(w._reset_transport)
 def exercise_stream(self,phase,slow=True):
  left,right=socket.socketpair();left.settimeout(.05);self.addCleanup(left.close);self.addCleanup(right.close)
  stopped=threading.Event()
  def writer():
   try:
    if phase=='headers':
     right.sendall(b'HTTP/1.1 200 OK\r\nX-Test: ')
     for b in b'abcdefghijklmnopqrst':
      if stopped.wait(.015 if slow else 0):return
      right.sendall(bytes([b]))
     right.sendall(b'\r\nContent-Length: 0\r\n\r\n')
    else:
     right.sendall(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n')
     for b in b'00000000000000000001':
      if stopped.wait(.015 if slow else 0):return
      right.sendall(bytes([b]))
     right.sendall(b'\r\nx\r\n0\r\n\r\n')
   except OSError:pass
  thread=threading.Thread(target=writer,daemon=True);thread.start()
  # Real HTTPResponse.begin runs INSIDE opener.open, as for urllib.
  class Opener:
   def open(self,*a,**k):
    left.settimeout(k['timeout']);resp=http.client.HTTPResponse(left);resp.begin();return resp
  outcome=None;body=None;begin=time.monotonic()
  try:
   with patch('urllib.request.build_opener',return_value=Opener()):
    try:body=w._io_call(w.default_http_get,'http://127.0.0.1:9187/metrics',.05,1024)
    except w.ReadError:outcome='ReadError'
   elapsed=time.monotonic()-begin
  finally:stopped.set();left.close();right.close();thread.join(1)
  return outcome,body,elapsed
 def test_total_deadline_includes_response_headers(self):
  err,_,elapsed=self.exercise_stream('headers')
  self.assertEqual(err,'ReadError');self.assertLessEqual(elapsed,.11,{'phase':'headers','deadline':.05,'margin':.06,'elapsed':elapsed})
 def test_total_deadline_includes_chunk_size_line(self):
  err,_,elapsed=self.exercise_stream('chunked')
  self.assertEqual(err,'ReadError');self.assertLessEqual(elapsed,.11,{'phase':'chunk framing','deadline':.05,'margin':.06,'elapsed':elapsed})
 def test_normal_headers_and_chunked_body_positive(self):
  err,body,_=self.exercise_stream('chunked',slow=False);self.assertIsNone(err);self.assertEqual(body,b'x')
 def test_completed_body_is_consumed_when_time_charge_overruns(self):
  # A separate valid charge advances authority while this permitted I/O is in flight.
  # The actual I/O lasts .1s within the timeout1s it received; failure occurs on consume.
  w.write_budget(self.g,{'seconds':w.OVERALL_SEC_CAP-1});clock=[0.0]
  body=json.dumps({'kind':'Cluster','apiVersion':'postgresql.cnpg.io/v1','metadata':{'uid':'c'},'status':{'currentPrimary':'portal-db-1'}}).encode();seen=[]
  def raw(k,path,timeout,cap):
   seen.append(timeout);w._charge(self.g,'seconds',.95,w.OVERALL_SEC_CAP);clock[0]+=.1;return body,0
  with patch.object(w.time,'monotonic',side_effect=lambda:clock[0]),patch.object(w,'run_kubectl_raw',side_effect=raw):
   result=w.run_wal_sample('FAKE',None,None,self.g)
  b=w.read_budget(self.g);self.assertEqual(result[0],w.INCONCLUSIVE);self.assertEqual(seen,[1.0])
  self.assertEqual((b['bytes'],b['wal_bytes']),(len(body),len(body)),b)
 def invalid_utf8(self):
  docs=[{'kind':'Cluster','apiVersion':'postgresql.cnpg.io/v1','metadata':{'uid':'c'},'status':{'currentPrimary':'portal-db-1'}},
        {'kind':'Pod','apiVersion':'v1','metadata':{'uid':'p'},'status':{'podIP':'127.0.0.1'}}]
  bodies=[json.dumps(d).encode() for d in docs];seq=iter(bodies);payload=b'\xff'*64;error=None;result=None
  with patch.object(w,'run_kubectl_raw',side_effect=lambda *a:(next(seq),0)):
   try:result=w.run_wal_sample('FAKE',lambda *a:payload,None,self.g)
   except Exception as e:error=type(e).__name__
  return error,result,w.read_budget(self.g),sum(map(len,bodies))+len(payload)
 def test_non_utf8_metrics_has_typed_nonpass(self):
  err,result,b,expected=self.invalid_utf8()
  self.assertIsNone(err,{'uncaught':err,'budget':b});self.assertEqual(result[0],w.INCONCLUSIVE)
 def test_non_utf8_metrics_all_received_bytes_consumed(self):
  err,result,b,expected=self.invalid_utf8()
  self.assertEqual((b['bytes'],b['wal_bytes']),(expected,expected),{'uncaught':err,'budget':b,'expected':expected})

if __name__=='__main__':unittest.main(verbosity=2)
