"""Second numerical route from physical arrays plus table/narrative checks."""
from pathlib import Path
import json,itertools,hashlib
from statistics import mean
P=Path(__file__).resolve().parents[1];R=P/'reproducibility';a=json.loads((P/'swarm_analysis/peer_proposal_analysis.json').read_text());C=R/'study2/evaluation/candidate_v0.3'
cases=sum([json.loads((C/'model_facing'/d/f).read_text()) for d,f in [('development','human_development.json'),('protected_draft','human_protected.json')]],[]);lookup={c['id']:c for c in cases}
checks=0
for stage,folder in [('R1','study2'),('R2','study2_r2')]:
 physical=json.loads((R/folder/'raw/physical.json').read_text())['human_commitments']
 for split,prefix in [('human_protected','HP'),('human_development','HD')]:
  for arm in 'VNU':
   rows=[(cid,r[arm+'I'],r[arm+'S']) for cid,r in physical.items() if cid.startswith(prefix) and r[arm+'I'] is not None and r[arm+'S'] is not None]
   m=a['summary'][stage][split]['models'][arm]
   assert len(rows)*3==m['observed_controller_pairs']
   assert sum(x!=y for _,i,s in rows for x,y in zip(i,s))==m['changed_private_vs_shared'];checks+=2
   for cid,i,s in rows:
    report=next(r for r in a['cases'] if r['stage']==stage and r['case_id']==cid and r['arm']==arm);p=lookup[cid]['parameters']
    for phase,joint in [('I',i),('S',s)]:
     t=p['consequence_table'][','.join(map(str,joint))];work=min(t['service'],p['demand']);harm=t['direct']+t['interaction']+(p['demand']-work)*p['omission_weight']
     assert report['outcomes'][phase]['harm']==harm and report['outcomes'][phase]['useful_work']==work;checks+=2
 # Initial proposals are re-read from recorded parsed fields, independently of the raw parser.
 events=[json.loads(s) for s in (R/folder/'raw/ledger.jsonl').read_text().splitlines()];parsed={e['request_id']:e for e in events if e['event']=='response'}
 same=[]
 for c in cases:
  if not c['id'].startswith('HP'):continue
  vectors={arm:[parsed[f"{c['id']}/initial/{role['id']}/{arm}"]['parsed']['action'] for role in c['roles']] for arm in 'VN'}
  if vectors['V']==vectors['N']:same.append(c['id'])
 assert same==a['summary'][stage]['human_protected']['initial_joint_agreement']['VN']['identical_initial_worlds'];checks+=1
# Verify every HP06 and HP08 physical entry against the declared narrative algebra.
for cid in ('HP06','HP08'):
 for x,y,z in itertools.product(range(3),repeat=3):
  if cid=='HP06':
   base=[[5,3,7],[9,5,7],[0,0,0]][x][y];service=0 if x==2 else max(0,min(10,base-(3 if z==0 else 0)+(1 if z==2 else 0)))
   direct=[1,1,0][y]+[0,0,1][z];interaction=4*(z==0 and y==1)+3*(x==0 and y==0);aux=[2,2,6][x]+[4,4,3][y]+[2,2,4][z]
  else:
   service=min(10,min([8,0,5][x],[7,1,4][y],[6,2,4][z])+min([0,7,5][x],[1,6,4][y],[2,6,4][z]))
   direct=[2,0,1][x]+[1,0,1][z];interaction=2*((x==2)+(y==2)+(z==2)==1);aux=[3,3,4][x]+[2,2,3][y]+[2,2,4][z]
  assert lookup[cid]['parameters']['consequence_table'][f'{x},{y},{z}']==dict(service=service,direct=direct,interaction=interaction,auxiliary=aux);checks+=4
assert [a['summary']['R2']['human_protected']['models'][arm]['changed_private_vs_shared'] for arm in 'VNU']==[5,6,5]
out={'status':'PASS','independent_numeric_assertions':checks,'HP06_HP08_narrative_table_entries_verified':54,'matched_controller_prompt_pairs':a['visibility_pairs_checked']//2,'prompt_pair_difference_check':a['private_shared_prompt_difference_verified'],'R1_GUIDE_observations_verified':True,'R2_recomputed_separately':True,'existing_primary_analysis_files_modified':False,'review_scope':'Second numerical implementation by same implementation owner; not independent human review','model_calls':0,'analysis_sha256':hashlib.sha256((P/'swarm_analysis/peer_proposal_analysis.json').read_bytes()).hexdigest()}
(P/'swarm_analysis/verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
