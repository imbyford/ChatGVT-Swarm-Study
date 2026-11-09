"""Study 2-R2 immutable execution release; preserves original evaluator/model bytes."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
MODEL_SHA='2c8b65d3e243f09e3771833fca61758501b5101f30360520e6c5f42d5b647117'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify_freeze(root=ROOT):
 p=root/'r2_freeze.v1.json';m=json.loads(p.read_text())
 if m['study_id']!='study2-r2' or m['maximum_requests']!=741 or m['maximum_output_tokens']!=94848 or m['model_manifest_sha256']!=MODEL_SHA:raise ValueError('Wrong R1 freeze')
 for rel,record in m['files'].items():
  f=root/rel
  if f.is_symlink() or not f.resolve().is_relative_to(root.resolve()) or not f.is_file() or f.stat().st_size!=record['bytes'] or sha(f)!=record['sha256']:raise ValueError('Frozen payload changed: '+rel)
 for folder in ('r1','integration','experiment','simulator','tools','launch_tools'):
  for f in (root/folder).rglob('*.py'):
   if f.relative_to(root).as_posix() not in m['files']:raise ValueError('Unbound executable')
 if sha(root/'config/models.manifest.json')!=MODEL_SHA:raise ValueError('Wrong trained checkpoints')
 return {'suite_sha256':sha(p),'model_manifest_sha256':MODEL_SHA,'candidate_manifest_sha256':m['candidate_manifest_sha256'],'maximum_requests':741,'maximum_output_tokens':94848,'frozen_files':len(m['files'])}
def live_routes():
 import experiment
 from binding import BASE,REVISION,verify_files
 from responses_client import Route
 routes={a:Route(**r) for a,r in verify_files().items()};routes['U']=Route(BASE,'public-deployment-base:'+BASE+'@'+REVISION,BASE);return routes
