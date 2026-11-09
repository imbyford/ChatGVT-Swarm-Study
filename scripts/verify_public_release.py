"""Offline public-release verification; runs only saved-response computations."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'PUBLIC_MANIFEST.json').read_text())
for rel,h in manifest['files'].items():assert sha(ROOT/rel)==h,rel
for c in json.loads((ROOT/'CLAIM_TO_EVIDENCE.json').read_text()):assert sha(ROOT/c['file'])==c['sha256'],c['id']
with tempfile.TemporaryDirectory(prefix='chatgvt-offline-') as td:
 work=Path(td)/'release';shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('.git','__pycache__'))
 guard=Path(td)/'guard';guard.mkdir()
 (guard/'sitecustomize.py').write_text("import socket\ndef denied(*a,**k): raise RuntimeError('Network disabled for offline replay')\nsocket.socket=denied\nsocket.create_connection=denied\n")
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(guard))
 for script in ['reproducibility/reproduce.py','scripts/verify_final_audit.py','scripts/check_scoring_independently.py','scripts/analyse_peer_proposals.py','scripts/verify_peer_analysis.py']:
  print('Running '+script,flush=True)
  result=subprocess.run([sys.executable,str(work/script)],cwd=work,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if result.returncode:
   print(result.stdout);raise SystemExit(result.returncode)
  print('PASS '+script,flush=True)
 for rel in ['swarm_analysis/peer_proposal_analysis.json','swarm_analysis/controller_transitions.csv','swarm_analysis/joint_transitions.csv','swarm_analysis/verification.json','evidence/scoring_reassessment.json']:
  assert sha(work/rel)==sha(ROOT/rel),('changed scientific result',rel)
for rel,h in manifest['files'].items():assert sha(ROOT/rel)==h,('modified input',rel)
print('PASS: public hashes and claim bindings; all saved-response replays and consequence analyses; R2 boundary tests; 35,065 arithmetic and 518 peer-proposal checks. No network, GPU, models or provider access.')
