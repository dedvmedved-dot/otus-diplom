"""Review harness: prohibit all network connections/DNS in this offline process tree."""
import sys,os,json

def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):
  p=os.environ.get('P8C_NETWORK_GUARD_LOG')
  if p:
   with open(p,'a') as f:f.write(json.dumps({'event':event,'result':'BLOCKED_OFFLINE'})+'\n')
  raise OSError('review offline network guard')
sys.addaudithook(guard)
